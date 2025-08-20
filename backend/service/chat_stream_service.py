import time
from openai import AzureOpenAI
from langchain_openai import AzureChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama.llms import OllamaLLM
from ollama import Client as OllamaClient

class ChatStreamService:
    def __init__(self, config):
        self.config = config

    def chat_stream(self, user_input, type='gemini'):
        """流式聊天方法，產生流式回應"""
        chat_map = {
            'azure': self.azure_chat_stream,
            'azure_completions': self.azure_completions_chat_stream,
            'gemini': self.gemini_chat_stream,
            'ollama': self.ollama_chat_stream,
            'ollama_client': self.ollama_client_chat_stream,
        }
        
        func = chat_map.get(type, self.gemini_chat_stream)
        role_description = self.config["Base"]["CHAT_ROLE_DESCRIPTION"]
        try:
            yield from func(user_input, role_description)
        except Exception as e:
            yield 'chat 模型需要升級，暫時無法提供服務'

    def azure_chat_stream(self, user_input, role_description):
        """Azure 流式聊天"""
        try:
            llm = AzureChatOpenAI(
                openai_api_version=self.config["AzureOpenAIChat"]["VERSION"],
                azure_deployment=self.config["AzureOpenAIChat"]["DEPLOYMENT_NAME"],
                azure_endpoint=self.config["AzureOpenAIChat"]["END_POINT"],
                api_key=self.config["AzureOpenAIChat"]["KEY"],
                streaming=True
            )
            messages = [
                ("system", role_description),
                ("human", user_input),
            ]
            
            for chunk in llm.stream(messages):
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
        except Exception as e:
            print(f"Azure Completions Chat Stream Error: {e}")
            yield 'chat 模型需要升級，暫時無法提供服務'

    def azure_completions_chat_stream(self, user_input, role_description, message_text=None):
        """Azure Completions 流式聊天"""
        try:
            client = AzureOpenAI(
                api_key=self.config["AzureOpenAIChat"]["KEY"],
                api_version=self.config["AzureOpenAIChat"]["VERSION"],
                azure_endpoint=self.config["AzureOpenAIChat"]["END_POINT"],
            )
            
            if message_text is None:
                message_text = [
                    {
                        "role": "system",
                        "content": role_description,
                    }
                ]
                message_text.append({"role": "user", "content": user_input})

            stream = client.chat.completions.create(
                model=self.config["AzureOpenAIChat"]["DEPLOYMENT_NAME"],
                messages=message_text,
                temperature=0.7,
                max_tokens=800,
                top_p=0.95,
                frequency_penalty=0,
                presence_penalty=0,
                stop=None,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            print(f"Azure Completions Chat Stream Error: {e}")
            yield 'chat 模型需要升級，暫時無法提供服務'

    def gemini_chat_stream(self, user_input, role_description):
        """Gemini 流式聊天"""
        try:
            llm_gemini = ChatGoogleGenerativeAI(
                model=self.config["GeminiChat"]["MODEL_NAME"],
                google_api_key=self.config["GeminiChat"]["KEY"],
                model_kwargs={"streaming": True}
            )
            messages = [
                ("system", role_description),
                ("human", user_input),
            ]
            
            for chunk in llm_gemini.stream(messages):
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
        except Exception as e:
            yield 'chat 模型需要升級，暫時無法提供服務'
        
    def ollama_chat_stream(self, user_input, role_description):
        """Ollama 流式聊天"""
        try:
            messages = [
                ("system", role_description),
                ("human", user_input),
            ]

            ollama_llm = OllamaLLM(model=self.config["OllamaLLM"]["MODEL_NAME"])
            
            # OllamaLLM 可能不支援流式，這裡模擬分塊發送
            response = ollama_llm.invoke(messages)
            
            # 將回應分割成小塊來模擬流式
            words = response.split()
            chunk_size = 3  # 每次發送3個詞
            
            for i in range(0, len(words), chunk_size):
                chunk = ' '.join(words[i:i+chunk_size])
                if i + chunk_size < len(words):
                    chunk += ' '
                yield chunk
                time.sleep(0.1)  # 模擬網路延遲
                
        except Exception as e:
            yield 'chat 模型需要升級，暫時無法提供服務'

    def ollama_client_chat_stream(self, user_input, role_description):
        """Ollama Client 流式聊天"""
        try:
            # 使用 Config 類提供的動態 OLLAMA_CLIENT URL
            client = OllamaClient(host=Config.OLLAMA_CLIENT)
            
            stream = client.chat(
                model=self.config["OllamaLLM"]["MODEL_NAME"],
                messages=[
                    {
                        "role": "system",
                        "content": role_description,
                    },
                    {
                        "role": "user",
                        "content": user_input,
                    },
                ],
                stream=True
            )
            
            for chunk in stream:
                if chunk.get("message", {}).get("content"):
                    yield chunk["message"]["content"]
                    
        except Exception as e:
            yield 'chat 模型需要升級，暫時無法提供服務'
