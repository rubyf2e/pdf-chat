from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext, Document, Settings
from llama_index.core.node_parser import UnstructuredElementNodeParser
from llama_index.llms.gemini import Gemini
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.postprocessor import LongContextReorder

import qdrant_client
import configparser


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


def load_documents(input_dir):
    """載入 PDF 文件"""
    documents = SimpleDirectoryReader(
        input_dir=input_dir,
        recursive=True,
        required_exts=[".pdf"],
        exclude=["*.tmp"],
        encoding='utf-8'
    ).load_data()
    
    print(f"成功載入 {len(documents)} 個文件")
    return documents


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
        show_progress=True,
    )
    
    print("向量索引建立完成")
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
    return query_engine


def query_pdf(query_engine, question: str):
    """執行 PDF 查詢"""
    response = query_engine.query(question)
    response.print_response_stream()
    return response


def initialize_pdf_service():
    """初始化完整的 PDF 服務"""
    # 1. 載入設定
    config = load_config()
    
    # 2. 設定模型
    llm, embed_model = setup_models(config)
    
    # 3. 載入文件
    documents = load_documents(config['input_dir'])
    
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

