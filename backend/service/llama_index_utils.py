from typing import List, Optional
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext, Document, Settings
from llama_index.core.node_parser import UnstructuredElementNodeParser
from llama_index.llms.gemini import Gemini
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.postprocessor import LongContextReorder
import qdrant_client
from .config_manager import ConfigManager


class LlamaIndexProcessor:
    """LlamaIndex 文件處理和查詢類"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or ConfigManager()
        self.gemini_config = self.config_manager.get_gemini_config()
        self.qdrant_config = self.config_manager.get_qdrant_config()
        
        self._setup_models()
        
        self.index = None
        self.query_engine = None
    
    def _setup_models(self):
        """設定 LLM 和嵌入模型"""
        # LLM 設定
        self.llm = Gemini(
            model_name=self.gemini_config['model_name'], 
            api_key=self.gemini_config['api_key']
        )
        
        # 嵌入模型設定
        self.embed_model = GoogleGenAIEmbedding(
            api_key=self.gemini_config['api_key'],
            model=self.gemini_config['embedding_model'],
            task_type="RETRIEVAL_DOCUMENT"
        )
        
        # 全域設定
        Settings.llm = self.llm
        Settings.embed_model = self.embed_model
        Settings.node_parser = UnstructuredElementNodeParser(llm=self.llm)
    
    def load_documents(self, input_dir: str, required_exts: List[str] = [".pdf"]) -> List[Document]:
        loader = SimpleDirectoryReader(
            input_dir=input_dir,
            recursive=True,
            required_exts=required_exts,
            exclude=["*.tmp"],
            encoding='utf-8'
        )
        return loader.load_data()
    
    def create_qdrant_index(self, documents: List[Document], collection_name: str = "document_collection") -> VectorStoreIndex:
        # Qdrant 客戶端連接
        qdrant_client_instance = qdrant_client.QdrantClient(
            url=self.qdrant_config['url'],
            api_key=self.qdrant_config['api_key']
        )
        
        # 檢查並刪除現有集合
        try:
            qdrant_client_instance.get_collection(collection_name=collection_name)
            print(f"集合 '{collection_name}' 已存在，正在刪除...")
            qdrant_client_instance.delete_collection(collection_name=collection_name)
            print("刪除成功。")
        except Exception as e:
            print(f"集合 '{collection_name}' 不存在，無需刪除。")
        
        # 建立向量存儲
        vector_store = QdrantVectorStore(
            client=qdrant_client_instance,
            collection_name=collection_name,
            enable_hybrid=True
        )
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        # 建立向量索引
        self.index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            vector_store_kwargs={"enable_hybrid": True},
            show_progress=True
        )
        
        return self.index
    
    def create_query_engine(self, 
                          vector_store_query_mode: str = 'hybrid',
                          alpha: float = 0.5,
                          similarity_top_k: int = 5,
                          sparse_top_k: int = 5,
                          num_queries: int = 4,
                          streaming: bool = True):
        if not self.index:
            raise ValueError("請先建立索引")
        
        chat_llm = Gemini(
            model_name=self.gemini_config['model_name'],
            api_key=self.gemini_config['api_key']
        )
        
        self.query_engine = self.index.as_query_engine(
            llm=chat_llm,
            vector_store_query_mode=vector_store_query_mode,
            alpha=alpha,
            similarity_top_k=similarity_top_k,
            sparse_top_k=sparse_top_k,
            node_postprocessors=[LongContextReorder()],
            num_queries=num_queries,
            streaming=streaming
        )
        
        return self.query_engine
    
    def query(self, question: str) -> str:
        if not self.query_engine:
            raise ValueError("請先建立查詢引擎")
        
        response = self.query_engine.query(question)
        
        print(f"🔍 LlamaIndex 查詢: {question}")
        print(f"📝 響應類型: {type(response)}")
        
        # 檢查是否是 StreamingResponse
        if hasattr(response, 'response_gen'):
            print(f"✅ 檢測到 StreamingResponse，返回完整對象")
            return response  # 直接返回 StreamingResponse 對象
        else:
            # 一般模式 - 檢查響應是否有效
            print(f"📝 LlamaIndex 原始響應: {response}")
            if response is not None and str(response).strip():
                response_str = str(response)
                print(f"✅ 返回響應: {response_str}")
                return response_str
            else:
                print(f"⚠️ 響應為空或無效")
                return None  # 返回 None 而不是字串 "None"
    
    def process_documents_and_query(self, 
                                  input_dir: str, 
                                  question: str,
                                  collection_name: str = "document_collection",
                                  required_exts: List[str] = [".pdf"]) -> str:
        # 載入文件
        documents = self.load_documents(input_dir, required_exts)
        
        # 建立索引
        self.create_qdrant_index(documents, collection_name)
        
        # 建立查詢引擎
        self.create_query_engine()
        
        # 執行查詢
        return self.query(question)
