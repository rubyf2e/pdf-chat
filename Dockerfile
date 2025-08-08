# ============================================================================
# PDF Chat Application - 完整部署 Dockerfile
# ============================================================================
# 此 Dockerfile 用於一次建置整個應用程式
# 建議使用 docker-compose.yml 進行開發和部署

# 階段 1: 前端建置
FROM node:18-alpine AS frontend-build

WORKDIR /app/frontend
ARG NODE_ENV=production
ENV NODE_ENV=${NODE_ENV}

# 複製前端檔案
COPY frontend/package*.json ./
RUN if [ "$NODE_ENV" = "production" ]; then npm ci --only=production; else npm ci; fi


COPY frontend/ ./
RUN npm run build

# 階段 2: 後端 + 整合
FROM python:3.11-slim AS production

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    curl \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# 設定工作目錄
WORKDIR /app

# 複製後端檔案
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./

# 複製前端建置檔案
COPY --from=frontend-build /app/frontend/build ./static

# 複製 nginx 配置
COPY frontend/nginx.conf /etc/nginx/nginx.conf

# 建立必要目錄
RUN mkdir -p uploads logs /var/log/nginx

# 建立啟動腳本
RUN echo '#!/bin/bash\n\
nginx\n\
exec gunicorn --bind 0.0.0.0:5009 --workers 4 app:app\n\
' > /app/start.sh && chmod +x /app/start.sh

# 暴露端口
EXPOSE 80 5009

# 健康檢查
HEALTHCHECK --interval=30s --timeout=30s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5009/api/status && wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

# 啟動服務
CMD ["/app/start.sh"]