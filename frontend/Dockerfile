# ============================================================================
# Frontend Dockerfile - React Application
# ============================================================================

# 階段 1: 開發環境
FROM node:18-alpine AS development

WORKDIR /app
ARG NODE_ENV=production
ENV NODE_ENV=${NODE_ENV}

# 複製 package.json 和 package-lock.json
COPY package*.json ./

# 安裝依賴
RUN npm ci

# 複製原始碼
COPY . .

# 暴露開發端口
EXPOSE 3000

# 開發環境啟動命令
CMD ["npm", "start"]

# 階段 2: 建置階段
FROM node:18-alpine AS build

WORKDIR /app

# 複製 package.json 和 package-lock.json
COPY package*.json ./

# 安裝依賴 (僅生產依賴)
RUN if [ "$NODE_ENV" = "production" ]; then npm ci --only=production; else npm ci; fi

# 複製原始碼
COPY . .

# 建置應用
RUN npm run build

# 階段 3: 生產環境 - 使用 nginx 提供靜態檔案
FROM nginx:alpine AS production

# 複製自訂 nginx 配置
COPY nginx.conf /etc/nginx/nginx.conf

# 複製建置後的檔案到 nginx
COPY --from=build /app/build /usr/share/nginx/html

# 暴露端口
EXPOSE 80

# 健康檢查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

# 啟動 nginx
CMD ["nginx", "-g", "daemon off;"]
