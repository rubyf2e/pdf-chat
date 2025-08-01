import json 
import os
import base64
import re
from IPython.display import Image, display
from ollama import Client as OllamaClient
import ollama
from openai import AzureOpenAI
from langchain_openai import AzureChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama.llms import OllamaLLM


class ChatService:
    def __init__(self, config):
        self.config = config

    def chat(self, user_input, type='azure'):
        chat_map = {
            'azure': self.azure_chat,
            'azure_completions': self.azure_completions_chat,
            'gemini': self.gemini_chat,
            'ollama': self.ollama_chat,
            'ollama_client': self.ollama_client_chat,
        }
        
        func = chat_map.get(type, self.azure_chat)
        role_description = self.config["Base"]["CHAT_ROLE_DESCRIPTION"]
        try:
            return func(user_input, role_description)
        except Exception as e:
            return 'chat 模型需要升級，暫時無法提供服務'

    def azure_chat(self, user_input, role_description):
        llm = AzureChatOpenAI(
            openai_api_version=self.config["AzureOpenAIChat"]["VERSION"],
            azure_deployment=self.config["AzureOpenAIChat"]["DEPLOYMENT_NAME"],
            azure_endpoint=self.config["AzureOpenAIChat"]["END_POINT"],
            api_key=self.config["AzureOpenAIChat"]["KEY"],
        )
        messages = [
            ("system", role_description),
            ("human", user_input),
        ]
        
        try:
            response = llm.invoke(messages)
            return response.content
        except Exception as e:
            return 'chat 模型需要升級，暫時無法提供服務'

    def get_prompts_content(self, message_text_file):
        """獲取提示內容。"""
        with open(os.path.join(os.path.dirname(__file__), message_text_file), "r", encoding="utf-8") as f:
            return json.load(f)
        

    def set_prompts_content(self, prompts, role = "user", replace = "{user_input}", user_input = "user_input"):
        for msg in prompts:
            if msg["role"] == role:
                msg["content"] =  msg["content"].replace(replace, user_input)
                
        return prompts


    def azure_completions_chat_bot(self, user_input, message_text):
        client = AzureOpenAI(
            api_key=self.config["AzureOpenAIChat"]["KEY"],
            api_version=self.config["AzureOpenAIChat"]["VERSION"],
            azure_endpoint=self.config["AzureOpenAIChat"]["END_POINT"],
        )
        
        try:
            completion = client.chat.completions.create(
                model=self.config["AzureOpenAIChat"]["DEPLOYMENT_NAME"],
                messages=message_text,
                temperature=0,
                max_tokens=800,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                stop=None,
            )

            response_text = completion.choices[0].message.content
        
        except Exception as e:
            return 'chat 模型需要升級，暫時無法提供服務'
        
        try:
            response_dict = json.loads(response_text)
        except Exception as e:
            response_dict = {"error": "回傳內容不是合法 JSON", "raw": response_text}
        return response_dict
    
    def azure_completions_chat(self, user_input, role_description, message_text=None):
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

        try:
            completion = client.chat.completions.create(
                model=self.config["AzureOpenAIChat"]["DEPLOYMENT_NAME"],
                messages=message_text,
                temperature=0.7,
                max_tokens=800,
                top_p=0.95,
                frequency_penalty=0,
                presence_penalty=0,
                stop=None,
            )
            
            return completion.choices[0].message.content
        
        except Exception as e:
            return 'chat 模型需要升級，暫時無法提供服務'

    def gemini_chat(self, user_input, role_description):
        llm_gemini = ChatGoogleGenerativeAI(
            model=self.config["GeminiChat"]["MODEL_NAME"],
            google_api_key=self.config["GeminiChat"]["KEY"]
        )
        messages = [
            ("system", role_description),
            ("human", user_input),
        ]
        
        try:
            response_gemini = llm_gemini.invoke(messages)
            return response_gemini.content
        except Exception as e:
            return 'chat 模型需要升級，暫時無法提供服務'


    def ollama_chat(self, user_input, role_description):
        messages = [
            ("system", role_description),
            ("human", user_input),
        ]

        ollama_llm = OllamaLLM(model=self.config["OllamaLLM"]["MODEL_NAME"])
        
        try:
            response_ollama = ollama_llm.invoke(messages)
        except Exception as e:
            return 'chat 模型需要升級，暫時無法提供服務'

        return response_ollama
        
        
    def ollama_client_chat(self, user_input, role_description):
        client = OllamaClient(host=self.config["OllamaLLM"]["OLLAMA_CLIENT"])
        
        try:
            response = client.chat(
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
            )
            return response["message"]["content"]
    
        except Exception as e:
            return 'chat 模型需要升級，暫時無法提供服務'

    @staticmethod
    def ollama_client_image_chat(user_input, config):
        def image_to_base64(image_path):
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
            return encoded_string

        image_file_path = "road.png"
        base64_image = image_to_base64(image_file_path)

        try:
            response = ollama.chat(
                model=config["GeminiChat"]["MODEL_NAME"],
                messages=[
                    {"role": "user", "content": user_input, "images": [base64_image]}
                ],
            )
            display(Image(filename=image_file_path))
            return response["message"]["content"]
        
        except Exception as e:
            return 'chat 模型需要升級，暫時無法提供服務'

