from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext, Document, Settings
from llama_index.core.node_parser import UnstructuredElementNodeParser
from llama_index.llms.gemini import Gemini
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.postprocessor import LongContextReorder

import qdrant_client
import configparser
import os
import sys


def load_config():
    """載入設定檔"""
    config_ini = configparser.ConfigParser()
    config_ini.read('config.ini')
    
    return {
        'gemini_key': config_ini['GeminiChat']['KEY'],
        'embedding_gemini_model': config_ini['GeminiChat']['EMBEDDING_MODEL_NAME'],
        'chat_gemini_model': config_ini['GeminiChat']['CHAT_MODEL_NAME'],
        'qdrant_url': config_ini['QDRANT']['URL'],
        'qdrant_key': config_ini['QDRANT']['API_KEY'],
        'input_dir': config_ini['Base']['INPUT_DIR']
    }


def setup_models(config):
    """設定 LLM 和嵌入模型"""
    llm = Gemini(model_name=config['chat_gemini_model'], api_key=config['gemini_key'])
    embed_model = GoogleGenAIEmbedding(
        api_key=config['gemini_key'], 
        model=config['embedding_gemini_model'], 
        task_type="RETRIEVAL_DOCUMENT"
    )
    
    Settings.llm = llm
    Settings.embed_model = embed_model
    Settings.node_parser = UnstructuredElementNodeParser(llm=llm)
    
    return llm, embed_model


def load_uploaded_documents(upload_folder):
    """只載入上傳目錄中的 PDF 文件，節省記憶體"""
    if not upload_folder or not os.path.exists(upload_folder):
        print(f"上傳目錄不存在: {upload_folder}")
        sys.stdout.flush()
        return []
    
    try:
        # 檢查目錄中是否有 PDF 文件
        pdf_files = [f for f in os.listdir(upload_folder) if f.lower().endswith('.pdf')]
        if not pdf_files:
            print(f"上傳目錄 {upload_folder} 中沒有找到 PDF 文件")
            sys.stdout.flush()
            return []
        
        print(f"找到 {len(pdf_files)} 個 PDF 文件: {pdf_files}")
        sys.stdout.flush()
        
        # 逐個載入文件以減少記憶體使用
        all_documents = []
        for pdf_file in pdf_files:
            file_path = os.path.join(upload_folder, pdf_file)
            try:
                # 使用 SimpleDirectoryReader 載入單個文件
                documents = SimpleDirectoryReader(
                    input_files=[file_path],
                    encoding='utf-8'
                ).load_data()
                
                all_documents.extend(documents)
                print(f"載入文件 {pdf_file}: {len(documents)} 個文檔片段")
                sys.stdout.flush()
                
                # 手動觸發垃圾回收
                import gc
                gc.collect()
                
            except Exception as e:
                print(f"載入文件 {pdf_file} 時發生錯誤: {e}")
                sys.stdout.flush()
                continue
        
        print(f"總共載入 {len(all_documents)} 個文檔片段")
        sys.stdout.flush()
        return all_documents
        
    except Exception as e:
        print(f"載入上傳目錄文件時發生錯誤: {e}")
        sys.stdout.flush()
        return []


def setup_vector_store(qdrant_url, qdrant_key, collection_name="operation_guide"):
    """設定向量資料庫"""
    qdrant_client_instance = qdrant_client.QdrantClient(url=qdrant_url, api_key=qdrant_key)
    
    # 檢查並刪除現有集合
    try:
        qdrant_client_instance.get_collection(collection_name=collection_name)
        print(f"集合 '{collection_name}' 已存在，正在刪除...")
        qdrant_client_instance.delete_collection(collection_name=collection_name)
        print("刪除成功。")
    except Exception as e:
        print(f"集合 '{collection_name}' 不存在，無需刪除。")
    
    vector_store = QdrantVectorStore(
        client=qdrant_client_instance, 
        collection_name=collection_name, 
        enable_hybrid=True
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    return vector_store, storage_context


def create_vector_index(documents, storage_context):
    """建立向量索引，使用小批次處理以節省記憶體"""
    if not documents:
        print("沒有文檔可以建立索引")
        sys.stdout.flush()
        return None
    
    # 使用更小的批次大小以節省記憶體
    batch_size = 3  # 減少到每批3個文檔片段
    
    print(f"開始分批建立向量索引，總文檔片段數: {len(documents)}, 批次大小: {batch_size}")
    sys.stdout.flush()
    
    index = None
    processed_count = 0
    
    try:
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            batch_num = i // batch_size + 1
            
            print(f"處理第 {batch_num} 批，文檔片段數: {len(batch)} (已處理: {processed_count}/{len(documents)})")
            sys.stdout.flush()
            
            if index is None:
                # 第一批：建立新索引
                index = VectorStoreIndex.from_documents(
                    batch,
                    storage_context=storage_context,
                    vector_store_kwargs={"enable_hybrid": True},
                    show_progress=False,
                )
                print(f"已建立初始索引，包含 {len(batch)} 個文檔片段")
            else:
                # 後續批次：逐個添加到現有索引以減少記憶體峰值
                for j, doc in enumerate(batch):
                    try:
                        index.insert(doc)
                        processed_count += 1
                        if (processed_count % 5) == 0:  # 每5個文檔片段顯示一次進度
                            print(f"已處理 {processed_count}/{len(documents)} 個文檔片段")
                            sys.stdout.flush()
                    except Exception as e:
                        print(f"插入文檔片段時發生錯誤: {e}")
                        sys.stdout.flush()
                        continue
            
            # 每批處理後手動觸發垃圾回收
            import gc
            gc.collect()
            
            # 給系統一點時間回收記憶體
            import time
            time.sleep(0.1)
        
        print("向量索引建立完成")
        sys.stdout.flush()
        return index
        
    except Exception as e:
        print(f"建立向量索引時發生錯誤: {e}")
        sys.stdout.flush()
        return None


def create_query_engine(index, config):
    """建立查詢引擎"""
    chat_llm = Gemini(
        model_name=config['chat_gemini_model'],
        api_key=config['gemini_key'],
    )
    
    query_engine = index.as_query_engine(
        llm=chat_llm,
        vector_store_query_mode='hybrid',
        alpha=0.5,
        similarity_top_k=5,
        sparse_top_k=5,
        node_postprocessors=[LongContextReorder()],
        num_queries=4,
        streaming=True
    )
    
    print("查詢引擎建立完成")
    sys.stdout.flush()
    return query_engine


def query_pdf(query_engine, question: str):
    """執行 PDF 查詢"""
    try:
        response = query_engine.query(question)
        
        # 提取來源資訊和頁數
        source_info = []
        if hasattr(response, 'source_nodes') and response.source_nodes:
            for node in response.source_nodes:
                page_info = {}
                
                # 提取檔案名稱
                if hasattr(node, 'metadata') and 'file_name' in node.metadata:
                    page_info['file_name'] = node.metadata['file_name']
                elif hasattr(node, 'node') and hasattr(node.node, 'metadata') and 'file_name' in node.node.metadata:
                    page_info['file_name'] = node.node.metadata['file_name']
                else:
                    page_info['file_name'] = "未知文件"
                
                # 提取頁數
                if hasattr(node, 'metadata') and 'page_label' in node.metadata:
                    page_info['page'] = node.metadata['page_label']
                elif hasattr(node, 'node') and hasattr(node.node, 'metadata') and 'page_label' in node.node.metadata:
                    page_info['page'] = node.node.metadata['page_label']
                else:
                    page_info['page'] = "未知頁數"
                
                # 提取相似度分數
                if hasattr(node, 'score'):
                    page_info['score'] = round(node.score, 3)
                else:
                    page_info['score'] = 0.0
                
                source_info.append(page_info)
        
        # 將來源資訊添加到回應中
        response.source_info = source_info
        
        # 返回響應對象而不是直接打印
        return response
    except Exception as e:
        print(f"查詢錯誤: {e}")
        raise e


def process_uploaded_pdf(pdf_path):
    """處理單個上傳的PDF文件，節省記憶體"""
    try:
        if not os.path.exists(pdf_path):
            print(f"文件不存在: {pdf_path}")
            return []
        
        # 使用SimpleDirectoryReader讀取單個文件
        documents = SimpleDirectoryReader(
            input_files=[pdf_path],
            encoding='utf-8'
        ).load_data()
        
        print(f"成功處理上傳的PDF: {os.path.basename(pdf_path)}, 文檔片段數量: {len(documents)}")
        sys.stdout.flush()
        
        # 手動觸發垃圾回收
        import gc
        gc.collect()
        
        return documents
    except Exception as e:
        print(f"處理上傳PDF錯誤: {e}")
        sys.stdout.flush()
        raise e


def add_pdf_to_existing_index(pdf_path, query_engine):
    """將新的PDF添加到現有的索引中，節省記憶體"""
    try:
        # 處理新的PDF文件
        new_documents = process_uploaded_pdf(pdf_path)
        if not new_documents:
            return query_engine
        
        # 獲取現有的索引
        index = query_engine._index if hasattr(query_engine, '_index') else None
        if index is None:
            print("無法獲取現有索引，需要重新初始化服務")
            return None
        
        # 分批添加新文檔以節省記憶體
        batch_size = 2  # 更小的批次
        for i in range(0, len(new_documents), batch_size):
            batch = new_documents[i:i+batch_size]
            for doc in batch:
                index.insert(doc)
            
            # 手動觸發垃圾回收
            import gc
            gc.collect()
            
            print(f"已添加 {min(i+batch_size, len(new_documents))}/{len(new_documents)} 個文檔片段到索引")
            sys.stdout.flush()
        
        print(f"成功將 {len(new_documents)} 個文檔片段添加到現有索引")
        sys.stdout.flush()
        return query_engine
        
    except Exception as e:
        print(f"添加PDF到索引時發生錯誤: {e}")
        sys.stdout.flush()
        return None


def clear_uploaded_data(upload_folder=None, qdrant_url=None, qdrant_key=None, collection_name="operation_guide"):
    """清空上傳的資料，包括上傳文件和向量資料庫"""
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
        
        # 2. 清空向量資料庫
        if qdrant_url and qdrant_key:
            try:
                qdrant_client_instance = qdrant_client.QdrantClient(url=qdrant_url, api_key=qdrant_key)
                try:
                    qdrant_client_instance.delete_collection(collection_name=collection_name)
                    print(f"已刪除向量資料庫集合: {collection_name}")
                    sys.stdout.flush()
                except Exception as e:
                    print(f"刪除向量資料庫集合失敗: {e}")
                    sys.stdout.flush()
            except Exception as e:
                print(f"連接向量資料庫失敗: {e}")
                sys.stdout.flush()
        
        # 手動觸發垃圾回收
        import gc
        gc.collect()
        
        print("上傳資料清空完成")
        sys.stdout.flush()
        return True
        
    except Exception as e:
        print(f"清空上傳資料失敗: {e}")
        sys.stdout.flush()
        return False


def get_upload_folder_info(upload_folder):
    """獲取上傳文件夾的資訊"""
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


def initialize_pdf_service(upload_folder=None):
    """初始化完整的 PDF 服務，只處理上傳的文件"""
    # 1. 載入設定
    config = load_config()
    
    # 2. 設定模型
    llm, embed_model = setup_models(config)
    
    # 3. 只載入上傳的文件
    if not upload_folder:
        upload_folder = config.get('input_dir', './uploads')
    
    documents = load_uploaded_documents(upload_folder)
    
    # 如果沒有文件，返回None
    if not documents:
        print("警告: 沒有找到任何上傳的PDF文件")
        sys.stdout.flush()
        return None
    
    # 4. 設定向量資料庫
    vector_store, storage_context = setup_vector_store(
        config['qdrant_url'], 
        config['qdrant_key']
    )
    
    # 5. 建立向量索引
    index = create_vector_index(documents, storage_context)
    if index is None:
        print("錯誤: 無法建立向量索引")
        sys.stdout.flush()
        return None
    
    # 6. 建立查詢引擎
    query_engine = create_query_engine(index, config)
    
    return query_engine


# 主程式執行
if __name__ == "__main__":
    # 初始化服務
    query_engine = initialize_pdf_service()
    
    # 執行查詢範例
    question = "請問文件中提到什麼重要資訊？"
    response = query_pdf(query_engine, question)

