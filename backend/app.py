from flask import Flask, request, jsonify, Response, stream_template
from flask_cors import CORS
import json
import time
import os
import shutil
from threading import Lock
from werkzeug.utils import secure_filename
from pathlib import Path
from service.pdf_service import initialize_pdf_service, query_pdf, process_uploaded_pdf, clear_all_data
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # 允許跨域請求

# 文件上傳配置
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# 確保上傳目錄存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 全局變數來存儲查詢引擎和上傳的文件
query_engine = None
uploaded_files = []
initialization_lock = Lock()

def allowed_file(filename):
    """檢查文件擴展名是否允許"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_query_engine(upload_folder=None):
    """獲取查詢引擎，如果未初始化則初始化"""
    global query_engine
    
    if query_engine is None:
        with initialization_lock:
            if query_engine is None:
                logger.info("初始化 PDF 服務...")
                try:
                    query_engine = initialize_pdf_service(upload_folder=upload_folder)
                    logger.info("PDF 服務初始化完成")
                except Exception as e:
                    logger.error(f"PDF 服務初始化失敗: {e}")
                    raise e
    
    return query_engine

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """處理文件上傳"""
    try:
        # 檢查是否有文件被上傳
        if 'file' not in request.files:
            return jsonify({
                'error': '沒有選擇文件',
                'status': 'error'
            }), 400
        
        file = request.files['file']
        
        # 檢查文件名
        if file.filename == '':
            return jsonify({
                'error': '沒有選擇文件',
                'status': 'error'
            }), 400
        
        # 檢查文件類型
        if not allowed_file(file.filename):
            return jsonify({
                'error': '只支援 PDF 文件',
                'status': 'error'
            }), 400
        
        # 處理上傳的PDF
        try:
            global query_engine, uploaded_files
            
            # 先清空現有資料
            with initialization_lock:
                logger.info("清空現有上傳文件和資料集...")
                
                # 載入配置以獲取 Qdrant 資訊
                import configparser
                config_ini = configparser.ConfigParser()
                config_ini.read('config.ini')
                
                # 使用新的清理函數
                clear_success = clear_all_data(
                    upload_folder=UPLOAD_FOLDER,
                    qdrant_url=config_ini['QDRANT']['URL'],
                    qdrant_key=config_ini['QDRANT']['API_KEY']
                )
                
                if not clear_success:
                    logger.warning("資料清空過程中發生警告，但繼續處理新文件")
                
                # 重置應用程式狀態
                uploaded_files.clear()
                query_engine = None
                
                logger.info("資料清空完成")
                
                # 現在保存新文件
                filename = secure_filename(file.filename)
                timestamp = str(int(time.time()))
                filename = f"{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                # 確保上傳目錄存在
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                file.save(filepath)
                
                logger.info(f"新文件保存成功: {filepath}")
                
                # 添加新文件到列表
                uploaded_files.append({
                    'filename': filename,
                    'original_name': file.filename,
                    'filepath': filepath,
                    'upload_time': time.time()
                })
                
                # 重新初始化服務（只包含新上傳的文件）
                logger.info("重新初始化 PDF 服務以包含新上傳的文件...")
                query_engine = initialize_pdf_service(upload_folder=UPLOAD_FOLDER)
                logger.info("PDF 服務重新初始化完成")
            
            return jsonify({
                'message': 'PDF 文件上傳並處理成功',
                'filename': file.filename,
                'status': 'success',
                'timestamp': time.time()
            })
            
        except Exception as e:
            logger.error(f"處理上傳文件錯誤: {e}")
            # 如果處理失敗，刪除上傳的文件
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({
                'error': f'處理上傳的PDF文件時發生錯誤: {str(e)}',
                'status': 'error'
            }), 500
        
    except Exception as e:
        logger.error(f"文件上傳錯誤: {e}")
        return jsonify({
            'error': f'文件上傳失敗: {str(e)}',
            'status': 'error'
        }), 500

@app.route('/api/files', methods=['GET'])
def list_files():
    """列出已上傳的文件"""
    global uploaded_files
    
    return jsonify({
        'files': uploaded_files,
        'count': len(uploaded_files),
        'status': 'success'
    })

@app.route('/api/files/<filename>', methods=['DELETE'])
def delete_file(filename):
    """刪除上傳的文件"""
    try:
        global uploaded_files, query_engine
        
        # 找到要刪除的文件
        file_to_delete = None
        for file_info in uploaded_files:
            if file_info['filename'] == filename:
                file_to_delete = file_info
                break
        
        if not file_to_delete:
            return jsonify({
                'error': '文件不存在',
                'status': 'error'
            }), 404
        
        # 刪除物理文件
        filepath = file_to_delete['filepath']
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # 從列表中移除
        uploaded_files = [f for f in uploaded_files if f['filename'] != filename]
        
        # 重新初始化PDF服務
        with initialization_lock:
            logger.info("重新初始化 PDF 服務...")
            query_engine = initialize_pdf_service(upload_folder=UPLOAD_FOLDER)
            logger.info("PDF 服務重新初始化完成")
        
        logger.info(f"文件刪除成功: {filename}")
        
        return jsonify({
            'message': '文件刪除成功',
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"刪除文件錯誤: {e}")
        return jsonify({
            'error': f'刪除文件失敗: {str(e)}',
            'status': 'error'
        }), 500

@app.route('/api/clear', methods=['POST'])
def clear_all():
    """清空所有上傳的文件和資料集"""
    try:
        global query_engine, uploaded_files
        
        with initialization_lock:
            logger.info("手動清空所有資料...")
            
            # 載入配置
            import configparser
            config_ini = configparser.ConfigParser()
            config_ini.read('config.ini')
            
            # 清空所有資料
            clear_success = clear_all_data(
                upload_folder=UPLOAD_FOLDER,
                qdrant_url=config_ini['QDRANT']['URL'],
                qdrant_key=config_ini['QDRANT']['API_KEY']
            )
            
            # 重置應用程式狀態
            uploaded_files.clear()
            query_engine = None
            
            if clear_success:
                logger.info("所有資料清空成功")
                return jsonify({
                    'message': '所有資料清空成功',
                    'status': 'success',
                    'timestamp': time.time()
                })
            else:
                logger.warning("資料清空過程中發生警告")
                return jsonify({
                    'message': '資料清空完成，但過程中發生一些警告',
                    'status': 'warning',
                    'timestamp': time.time()
                })
        
    except Exception as e:
        logger.error(f"清空資料錯誤: {e}")
        return jsonify({
            'error': f'清空資料時發生錯誤: {str(e)}',
            'status': 'error'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康檢查端點"""
    return jsonify({
        'status': 'healthy',
        'message': 'PDF Chat API is running',
        'timestamp': time.time()
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    """處理聊天請求"""
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                'error': '缺少必要的訊息內容'
            }), 400
        
        user_message = data['message'].strip()
        if not user_message:
            return jsonify({
                'error': '訊息內容不能為空'
            }), 400
        
        # 獲取查詢引擎
        engine = get_query_engine(upload_folder=UPLOAD_FOLDER)
        
        # 執行查詢
        logger.info(f"處理查詢: {user_message}")
        response = query_pdf(engine, user_message)
        
        # 提取回應文字
        response_text = str(response.response) if hasattr(response, 'response') else str(response)
        
        # 提取來源資訊
        sources = []
        if hasattr(response, 'source_info') and response.source_info:
            sources = response.source_info
            
        # 如果有來源資訊，在回應中添加
        if sources:
            source_text = "\n\n📖 參考來源："
            for i, source in enumerate(sources[:3], 1):  # 只顯示前3個來源
                file_name = source.get('file_name', '未知文件')
                page = source.get('page', '未知頁數')
                score = source.get('score', 0.0)
                source_text += f"\n{i}. {file_name} - 第 {page} 頁 (相關度: {score:.2f})"
            
            response_text += source_text
        
        return jsonify({
            'response': response_text,
            'sources': sources,
            'timestamp': time.time(),
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"聊天處理錯誤: {e}")
        return jsonify({
            'error': f'處理請求時發生錯誤: {str(e)}',
            'status': 'error'
        }), 500

@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """處理流式聊天請求"""
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                'error': '缺少必要的訊息內容'
            }), 400
        
        user_message = data['message'].strip()
        if not user_message:
            return jsonify({
                'error': '訊息內容不能為空'
            }), 400
        
        def generate():
            try:
                # 獲取查詢引擎
                engine = get_query_engine(upload_folder=UPLOAD_FOLDER)
                
                # 執行查詢
                logger.info(f"處理流式查詢: {user_message}")
                response = query_pdf(engine, user_message)
                
                # 處理流式回應
                if hasattr(response, 'response_gen'):
                    for chunk in response.response_gen:
                        yield f"data: {json.dumps({'chunk': chunk, 'status': 'streaming'})}\n\n"
                else:
                    # 如果不支援流式，則一次性返回
                    response_text = str(response.response) if hasattr(response, 'response') else str(response)
                    yield f"data: {json.dumps({'chunk': response_text, 'status': 'complete'})}\n\n"
                
                # 發送來源資訊
                if hasattr(response, 'source_info') and response.source_info:
                    sources = response.source_info[:3]  # 只顯示前3個來源
                    source_text = "\n\n📖 參考來源："
                    for i, source in enumerate(sources, 1):
                        file_name = source.get('file_name', '未知文件')
                        page = source.get('page', '未知頁數')
                        score = source.get('score', 0.0)
                        source_text += f"\n{i}. {file_name} - 第 {page} 頁 (相關度: {score:.2f})"
                    
                    yield f"data: {json.dumps({'chunk': source_text, 'sources': sources, 'status': 'sources'})}\n\n"
                
                yield f"data: {json.dumps({'status': 'complete'})}\n\n"
                
            except Exception as e:
                logger.error(f"流式聊天處理錯誤: {e}")
                yield f"data: {json.dumps({'error': str(e), 'status': 'error'})}\n\n"
        
        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        )
        
    except Exception as e:
        logger.error(f"流式聊天初始化錯誤: {e}")
        return jsonify({
            'error': f'初始化流式聊天時發生錯誤: {str(e)}',
            'status': 'error'
        }), 500

@app.route('/api/initialize', methods=['POST'])
def initialize():
    """手動初始化 PDF 服務"""
    try:
        global query_engine
        
        with initialization_lock:
            logger.info("手動初始化 PDF 服務...")
            query_engine = initialize_pdf_service()
            logger.info("PDF 服務初始化完成")
        
        return jsonify({
            'message': 'PDF 服務初始化成功',
            'status': 'success',
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"手動初始化錯誤: {e}")
        return jsonify({
            'error': f'初始化 PDF 服務時發生錯誤: {str(e)}',
            'status': 'error'
        }), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """獲取服務狀態"""
    global query_engine
    
    return jsonify({
        'pdf_service_initialized': query_engine is not None,
        'timestamp': time.time(),
        'status': 'active'
    })

if __name__ == '__main__':
    # 啟動時不自動初始化，等待第一次請求時初始化
    logger.info("啟動 Flask 應用...")
    app.run(debug=True, host='0.0.0.0', port=5009, threaded=True)
