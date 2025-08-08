# ============================================================================
# Backend Dockerfile - Flask API
# ============================================================================

FROM python:3.11-slim

# 設定環境變數
ENV PYTHONPATH=/app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 設定工作目錄
WORKDIR /app

# 複製 requirements.txt 並安裝 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式碼
COPY . .

# 建立必要的目錄
RUN mkdir -p uploads logs

# 建立非 root 使用者
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 5009

# 健康檢查
HEALTHCHECK --interval=30s --timeout=30s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5009/api/status || exit 1

# 啟動應用
CMD ["gunicorn", "--bind", "0.0.0.0:5009", "--workers", "4", "--timeout", "120", "--keep-alive", "5", "app:app"]
