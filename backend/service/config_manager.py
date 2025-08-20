import configparser
import os
from typing import Dict, Any


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = 'config.ini'):
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        self._load_config()
    
    def _load_config(self):
        if os.path.exists(self.config_path):
            self.config.read(self.config_path)
        else:
            print(f"警告: 配置文件 {self.config_path} 不存在")
    
    def get_gemini_config(self) -> Dict[str, Any]:
        if 'GeminiChat' in self.config:
            return {
                'api_key': self.config.get('GeminiChat', 'KEY', fallback=''),
                'model_name': self.config.get('GeminiChat', 'CHAT_MODEL_NAME', fallback='gemini-2.5-pro'),
                'embedding_model': self.config.get('GeminiChat', 'EMBEDDING_MODEL_NAME', fallback='models/text-embedding-004')
            }
            
        return {
            'api_key': '',
            'model_name': 'gemini-2.5-pro',
            'embedding_model': 'models/text-embedding-004'
        }
    
    def get_qdrant_config(self) -> Dict[str, Any]:
        if 'QDRANT' in self.config:
            return {
                'url': self.config.get('QDRANT', 'URL', fallback=''),
                'api_key': self.config.get('QDRANT', 'API_KEY', fallback='')
            }
            
        return {
            'url': '',
            'api_key': ''
        }
    
    def get_azure_config(self) -> Dict[str, Any]:
        if 'AzureOpenAIChat' in self.config:
            return {
                'api_key': self.config.get('AzureOpenAIChat', 'KEY', fallback=''),
                'endpoint': self.config.get('AzureOpenAIChat', 'END_POINT', fallback=''),
                'deployment_name': self.config.get('AzureOpenAIChat', 'DEPLOYMENT_NAME', fallback=''),
                'api_version': self.config.get('AzureOpenAIChat', 'VERSION', fallback='')
            }
            
        return {
            'api_key': '',
            'endpoint': '',
            'deployment_name': '',
            'api_version': ''
        }
    
    def get_ollama_config(self) -> Dict[str, Any]:
        if 'OllamaLLM' in self.config:
            return {
                'model_name': self.config.get('OllamaLLM', 'MODEL_NAME', fallback=''),
                'client_url': self.config.get('OllamaLLM', 'OLLAMA_CLIENT', fallback='http://localhost:11434')
            }
            
        return {
            'model_name': '',
            'client_url': 'http://localhost:11434'
        }
    
    def get_base_config(self) -> Dict[str, Any]:
        if 'Base' in self.config:
            return {
                'input_dir': self.config.get('Base', 'INPUT_DIR', fallback='./uploads'),
                'ssl_enabled': self.config.getboolean('Base', 'SSL_ENABLED', fallback=False),
                'flask_debug': self.config.getboolean('Base', 'FLASK_DEBUG', fallback=False),
                'port_backend': self.config.getint('Base', 'PORT_PDF_CHAT_BACKEND', fallback=5009),
                'chat_role_description': self.config.get('Base', 'CHAT_ROLE_DESCRIPTION', fallback='你是一個有用的助手。')
            }
            
        return {
            'input_dir': './uploads',
            'ssl_enabled': False,
            'flask_debug': False,
            'port_backend': 5009,
            'chat_role_description': '你是一個有用的助手。'
        }
    
    def get_cors_config(self) -> Dict[str, Any]:
        if 'CORS' in self.config:
            origins = self.config.get('CORS', 'ALLOWED_ORIGINS', fallback='').split(',')
            return {
                'allowed_origins': [origin.strip() for origin in origins if origin.strip()]
            }
            
        return {
            'allowed_origins': []
        }
    
    def get_upload_config(self) -> Dict[str, Any]:
        """獲取文件上傳配置"""
        if 'Upload' in self.config:
            allowed_extensions_str = self.config.get('Upload', 'ALLOWED_EXTENSIONS', fallback='pdf')
            allowed_extensions = {ext.strip().lower() for ext in allowed_extensions_str.split(',') if ext.strip()}
            
            return {
                'allowed_extensions': allowed_extensions,
                'max_file_size': self.config.getint('Upload', 'MAX_FILE_SIZE', fallback=16 * 1024 * 1024)  # 16MB
            }
            
        return {
            'allowed_extensions': {'pdf'},
            'max_file_size': 16 * 1024 * 1024  # 16MB
        }

    def get_complete_config(self) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """獲取完整的配置，返回簡化配置和兼容格式配置"""
        # 獲取各種配置
        gemini_config = self.get_gemini_config()
        qdrant_config = self.get_qdrant_config()
        base_config = self.get_base_config()
        cors_config = self.get_cors_config()
        azure_config = self.get_azure_config()
        ollama_config = self.get_ollama_config()
        upload_config = self.get_upload_config()
        
        # 簡化配置格式
        config = {
            'flask_debug': base_config['flask_debug'],
            'base_origins': cors_config['allowed_origins'],
            'gemini_key': gemini_config['api_key'],
            'embedding_gemini_model': gemini_config['embedding_model'],
            'chat_gemini_model': gemini_config['model_name'],
            'qdrant_url': qdrant_config['url'],
            'qdrant_key': qdrant_config['api_key'],
            'input_dir': os.path.join(os.path.dirname(os.path.abspath(__file__)), base_config['input_dir']),
            'ssl_enabled': base_config['ssl_enabled'],
            'port_backend': base_config['port_backend'],
            'chat_role_description': base_config['chat_role_description'],
            'allowed_extensions': upload_config['allowed_extensions'],
            'max_file_size': upload_config['max_file_size']
        }
        
        # 兼容現有 ChatService 的格式
        config_sections = {
            'Base': {
                'CHAT_ROLE_DESCRIPTION': config['chat_role_description'],
                'SSL_ENABLED': config['ssl_enabled'],
                'PORT_PDF_CHAT_BACKEND': config['port_backend'],
                'INPUT_DIR': config['input_dir']
            },
            'GeminiChat': {
                'KEY': config['gemini_key'],
                'MODEL_NAME': config['chat_gemini_model'],
                'EMBEDDING_MODEL_NAME': config['embedding_gemini_model'],
                'CHAT_MODEL_NAME': config['chat_gemini_model']
            },
            'QDRANT': {
                'URL': config['qdrant_url'],
                'API_KEY': config['qdrant_key']
            },
            'CORS': {
                'ALLOWED_ORIGINS': ','.join(config['base_origins'])
            },
            'Upload': {
                'ALLOWED_EXTENSIONS': ','.join(config['allowed_extensions']),
                'MAX_FILE_SIZE': config['max_file_size']
            },
            'AzureOpenAIChat': azure_config,
            'OllamaLLM': ollama_config
        }
        
        return config, config_sections
    
    def get_protocol(self):
        base_config = self.get_base_config()
        return 'https' if base_config['ssl_enabled'] else 'http'

    def get_cors_origins(self):
        cors_config = self.get_cors_config()
        base_config = self.get_base_config()
        
        base_origins = cors_config['allowed_origins']
        protocol = 'https' if base_config['ssl_enabled'] else 'http'
        
        # 將所有 origins 轉換為正確的協議
        updated_origins = []
        for origin in base_origins:
            origin = origin.strip()
            if '://' in origin:
                # 替換現有協議
                origin = origin.replace('http://', f'{protocol}://').replace('https://', f'{protocol}://')
            updated_origins.append(origin)
        
        return updated_origins
