import os
import logging
import json
from celery import Celery
from datetime import datetime

# Structured logging setup (JSON format)
def setup_logging():
    os.makedirs(os.path.dirname('application.log'), exist_ok=True)
    handler = logging.FileHandler('application.log', encoding='utf-8')
    formatter = logging.Formatter(json.dumps({
        'timestamp': '%(asctime)s',
        'level': '%(levelname)s',
        'component': 'instyper_worker',
        'message': '%(message)s',
        'correlation_id': '%(correlation_id)s',
        'user_id': '%(user_id)s',
        'request_id': '%(request_id)s'
    }))
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    if not root_logger.handlers:
        root_logger.addHandler(handler)

setup_logging()

def log_json(message, level='INFO', **kwargs):
    record = {
        'timestamp': datetime.utcnow().isoformat(),
        'level': level,
        'component': 'instyper_worker',
        'message': message,
        'correlation_id': kwargs.get('correlation_id'),
        'user_id': kwargs.get('user_id'),
        'request_id': kwargs.get('request_id'),
    }
    logging.log(getattr(logging, level.upper(), logging.INFO), json.dumps(record))

# Celery app placeholder (do not move or change original logic)
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'memory://')
CELERY_BACKEND_URL = os.environ.get('CELERY_BACKEND_URL', 'rpc://')
celery_app = Celery('instyper_worker', broker=CELERY_BROKER_URL, backend=CELERY_BACKEND_URL)

# Example placeholder task
def example_task():
    log_json('Example task executed', level='INFO')
    return 'This is a placeholder task.'
