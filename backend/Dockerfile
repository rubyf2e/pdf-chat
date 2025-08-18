# ============================================================================
# Backend Dockerfile - Flask API
# ============================================================================

FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 設定 Python 環境變數
ENV FLASK_ENV=${FLASK_ENV} \
    PORT_PDF_CHAT_BACKEND=${PORT_PDF_CHAT_BACKEND} \
    PORT_PDF_CHAT_FRONTEND=${PORT_PDF_CHAT_FRONTEND} \
    PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴文件
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式碼
COPY . .

# 建立必要的目錄
RUN mkdir -p uploads logs \
    && chmod 777 uploads

# 設定健康檢查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT_PDF_CHAT_BACKEND}/api/status || exit 1

# 暴露端口
EXPOSE ${PORT_PDF_CHAT_BACKEND}

# 使用 gunicorn 啟動
CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]
