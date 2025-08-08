#!/bin/bash

# ============================================================================
# PDF Chat Application 部署腳本
# ============================================================================

set -e

echo "🚀 PDF Chat 應用部署腳本"
echo "=========================="

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 函數定義
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 檢查 Docker 是否安裝
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安裝，請先安裝 Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! command -v docker compose &> /dev/null; then
        print_error "Docker Compose 未安裝，請先安裝 Docker Compose"
        exit 1
    fi
    
    print_success "Docker 環境檢查通過"
}

# 清理舊容器和映像
cleanup() {
    print_status "清理舊容器和映像..."
    
    # 停止並移除舊容器
    docker-compose down --remove-orphans 2>/dev/null || true
    
    # 移除舊映像（可選）
    if [ "$1" = "--clean" ]; then
        docker system prune -f
        print_success "清理完成"
    fi
}

# 建置應用
build() {
    print_status "建置應用映像..."
    
    # 建置所有服務
    docker-compose build
    
    print_success "應用建置完成"
}

# 啟動服務
start() {
    print_status "啟動服務..."
    
    # 啟動生產環境
    docker-compose up -d
    
    print_success "服務啟動完成"
}

# 啟動開發環境
start_dev() {
    print_status "啟動開發環境..."
    
    # 啟動開發環境（包含開發前端）
    docker-compose --profile dev up -d
    
    print_success "開發環境啟動完成"
}

# 檢查服務狀態
check_status() {
    print_status "檢查服務狀態..."
    
    echo ""
    docker-compose ps
    echo ""
    
    # 檢查健康狀態
    print_status "等待服務健康檢查..."
    sleep 10
    
    # 測試後端 API
    if curl -f http://localhost:5009/api/status &> /dev/null; then
        print_success "後端 API 服務正常"
    else
        print_warning "後端 API 服務可能未就緒，請稍後再試"
    fi
    
    # 測試前端
    if curl -f http://localhost:3000 &> /dev/null; then
        print_success "前端服務正常"
    else
        print_warning "前端服務可能未就緒，請稍後再試"
    fi
}

# 顯示日誌
show_logs() {
    print_status "顯示服務日誌..."
    docker-compose logs -f
}

# 停止服務
stop() {
    print_status "停止服務..."
    docker-compose down
    print_success "服務已停止"
}

# 顯示使用說明
usage() {
    echo ""
    echo "使用方法："
    echo "  $0 [命令] [選項]"
    echo ""
    echo "命令："
    echo "  build          建置應用映像"
    echo "  start          啟動生產環境服務"
    echo "  dev            啟動開發環境服務"
    echo "  stop           停止所有服務"
    echo "  restart        重啟服務"
    echo "  status         檢查服務狀態"
    echo "  logs           顯示服務日誌"
    echo "  clean          清理並重新建置"
    echo ""
    echo "選項："
    echo "  --clean        清理舊映像和容器"
    echo ""
    echo "範例："
    echo "  $0 start              # 啟動生產環境"
    echo "  $0 dev                # 啟動開發環境"
    echo "  $0 clean              # 清理並重新建置"
    echo "  $0 logs               # 查看日誌"
    echo ""
}

# 主程序
main() {
    check_docker
    
    case "$1" in
        build)
            build
            ;;
        start)
            cleanup
            build
            start
            check_status
            ;;
        dev)
            cleanup
            build
            start_dev
            check_status
            ;;
        stop)
            stop
            ;;
        restart)
            stop
            start
            ;;
        status)
            check_status
            ;;
        logs)
            show_logs
            ;;
        clean)
            cleanup --clean
            build
            start
            check_status
            ;;
        *)
            usage
            exit 1
            ;;
    esac
}

# 執行主程序
main "$@"
