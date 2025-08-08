# PDF Chat Application

PDF 文件 AI 分析與對話系統，採用前後端分離架構。

## 🏗️ 專案架構

```
pdf_chat/
├── frontend/                # React 前端應用
│   ├── src/                 # 前端原始碼
│   ├── public/              # 靜態資源
│   ├── Dockerfile           # 前端 Docker 配置
│   ├── nginx.conf           # Nginx 配置
│   └── package.json         # 前端依賴
├── backend/                 # Flask 後端 API
│   ├── service/             # 業務邏輯服務
│   ├── uploads/             # 檔案上傳目錄
│   ├── Dockerfile           # 後端 Docker 配置
│   ├── app.py              # Flask 應用入口
│   ├── requirements.txt     # Python 依賴
│   └── config.ini          # 後端配置
├── docker-compose.yml       # Docker Compose 配置
├── Dockerfile              # 完整應用 Dockerfile
└── deploy.sh               # 部署腳本
```

## 🚀 快速開始

### 使用部署腳本（推薦）

```bash
# 啟動生產環境
./deploy.sh start

# 啟動開發環境
./deploy.sh dev

# 查看服務狀態
./deploy.sh status

# 查看日誌
./deploy.sh logs

# 停止服務
./deploy.sh stop
```

## 功能

- **文件上傳**：支持 PDF 文件的上傳，並自動處理和分析內容。

- **AI 聊天**：基於文件內容的智能問答。

- **流式聊天**：實時返回 AI 回應。

## 技術棧

- **前端**：React, SCSS

- **後端**：Flask, Python

- **AI 技術**：Llama-Index, Qdrant 向量存儲, 多模 LLM
