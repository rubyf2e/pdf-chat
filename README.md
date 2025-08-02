# PDF Chat Application

## 簡介

PDF Chat 是一個基於 Flask 和 React 的應用程式，允許用戶上傳 PDF 文件並與 AI 進行互動式聊天，從而快速獲取文件中的相關資訊。

## 功能

- **文件上傳**：支持 PDF 文件的上傳，並自動處理和分析內容。

- **AI 聊天**：基於文件內容的智能問答。

- **流式聊天**：實時返回 AI 回應。

## 技術棧

- **前端**：React, SCSS

- **後端**：Flask, Python

- **AI 技術**：Llama-Index, Qdrant 向量存儲, 多模 LLM

## 文件結構

```plaintext
├── app.py                # Flask 後端主程式
├── config.ini            # 配置文件
├── package.json          # 前端依賴
├── requirements.txt      # 後端依賴
├── src/                  # 前端源代碼
│   ├── App.js            # React 主組件
│   ├── components/       # React 子組件
│   ├── scss/             # SCSS 樣式
│   └── utils/            # 工具函數
├── service/              # 後端服務邏輯
│   ├── chat_service.py   # 聊天服務
│   ├── pdf_service.py    # PDF 處理服務
├── uploads/              # 上傳的 PDF 文件
└── build/                # 前端編譯後的靜態文件
```
