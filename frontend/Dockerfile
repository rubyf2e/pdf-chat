# ============================================================================
# Frontend Dockerfile - React Application
# ============================================================================

# 多階段構建
# 第一階段：構建階段
FROM node:18-alpine AS build

# 設定工作目錄
WORKDIR /app
ARG NODE_ENV=production
ENV NODE_ENV=${NODE_ENV}

# 設定 PUBLIC_URL 以確保正確的靜態資源路徑
ARG PUBLIC_URL=/pdf-chat
ENV PUBLIC_URL=${PUBLIC_URL}

# 複製 package.json 和 package-lock.json
COPY package*.json ./

# 安裝依賴
RUN if [ "$NODE_ENV" = "production" ]; then npm ci --only=production; else npm ci; fi

# 複製源代碼
COPY . .

# 構建應用
RUN npm run build

# 第二階段：運行階段
FROM nginx:alpine

# 複製構建好的檔案到 nginx 默認目錄
COPY --from=build /app/build /usr/share/nginx/html

# 複製 nginx 配置模板和啟動腳本
COPY ./nginx.conf.template /etc/nginx/nginx.conf.template
COPY ./docker-entrypoint.sh /docker-entrypoint.sh

# 設定執行權限
RUN chmod +x /docker-entrypoint.sh

# 設定入口點
ENTRYPOINT ["/docker-entrypoint.sh"]

# 暴露端口
EXPOSE 80
