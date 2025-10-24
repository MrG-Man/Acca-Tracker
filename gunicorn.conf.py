"""
Gunicorn Configuration for Football Predictions App
Production-ready WSGI server configuration
"""

import os
import multiprocessing

# Server socket
bind = f"{os.getenv('HOST', '0.0.0.0')}:{os.getenv('PORT', '5000')}"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
loglevel = os.getenv('LOG_LEVEL', 'info').lower()
accesslog = os.getenv('LOG_FILE', 'logs/access.log')
errorlog = os.getenv('LOG_FILE', 'logs/error.log')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'football_predictions'

# Server mechanics
daemon = False
pidfile = 'logs/gunicorn.pid'
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
keyfile = None
certfile = None

# Environment
raw_env = [
    f'FLASK_ENV={os.getenv("FLASK_ENV", "production")}',
    f'SECRET_KEY={os.getenv("SECRET_KEY", "")}',
]

# Preload application for better performance
preload_app = True

# Worker timeout and limits
graceful_timeout = 30
worker_abort_timeout = 60

def post_fork(server, worker):
    """Called after worker processes are forked"""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def pre_fork(server, worker):
    """Called before worker processes are forked"""
    server.log.info("Forking worker (pid: %s)", worker.pid)

def pre_exec(server):
    """Called before exec of worker process"""
    server.log.info("Worker process exec")

def when_ready(server):
    """Called when server is ready to serve requests"""
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    """Called when worker receives INT signal"""
    worker.log.info("Worker received INT signal")

def worker_abort(worker):
    """Called when worker is aborted"""
    worker.log.info("Worker aborted")