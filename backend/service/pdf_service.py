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


def load_documents(input_dir, upload_folder=None):
    """載入 PDF 文件"""
    all_documents = []
    
    # 載入配置文件中指定的文件
    if input_dir and os.path.exists(input_dir):
        try:
            # 檢查目錄中是否有 PDF 文件
            pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.pdf')]
            if pdf_files:
                config_documents = SimpleDirectoryReader(
                    input_dir=input_dir,
                    recursive=True,
                    required_exts=[".pdf"],
                    exclude=["*.tmp"],
                    encoding='utf-8'
                ).load_data()
                all_documents.extend(config_documents)
                print(f"從配置目錄載入 {len(config_documents)} 個文件")
                sys.stdout.flush()
            else:
                print(f"配置目錄 {input_dir} 中沒有找到 PDF 文件")
                sys.stdout.flush()
        except Exception as e:
            print(f"載入配置目錄文件時發生錯誤: {e}")
            sys.stdout.flush()
    
    # 載入上傳的文件
    if upload_folder and os.path.exists(upload_folder):
        try:
            # 檢查目錄中是否有 PDF 文件
            pdf_files = [f for f in os.listdir(upload_folder) if f.lower().endswith('.pdf')]
            if pdf_files:
                upload_documents = SimpleDirectoryReader(
                    input_dir=upload_folder,
                    recursive=True,
                    required_exts=[".pdf"],
                    exclude=["*.tmp"],
                    encoding='utf-8'
                ).load_data()
                all_documents.extend(upload_documents)
                print(f"從上傳目錄載入 {len(upload_documents)} 個文件")
                sys.stdout.flush()
            else:
                print(f"上傳目錄 {upload_folder} 中沒有找到 PDF 文件")
                sys.stdout.flush()
        except Exception as e:
            print(f"載入上傳目錄文件時發生錯誤: {e}")
            sys.stdout.flush()
    
    print(f"總共載入 {len(all_documents)} 個文件")
    sys.stdout.flush()
    return all_documents


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
    """建立向量索引"""
    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        vector_store_kwargs={"enable_hybrid": True},
        show_progress=False,
    )
    
    print("向量索引建立完成")
    sys.stdout.flush()
    return index


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
    """處理單個上傳的PDF文件"""
    try:
        # 使用SimpleDirectoryReader讀取單個文件
        documents = SimpleDirectoryReader(
            input_files=[pdf_path],
            encoding='utf-8'
        ).load_data()
        
        print(f"成功處理上傳的PDF: {pdf_path}, 文件數量: {len(documents)}")
        return documents
    except Exception as e:
        print(f"處理上傳PDF錯誤: {e}")
        raise e


def clear_all_data(upload_folder=None, qdrant_url=None, qdrant_key=None, collection_name="operation_guide"):
    """清空所有資料，包括上傳文件和向量資料庫"""
    try:
        # 1. 清空上傳文件夾
        if upload_folder and os.path.exists(upload_folder):
            try:
                for filename in os.listdir(upload_folder):
                    filepath = os.path.join(upload_folder, filename)
                    if os.path.isfile(filepath):
                        try:
                            os.remove(filepath)
                            print(f"已刪除文件: {filepath}")
                        except Exception as e:
                            print(f"刪除文件失敗 {filepath}: {e}")
                print(f"已清空上傳文件夾: {upload_folder}")
            except Exception as e:
                print(f"清空上傳文件夾時發生錯誤: {e}")
        
        # 2. 清空向量資料庫
        if qdrant_url and qdrant_key:
            try:
                qdrant_client_instance = qdrant_client.QdrantClient(url=qdrant_url, api_key=qdrant_key)
                try:
                    qdrant_client_instance.delete_collection(collection_name=collection_name)
                    print(f"已刪除向量資料庫集合: {collection_name}")
                except Exception as e:
                    print(f"刪除向量資料庫集合失敗: {e}")
            except Exception as e:
                print(f"連接向量資料庫失敗: {e}")
        
        print("所有資料清空完成")
        return True
        
    except Exception as e:
        print(f"清空資料失敗: {e}")
        return False


def initialize_pdf_service(upload_folder=None):
    """初始化完整的 PDF 服務"""
    # 1. 載入設定
    config = load_config()
    
    # 2. 設定模型
    llm, embed_model = setup_models(config)
    
    # 3. 載入文件（包括上傳的文件）
    documents = load_documents(config['input_dir'], upload_folder)
    
    # 如果沒有文件，返回None
    if not documents:
        print("警告: 沒有找到任何PDF文件")
        return None
    
    # 4. 設定向量資料庫
    vector_store, storage_context = setup_vector_store(
        config['qdrant_url'], 
        config['qdrant_key']
    )
    
    # 5. 建立向量索引
    index = create_vector_index(documents, storage_context)
    
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

