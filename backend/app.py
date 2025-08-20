from flask import Flask, request, jsonify, Response, stream_template
from flask_cors import CORS
import json
import time
import os
import sys
import shutil
from threading import Lock
from werkzeug.utils import secure_filename
from pathlib import Path
from service.pdf_service import initialize_pdf_service, query_pdf, process_uploaded_pdf, clear_uploaded_data, add_pdf_to_existing_index, get_upload_folder_info, load_config, get_cors_origins
import logging

# 載入配置
app_config = load_config()
                
# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 動態 CORS 設定
cors_origins = get_cors_origins(app_config)
CORS(app, origins=cors_origins)  # 使用動態生成的允許來源

# 文件上傳配置
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# 確保上傳目錄存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.chmod(UPLOAD_FOLDER, 0o777) 

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
    """處理文件上傳 - 改進版本，支援異步處理"""
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
                
                # 使用新的清理函數
                clear_success = clear_uploaded_data(
                    upload_folder=UPLOAD_FOLDER,
                    qdrant_url=app_config['qdrant_url'],
                    qdrant_key=app_config['qdrant_key']
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
                os.chmod(UPLOAD_FOLDER, 0o777) 
                file.save(filepath)
                
                logger.info(f"新文件保存成功: {filepath}")
                
                # 添加新文件到列表
                uploaded_files.append({
                    'filename': filename,
                    'original_name': file.filename,
                    'filepath': filepath,
                    'upload_time': time.time(),
                    'status': 'processing'
                })
                
                # 立即返回成功響應，在背景處理索引
                response_data = {
                    'message': 'PDF 文件上傳成功，正在處理中...',
                    'filename': file.filename,
                    'status': 'uploading',
                    'processing': True,
                    'timestamp': time.time()
                }
                
                # 在背景線程中處理索引
                import threading
                def process_in_background():
                    try:
                        logger.info("背景處理：重新初始化 PDF 服務以包含新上傳的文件...")
                        global query_engine
                        query_engine = initialize_pdf_service(upload_folder=UPLOAD_FOLDER)
                        # 更新文件狀態
                        if uploaded_files:
                            uploaded_files[-1]['status'] = 'completed'
                        logger.info("背景處理：PDF 服務重新初始化完成")
                    except Exception as e:
                        logger.error(f"背景處理錯誤: {e}")
                        if uploaded_files:
                            uploaded_files[-1]['status'] = 'error'
                            uploaded_files[-1]['error'] = str(e)
                
                thread = threading.Thread(target=process_in_background)
                thread.daemon = True
                thread.start()
                
                return jsonify(response_data)
            
        except Exception as e:
            logger.error(f"處理上傳文件錯誤: {e}")
            # 如果處理失敗，刪除上傳的文件
            if 'filepath' in locals() and os.path.exists(filepath):
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
    """列出所有上傳的文件"""
    try:
        files_info = []
        for file_info in uploaded_files:
            files_info.append({
                'filename': file_info.get('original_name', file_info['filename']),
                'upload_time': file_info['upload_time'],
                'status': file_info.get('status', 'completed'),
                'error': file_info.get('error', None)
            })
        
        return jsonify({
            'files': files_info,
            'total': len(files_info),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"列出文件錯誤: {e}")
        return jsonify({
            'error': f'獲取文件列表失敗: {str(e)}',
            'status': 'error'
        }), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """獲取系統狀態和處理進度"""
    try:
        # 檢查是否有文件正在處理
        processing_files = [f for f in uploaded_files if f.get('status') == 'processing']
        completed_files = [f for f in uploaded_files if f.get('status') == 'completed']
        error_files = [f for f in uploaded_files if f.get('status') == 'error']
        
        return jsonify({
            'query_engine_ready': query_engine is not None,
            'total_files': len(uploaded_files),
            'processing_files': len(processing_files),
            'completed_files': len(completed_files),
            'error_files': len(error_files),
            'files_detail': [{
                'filename': f.get('original_name', f['filename']),
                'status': f.get('status', 'unknown'),
                'upload_time': f['upload_time'],
                'error': f.get('error', None)
            } for f in uploaded_files],
            'status': 'ready' if query_engine is not None else 'initializing',
            'timestamp': time.time()
        })
    except Exception as e:
        logger.error(f"獲取狀態錯誤: {e}")
        return jsonify({
            'error': f'獲取系統狀態失敗: {str(e)}',
            'status': 'error'
        }), 500

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
            
            # 清空所有資料
            clear_success = clear_uploaded_data(
                upload_folder=UPLOAD_FOLDER,
                qdrant_url=app_config['qdrant_url'],
                qdrant_key=app_config['qdrant_key']
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

@app.route('/api/status', methods=['GET'])
def status_check():
    """狀態檢查端點 - 用於 Docker 健康檢查"""
    return jsonify({
        'status': 'healthy',
        'message': 'PDF Chat API is running',
        'timestamp': time.time()
    })

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
                if engine is None:
                    yield f"data: {json.dumps({'error': 'PDF 服務未初始化，請先上傳文件', 'status': 'error'})}\n\n"
                    sys.stdout.flush()
                    return
                
                # 執行查詢
                logger.info(f"處理流式查詢: {user_message}")
                response = query_pdf(engine, user_message)
                
                # 檢查是否有回應
                if response is None:
                    yield f"data: {json.dumps({'error': '查詢失敗，沒有收到回應', 'status': 'error'})}\n\n"
                    sys.stdout.flush()
                    return
                
                # 處理流式回應
                if hasattr(response, 'response_gen') and response.response_gen:
                    logger.info("使用流式回應生成器")
                    try:
                        for chunk in response.response_gen:
                            if chunk and chunk.strip():
                                yield f"data: {json.dumps({'chunk': str(chunk), 'status': 'streaming'})}\n\n"
                                sys.stdout.flush()
                    except Exception as gen_error:
                        logger.error(f"流式生成器錯誤: {gen_error}")
                        # 如果流式失敗，回退到完整回應
                        response_text = str(response.response) if hasattr(response, 'response') else str(response)
                        yield f"data: {json.dumps({'chunk': response_text, 'status': 'complete'})}\n\n"
                        sys.stdout.flush()
                else:
                    # 非流式回應，模擬流式輸出
                    response_text = str(response.response) if hasattr(response, 'response') else str(response)
                    logger.info("使用模擬流式回應")
                    
                    # 將回應分割成小塊來模擬流式輸出
                    words = response_text.split()
                    chunk_size = 5  # 每次發送5個字
                    
                    for i in range(0, len(words), chunk_size):
                        chunk = ' '.join(words[i:i+chunk_size])
                        if chunk.strip():
                            yield f"data: {json.dumps({'chunk': chunk + ' ', 'status': 'streaming'})}\n\n"
                            sys.stdout.flush()
                            time.sleep(0.05)  # 小延遲模擬打字效果
                
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
                    sys.stdout.flush()
                
                # 發送完成信號
                yield f"data: {json.dumps({'status': 'complete'})}\n\n"
                sys.stdout.flush()
                
            except Exception as e:
                logger.error(f"流式聊天處理錯誤: {e}")
                yield f"data: {json.dumps({'error': f'處理請求時發生錯誤: {str(e)}', 'status': 'error'})}\n\n"
                sys.stdout.flush()
        
        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'X-Accel-Buffering': 'no'  # 關閉 nginx 緩衝
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

if __name__ == '__main__':
    # 啟動時不自動初始化，等待第一次請求時初始化
    logger.info("啟動 Flask 應用...")
    app.run(debug=True, host='0.0.0.0', port=app_config['port_backend'], threaded=True)
