import os
import sys
import gc
from .chat_stream_service import ChatStreamService
from .embedding_service import EmbeddingService
from .llama_index_utils import LlamaIndexProcessor
from .config_manager import ConfigManager

class PDFService:
    def __init__(self, config_path = 'config.ini'):
        config_manager = ConfigManager(config_path)
        config, config_sections = config_manager.get_complete_config()
        self.config = config
        self.config_sections = config_sections
        self.config_manager = config_manager
        self.embedding_service = EmbeddingService(config_path)

    def clear_uploaded_data(self, upload_folder=None, collection_name="operation_guide"):
        try:
            # 1. 清空上傳文件夾
            if upload_folder and os.path.exists(upload_folder):
                try:
                    pdf_files = [f for f in os.listdir(upload_folder) if f.lower().endswith('.pdf')]
                    for filename in pdf_files:
                        filepath = os.path.join(upload_folder, filename)
                        try:
                            os.remove(filepath)
                            print(f"已刪除上傳的PDF文件: {filename}")
                            sys.stdout.flush()
                        except Exception as e:
                            print(f"刪除文件失敗 {filename}: {e}")
                            sys.stdout.flush()
                    print(f"已清空上傳的PDF文件，共清理 {len(pdf_files)} 個文件")
                    sys.stdout.flush()
                except Exception as e:
                    print(f"清空上傳文件夾時發生錯誤: {e}")
                    sys.stdout.flush()

                try:
                    success = self.embedding_service.delete_qdrant_collection(collection_name)
                    if success:
                        print(f"✅ 已刪除向量資料庫集合: {collection_name}")
                    else:
                        print(f"⚠️ 刪除向量資料庫集合失敗 (可能不存在): {collection_name}")
                except Exception as e:
                    print(f"❌ 清空向量資料庫時發生錯誤: {e}")
                    sys.stdout.flush()
            
            # 手動觸發垃圾回收
            gc.collect()
            
            print("上傳資料清空完成")
            sys.stdout.flush()
            return True
            
        except Exception as e:
            print(f"清空上傳資料失敗: {e}")
            sys.stdout.flush()
            return False


    def create_llama_index_service(
        self,
        upload_folder=None,
        collection_name="pdf_chat_collection"):
        
        print(f"🚀 使用 LlamaIndexProcessor 創建 PDF 服務")

        try:
            processor = LlamaIndexProcessor(self.config_manager)
            print("✅ LlamaIndexProcessor 初始化成功")
        except Exception as e:
            print(f"❌ LlamaIndexProcessor 初始化失敗: {e}")
            return None
        
        # 獲取上傳文件夾路徑
        if not upload_folder:
            base_config = self.config_manager.get_base_config()
            upload_folder = base_config['input_dir']
        
        # 檢查是否有文件
        if not upload_folder or not os.path.exists(upload_folder):
            print(f"⚠️ 上傳目錄不存在: {upload_folder}")
            return {
                'processor': processor,
                'mode': 'chat_only',
                'upload_folder': upload_folder
            }
        
        # 檢查 PDF 文件
        pdf_files = [f for f in os.listdir(upload_folder) if f.lower().endswith('.pdf')]
        if not pdf_files:
            print(f"⚠️ 上傳目錄中沒有 PDF 文件: {upload_folder}")
            return {
                'processor': processor,
                'mode': 'chat_only',
                'upload_folder': upload_folder
            }
        
        print(f"📁 找到 {len(pdf_files)} 個 PDF 文件: {pdf_files}")
        
        # 載入文件並創建索引
        try:
            print("📄 載入文件...")
            documents = processor.load_documents(upload_folder, [".pdf"])
            print(f"✅ 載入 {len(documents)} 個文件片段")
            
            print("🔍 創建向量索引...")
            index = processor.create_qdrant_index(documents, collection_name)
            print("✅ 向量索引創建成功")
            
            print("⚙️ 創建查詢引擎...")
            query_engine = processor.create_query_engine()
            print("✅ 查詢引擎創建成功")
            
            return {
                'processor': processor,
                'mode': 'full',
                'upload_folder': upload_folder,
                'documents': documents,
                'index': index,
                'query_engine': query_engine,
                'collection_name': collection_name,
                'pdf_files': pdf_files
            }
            
        except Exception as e:
            print(f"❌ 創建索引或查詢引擎失敗: {e}")
            return {
                'processor': processor,
                'mode': 'error',
                'upload_folder': upload_folder,
                'error': str(e)
            }


    def query_with_llama_index(self, service, question: str, use_chat_enhancement=False, chat_type='gemini'):
        if not service:
            return "❌ 服務未初始化"
        
        processor = service.get('processor')
        if not processor:
            return "❌ LlamaIndexProcessor 未初始化"
        
        # 如果是純聊天模式
        if service.get('mode') == 'chat_only':
            if use_chat_enhancement:
                try:
                    # 使用實例的配置創建聊天服務
                    chat_stream_service = ChatStreamService(self.config_sections)
                    return chat_stream_service.chat(question, chat_type)
                except Exception as e:
                    return f"❌ 聊天服務錯誤: {e}"
            else:
                return "⚠️ 沒有 PDF 文件可查詢，請先上傳 PDF 文件"
        
        # 如果是錯誤模式
        if service.get('mode') == 'error':
            return f"❌ 服務錯誤: {service.get('error', '未知錯誤')}"
        
        # 執行 PDF 查詢
        try:
            response = processor.query(question)
            
            # 調試日誌
            print(f"🔍 查詢問題: {question}")
            print(f"📝 響應類型: {type(response)}")
            
            # 檢查是否是 StreamingResponse
            if hasattr(response, 'response_gen'):
                print(f"✅ 檢測到 StreamingResponse，直接返回")
                return response  # 直接返回 StreamingResponse 對象
            
            # 檢查響應是否有效
            has_valid_response = response is not None and str(response).strip()
            print(f"📝 原始響應: {response}")
            print(f"📊 響應有效性: {has_valid_response}")
            
            # 如果啟用聊天增強
            if use_chat_enhancement:
                try:
                    chat_stream_service = ChatStreamService(self.config_sections)
                    
                    if has_valid_response:
                        # 構建增強問題
                        context_text = str(response)[:1000]
                        enhanced_question = f"""
基於以下 PDF 文件內容回答問題，請提供更詳細和有用的回答：

PDF 內容摘要：
{context_text}

原始問題：{question}

請基於 PDF 內容提供詳細回答，並補充相關建議或解釋：
"""
                        enhanced_response = chat_stream_service.chat(enhanced_question, chat_type)
                        
                        # 組合回答
                        final_response = {
                            'pdf_answer': str(response),
                            'enhanced_answer': enhanced_response,
                            'chat_type': chat_type,
                            'source_files': service.get('pdf_files', [])
                        }
                    else:
                        # 沒有 PDF 內容時，只使用聊天服務
                        chat_response = chat_stream_service.chat(question, chat_type)
                        final_response = {
                            'pdf_answer': None,
                            'enhanced_answer': chat_response,
                            'chat_type': chat_type,
                            'source_files': service.get('pdf_files', [])
                        }
                    
                    print(f"✅ 增強響應: {final_response}")
                    return final_response
                    
                except Exception as e:
                    print(f"⚠️ 聊天增強失敗: {e}")
                    return {
                        'pdf_answer': str(response) if has_valid_response else None,
                        'enhanced_answer': None,
                        'error': str(e),
                        'source_files': service.get('pdf_files', [])
                    }
            
            # 返回基本回答
            basic_response = {
                'pdf_answer': str(response) if has_valid_response else None,
                'enhanced_answer': None,
                'source_files': service.get('pdf_files', [])
            }
            print(f"✅ 基本響應: {basic_response}")
            return basic_response
            
        except Exception as e:
            print(f"❌ 查詢錯誤: {e}")
            return f"❌ 查詢錯誤: {e}"


    def add_pdf_to_llama_index_service(self, service, pdf_path):
        if not service or not service.get('processor'):
            print("❌ 服務未初始化")
            return None
        
        processor = service['processor']
        
        try:
            # 載入新的 PDF 文件
            print(f"📄 載入新的 PDF: {pdf_path}")
            new_documents = processor.load_documents(os.path.dirname(pdf_path), [".pdf"])
            
            # 如果之前沒有索引，創建新的
            if service.get('mode') == 'chat_only' or not service.get('index'):
                print("🔍 創建新的向量索引...")
                collection_name = service.get('collection_name', 'pdf_chat_collection')
                index = processor.create_qdrant_index(new_documents, collection_name)
                query_engine = processor.create_query_engine()
                
                # 更新服務狀態
                service['mode'] = 'full'
                service['documents'] = new_documents
                service['index'] = index
                service['query_engine'] = query_engine
                service['pdf_files'] = [os.path.basename(pdf_path)]
                
            else:
                # 將新文檔添加到現有索引
                print("➕ 添加到現有索引...")
                for doc in new_documents:
                    processor.index.insert(doc)
                
                # 更新文件列表
                if 'pdf_files' not in service:
                    service['pdf_files'] = []
                service['pdf_files'].append(os.path.basename(pdf_path))
                
                # 更新文檔列表
                if 'documents' in service:
                    service['documents'].extend(new_documents)
                else:
                    service['documents'] = new_documents
            
            print(f"✅ 成功添加 PDF: {os.path.basename(pdf_path)}")
            return service
            
        except Exception as e:
            print(f"❌ 添加 PDF 失敗: {e}")
            return service

    def get_upload_folder_info(self, upload_folder=None):
        if upload_folder is None:
            upload_folder = self.config['input_dir']
            
        try:
            if not upload_folder or not os.path.exists(upload_folder):
                return {
                    'exists': False,
                    'pdf_count': 0,
                    'pdf_files': [],
                    'total_size': 0
                }
            
            pdf_files = [f for f in os.listdir(upload_folder) if f.lower().endswith('.pdf')]
            total_size = 0
            
            for pdf_file in pdf_files:
                file_path = os.path.join(upload_folder, pdf_file)
                try:
                    total_size += os.path.getsize(file_path)
                except:
                    pass
            
            return {
                'exists': True,
                'pdf_count': len(pdf_files),
                'pdf_files': pdf_files,
                'total_size': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            print(f"獲取上傳文件夾資訊時發生錯誤: {e}")
            return {
                'exists': False,
                'pdf_count': 0,
                'pdf_files': [],
                'total_size': 0,
                'error': str(e)
            }

    def list_qdrant_collections(self):
        """列出所有 Qdrant 集合"""
        return self.embedding_service.list_qdrant_collections()
    
    def collection_exists(self, collection_name: str):
        """檢查集合是否存在"""
        return self.embedding_service.collection_exists(collection_name)
    
    def delete_collection(self, collection_name: str):
        """刪除指定的集合"""
        return self.embedding_service.delete_qdrant_collection(collection_name)

