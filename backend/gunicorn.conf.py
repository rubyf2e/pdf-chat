import multiprocessing
import os

# 工作進程數 - 在容器環境中使用較少的進程以節省記憶體
workers = int(os.getenv('GUNICORN_WORKERS', '2'))

# 使用 gevent worker
worker_class = 'gevent'

# 綁定地址
bind = '0.0.0.0:' + os.getenv('PORT_PDF_CHAT_BACKEND', '5009')

# 超時設置 - 增加 SSE 長連線的 timeout
timeout = 3600  # 1 小時，適合 SSE 長連線
graceful_timeout = 30

# 保持連線
keepalive = 65

# 日誌設置
accesslog = '-'
errorlog = '-'
loglevel = "info"

reload = False  # 在生產環境關閉 reload
reload_extra_files = [
    "config.ini"
]

# 支援 SSE 串流
worker_connections = 1000

# 記憶體優化
max_requests = 1000
max_requests_jitter = 100
