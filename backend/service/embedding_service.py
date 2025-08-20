import os
from typing import List, Dict, Any, Optional, Tuple
from .config_manager import ConfigManager
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

class EmbeddingService:
    def __init__(self, config_path: str = "config.ini"):
        self.config_manager = ConfigManager(config_path)
        self._embedding_models = {}
        self._qdrant_client = None
    
    def get_qdrant_client(self):
        """獲取 Qdrant 客戶端實例"""
        if self._qdrant_client is None:
            try:
                qdrant_config = self.config_manager.get_qdrant_config()
                if not qdrant_config.get('url'):
                    print("❌ Qdrant URL 未設定")
                    return None
                
                self._qdrant_client = QdrantClient(
                    url=qdrant_config['url'],
                    api_key=qdrant_config.get('api_key')
                )
                print("✅ Qdrant 客戶端連接成功")
                
            except Exception as e:
                print(f"❌ Qdrant 客戶端連接失敗: {e}")
                return None
        
        return self._qdrant_client
    
    def delete_qdrant_collection(self, collection_name: str):
        """刪除 Qdrant 集合"""
        try:
            client = self.get_qdrant_client()
            if not client:
                return False
            
            client.delete_collection(collection_name=collection_name)
            print(f"✅ 已刪除向量資料庫集合: {collection_name}")
            return True
            
        except Exception as e:
            print(f"❌ 刪除向量資料庫集合失敗: {e}")
            return False
    
    def list_qdrant_collections(self):
        """列出所有 Qdrant 集合"""
        try:
            client = self.get_qdrant_client()
            if not client:
                return []
            
            collections = client.get_collections()
            return [collection.name for collection in collections.collections]
            
        except Exception as e:
            print(f"❌ 獲取集合列表失敗: {e}")
            return []
    
    def collection_exists(self, collection_name: str):
        """檢查集合是否存在"""
        try:
            client = self.get_qdrant_client()
            if not client:
                return False
            
            collections = self.list_qdrant_collections()
            return collection_name in collections
            
        except Exception as e:
            print(f"❌ 檢查集合是否存在失敗: {e}")
            return False
    
    def get_huggingface_embeddings(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        try:
            if model_name not in self._embedding_models:
                self._embedding_models[model_name] = HuggingFaceEmbeddings(
                    model_name=model_name
                )
            
            return self._embedding_models[model_name]
            
        except ImportError:
            print("❌ langchain_huggingface 未安裝")
            return None
        except Exception as e:
            print(f"❌ HuggingFace Embeddings 錯誤: {e}")
            return None
    
    def get_gemini_embeddings(self, model: str = "models/text-embedding-004"):
        try:
            gemini_config = self.config_manager.get_gemini_config()
            if not gemini_config.get('api_key'):
                print("❌ Gemini API Key 未設定")
                return None
            
            key = f"gemini_{model}"
            if key not in self._embedding_models:
                self._embedding_models[key] = GoogleGenerativeAIEmbeddings(
                    model=model,
                    google_api_key=gemini_config['api_key']
                )
            
            return self._embedding_models[key]
            
        except ImportError:
            print("❌ langchain_google_genai 未安裝")
            return None
        except Exception as e:
            print(f"❌ Gemini Embeddings 錯誤: {e}")
            return None
    
    def get_azure_openai_embeddings(self, deployment_name: Optional[str] = None):
        try:
            from langchain_openai import AzureOpenAIEmbeddings
            
            azure_config = self.config_manager.get_azure_openai_config()
            
            required_keys = ['key', 'base', 'version']
            for key in required_keys:
                if not azure_config.get(key):
                    print(f"❌ Azure OpenAI {key} 未設定")
                    return None
            
            if not deployment_name:
                deployment_name = azure_config.get('deployment_name_embedding')
                if not deployment_name:
                    print("❌ Azure OpenAI embedding deployment 未設定")
                    return None
            
            cache_key = f"azure_{deployment_name}"
            if cache_key not in self._embedding_models:
                self._embedding_models[cache_key] = AzureOpenAIEmbeddings(
                    azure_deployment=deployment_name,
                    openai_api_version=azure_config['version'],
                    api_key=azure_config['key'],
                    azure_endpoint=azure_config['base']
                )
            
            return self._embedding_models[cache_key]
            
        except ImportError:
            print("❌ langchain_openai 未安裝")
            return None
        except Exception as e:
            print(f"❌ Azure OpenAI Embeddings 錯誤: {e}")
            return None
    
    def create_faiss_vectorstore(self, documents: List, embeddings, **kwargs):
        try:
            from langchain_community.vectorstores import FAISS
            
            return FAISS.from_documents(documents, embeddings, **kwargs)
            
        except ImportError:
            print("❌ langchain_community 未安裝")
            return None
        except Exception as e:
            print(f"❌ 建立 FAISS 向量資料庫錯誤: {e}")
            return None
    
    def create_qdrant_vectorstore(
        self, 
        collection_name: str, 
        embeddings, 
        path: str = "qdrant_storage",
        **kwargs
    ):
        try:
            client = QdrantClient(path=path)

            try:
                vector_size = kwargs.get('vector_size', 384) 
                distance = kwargs.get('distance', Distance.COSINE)
                
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=vector_size, distance=distance),
                )
                print(f"✓ 建立 Qdrant 集合: {collection_name}")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"✓ Qdrant 集合已存在: {collection_name}")
                else:
                    raise e
            
            return QdrantVectorStore(
                client=client,
                collection_name=collection_name,
                embedding=embeddings,
            )
            
        except ImportError:
            print("❌ langchain_qdrant 或 qdrant_client 未安裝")
            return None
        except Exception as e:
            print(f"❌ 建立 Qdrant 向量資料庫錯誤: {e}")
            return None
    
    def load_documents_from_text(self, file_path: str, **kwargs):
        try:
            from langchain_community.document_loaders import TextLoader
            
            loader = TextLoader(file_path, autodetect_encoding=True, **kwargs)
            return loader.load()
            
        except ImportError:
            print("❌ langchain_community 未安裝")
            return None
        except Exception as e:
            print(f"❌ 載入文字檔錯誤: {e}")
            return None
    
    def load_documents_from_pdf(self, file_paths: List[str], **kwargs):
        try:
            all_documents = []
            for file_path in file_paths:
                if os.path.exists(file_path):
                    loader = PyPDFLoader(file_path, **kwargs)
                    documents = loader.load()
                    all_documents.extend(documents)
                    print(f"✓ 載入 PDF: {file_path}")
                else:
                    print(f"⚠️ 找不到 PDF 檔案: {file_path}")
            
            return all_documents if all_documents else None
            
        except ImportError:
            print("❌ langchain_community 未安裝")
            return None
        except Exception as e:
            print(f"❌ 載入 PDF 檔案錯誤: {e}")
            return None
    
    def split_documents(
        self, 
        documents: List, 
        chunk_size: int = 1000, 
        chunk_overlap: int = 200,
        splitter_type: str = "recursive"
    ):
        try:
            if splitter_type == "recursive":
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )
            else:
                splitter = CharacterTextSplitter(
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )
            
            return splitter.split_documents(documents)
            
        except ImportError:
            print("❌ langchain text splitter 未安裝")
            return None
        except Exception as e:
            print(f"❌ 分割文件錯誤: {e}")
            return None
    
    def similarity_search(
        self, 
        vectorstore, 
        query: str, 
        k: int = 4, 
        with_score: bool = False
    ):
        try:
            if with_score:
                return vectorstore.similarity_search_with_score(query, k)
            else:
                return vectorstore.similarity_search(query, k)
                
        except Exception as e:
            print(f"❌ 相似度搜尋錯誤: {e}")
            return None
    
    def get_available_models(self) -> Dict[str, List[str]]:
        models = {
            "huggingface": [
                "sentence-transformers/all-MiniLM-L6-v2"
            ],
            "gemini": [
                "models/text-embedding-004"
            ],
            "azure_openai": [
                "text-embedding-3-large"
            ]
        }
        
        return models
    
    def create_embedding_pipeline(
        self,
        documents: List,
        embedding_type: str = "huggingface",
        vectorstore_type: str = "faiss",
        **kwargs
    ) -> Tuple[Any, Any]:
        try:
            # 取得 embedding 模型
            if embedding_type == "huggingface":
                model_name = kwargs.get('model_name', 'sentence-transformers/all-MiniLM-L6-v2')
                embeddings = self.get_huggingface_embeddings(model_name)
            elif embedding_type == "gemini":
                model = kwargs.get('model', 'models/text-embedding-004')
                embeddings = self.get_gemini_embeddings(model)
            elif embedding_type == "azure_openai":
                deployment_name = kwargs.get('deployment_name')
                embeddings = self.get_azure_openai_embeddings(deployment_name)
            else:
                print(f"❌ 不支援的 embedding 類型: {embedding_type}")
                return None, None
            
            if not embeddings:
                return None, None
            
            # 建立向量資料庫
            if vectorstore_type == "faiss":
                vectorstore = self.create_faiss_vectorstore(documents, embeddings)
            elif vectorstore_type == "qdrant":
                collection_name = kwargs.get('collection_name', 'default_collection')
                vectorstore = self.create_qdrant_vectorstore(collection_name, embeddings, **kwargs)
                if vectorstore and documents:
                    # 添加文件到 Qdrant
                    texts = [doc.page_content for doc in documents]
                    metadatas = [doc.metadata for doc in documents]
                    vectorstore.add_texts(texts=texts, metadatas=metadatas)
            else:
                print(f"❌ 不支援的向量資料庫類型: {vectorstore_type}")
                return embeddings, None
            
            return embeddings, vectorstore
            
        except Exception as e:
            print(f"❌ 建立 embedding 流水線錯誤: {e}")
            return None, None

