import os
import logging
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import requests
from datetime import datetime
from typing import Optional, Dict, List, Any
import json as _json
import shutil
import pyaudio
from celery import Celery
import importlib
import string
import jwt
from jwt import PyJWTError
from fastapi import status
from pydantic import BaseModel, ValidationError
import time
from collections import defaultdict, deque
from starlette.middleware.cors import CORSMiddleware
import functools
import asyncio

app = FastAPI()

# Structured logging setup (JSON format)
def setup_logging():
    os.makedirs(os.path.dirname('application.log'), exist_ok=True)
    handler = logging.FileHandler('application.log', encoding='utf-8')
    formatter = logging.Formatter(json.dumps({
        'timestamp': '%(asctime)s',
        'level': '%(levelname)s',
        'component': 'instyper_api',
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

JWT_SECRET = os.environ.get('JWT_SECRET', 'CHANGE_ME_TO_A_SECURE_SECRET')
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')

ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', 'http://localhost').split(',')

# Add CORS middleware for HTTP endpoints (if any)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# WebSocket origin check decorator
def require_allowed_origin(endpoint_func):
    async def wrapper(websocket: WebSocket, *args, **kwargs):
        origin = websocket.headers.get('origin')
        if origin not in ALLOWED_ORIGINS:
            log_json(f"Rejected WebSocket connection from disallowed origin: {origin}", level='WARN')
            await websocket.close(code=4403)
            return
        await endpoint_func(websocket, *args, **kwargs)
    return wrapper

# Patch all WebSocket endpoints to require allowed origin
for name, obj in list(globals().items()):
    if callable(obj) and hasattr(obj, '__name__') and obj.__name__.startswith('ws_'):
        globals()[name] = require_allowed_origin(obj)

def log_json(message, level='INFO', **kwargs):
    record = {
        'timestamp': datetime.utcnow().isoformat(),
        'level': level,
        'component': 'instyper_api',
        'message': message,
        'correlation_id': kwargs.get('correlation_id'),
        'user_id': kwargs.get('user_id'),
        'request_id': kwargs.get('request_id'),
        'client_ip': kwargs.get('client_ip'),
        'user_agent': kwargs.get('user_agent'),
    }
    # Remove sensitive data
    if 'token' in record:
        record['token'] = '***'
    logging.log(getattr(logging, level.upper(), logging.INFO), json.dumps(record))

# Patch all WebSocket endpoints to pass client_ip and user_agent to log_json
import functools

def enrich_logging(endpoint_func):
    @functools.wraps(endpoint_func)
    async def wrapper(websocket: WebSocket, *args, **kwargs):
        client_ip = websocket.client.host if websocket.client else None
        user_agent = websocket.headers.get('user-agent')
        kwargs['client_ip'] = client_ip
        kwargs['user_agent'] = user_agent
        await endpoint_func(websocket, *args, **kwargs)
    return wrapper

for name, obj in list(globals().items()):
    if callable(obj) and hasattr(obj, '__name__') and obj.__name__.startswith('ws_'):
        globals()[name] = enrich_logging(obj)

# Utility to verify JWT and extract claims
def verify_jwt(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except PyJWTError as e:
        return None

# Decorator for WebSocket authentication
def require_jwt_auth(endpoint_func):
    async def wrapper(websocket: WebSocket, *args, **kwargs):
        token = None
        # Try to get token from headers
        auth_header = websocket.headers.get('authorization')
        if auth_header and auth_header.lower().startswith('bearer '):
            token = auth_header[7:]
        # Optionally, support token in query params (for dev/testing)
        if not token:
            token = websocket.query_params.get('token')
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        claims = verify_jwt(token)
        if not claims:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        # Attach claims to kwargs for endpoint use
        kwargs['jwt_claims'] = claims
        kwargs['user_id'] = claims.get('sub')
        await endpoint_func(websocket, *args, **kwargs)
    return wrapper

# Patch all WebSocket endpoints to require JWT auth
for name, obj in list(globals().items()):
    if callable(obj) and hasattr(obj, '__name__') and obj.__name__.startswith('ws_'):
        globals()[name] = require_jwt_auth(obj)

# Business logic copy: translate_text
async def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """Translate text from source_lang to target_lang using Google Translate unofficial API."""
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": source_lang,
            "tl": target_lang,
            "dt": "t",
            "q": text
        }
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        translated = ''.join(segment[0] for segment in data[0])
        log_json(f"Translation succeeded", level='INFO')
        return translated
    except Exception as e:
        log_json(f"Translation error: {e}", level='ERROR')
        return text

# Copy of ModelsConfig for API use (do not move original)
class ModelsConfigAPI:
    def __init__(self):
        self._load_models_config()

    def _load_models_config(self) -> None:
        try:
            with open(os.path.expanduser('~/.instyper/models.json'), 'r', encoding='utf-8') as f:
                config = _json.load(f)
                self.all_models = config['models']
                self.defaults = config.get('defaults', {})
        except Exception as e:
            log_json(f"Error loading models config: {e}", level='ERROR')
            self.all_models = []
            self.defaults = {}

    def get_backend_models(self, backend: str) -> List[Dict[str, Any]]:
        return [m for m in self.all_models if m['backend'] == backend]

    def get_model_by_id(self, backend: str, model_id: str) -> Optional[Dict[str, Any]]:
        for m in self.all_models:
            if m['backend'] == backend and m['id'] == model_id:
                return m
        return None

    def get_model_by_name(self, backend: str, model_name: str) -> Optional[Dict[str, Any]]:
        for m in self.all_models:
            if m['backend'] == backend and m['model'] == model_name:
                return m
        return None

    def get_default_backend(self) -> Optional[str]:
        backends = [m['backend'] for m in self.all_models]
        if 'vosk' in backends:
            return 'vosk'
        return backends[0] if backends else None

    def get_default_model_for_backend(self, backend: str) -> Optional[str]:
        for m in self.all_models:
            if m['backend'] == backend and m.get('is_default'):
                return m['model']
        for m in self.all_models:
            if m['backend'] == backend:
                return m['model']
        return None

models_config_api = ModelsConfigAPI()

USER_ENV_PATH = os.path.expanduser('~/.instyper/.env')

# Import the worker's Celery app
worker_module = importlib.import_module('instyper_worker.__init__')
celery_app = getattr(worker_module, 'celery_app')

IGNORE_WHISPER_OUTPUTS = {
    "thank you.", "i'm sorry, i cannot help with that.", "i'm sorry.",
    "sorry.", "hello.", "hi.", "yes.", "no.", "okay.", "ok."
}

# --- Rate Limiting ---
RATE_LIMIT = int(os.environ.get('WS_RATE_LIMIT', 10))  # max requests per window
RATE_LIMIT_WINDOW = int(os.environ.get('WS_RATE_LIMIT_WINDOW', 5))  # seconds
_user_buckets = defaultdict(lambda: deque())

def check_rate_limit(user_id):
    now = time.time()
    bucket = _user_buckets[user_id]
    # Remove old timestamps
    while bucket and now - bucket[0] > RATE_LIMIT_WINDOW:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT:
        return False
    bucket.append(now)
    return True

# --- Input Validation Decorator ---
def validate_input(model):
    def decorator(endpoint_func):
        async def wrapper(websocket: WebSocket, *args, **kwargs):
            user_id = kwargs.get('user_id', 'anonymous')
            # Rate limiting
            if not check_rate_limit(user_id):
                log_json(f"Rate limit exceeded for user {user_id}", level='WARN', user_id=user_id)
                await websocket.send_json({'error': 'Rate limit exceeded'})
                return
            try:
                data = await websocket.receive_json()
                validated = model(**data)
            except ValidationError as ve:
                log_json(f"Input validation error: {ve}", level='WARN', user_id=user_id)
                await websocket.send_json({'error': 'Input validation error', 'details': ve.errors()})
                return
            except Exception as e:
                log_json(f"Malformed JSON: {e}", level='WARN', user_id=user_id)
                await websocket.send_json({'error': 'Malformed JSON'})
                return
            kwargs['validated_data'] = validated
            await endpoint_func(websocket, *args, **kwargs)
        return wrapper
    return decorator

# Example: update /ws/translate to use input validation and rate limiting
class TranslateInput(BaseModel):
    text: str
    source_lang: str
    target_lang: str

@require_jwt_auth
@validate_input(TranslateInput)
async def ws_translate(websocket: WebSocket, *args, **kwargs):
    validated = kwargs['validated_data']
    translated = await translate_text(validated.text, validated.source_lang, validated.target_lang)
    await websocket.send_json({'translated': translated})

# Patch the translate endpoint
app.websocket('/ws/translate')(ws_translate)

@app.websocket("/ws/get_hf_token_from_env")
@require_jwt_auth
@enrich_logging
async def ws_get_hf_token_from_env(websocket: WebSocket, *args, **kwargs):
    user_id = kwargs.get('user_id')
    client_ip = kwargs.get('client_ip')
    correlation_id = kwargs.get('correlation_id')
    await websocket.accept()
    try:
        while True:
            await websocket.receive_text()  # Just to keep the connection
            task = celery_app.send_task(
                'get_hf_token_from_env_task',
                args=[user_id, client_ip, correlation_id]
            )
            log_json(f"Triggered get_hf_token_from_env: {task.id}", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
            await websocket.send_json({'task_id': task.id})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (get_hf_token_from_env)", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    except Exception as e:
        log_json(f"WebSocket error (get_hf_token_from_env): {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        await websocket.close()

@app.websocket("/ws/save_hf_token_to_env")
@require_jwt_auth
@enrich_logging
async def ws_save_hf_token_to_env(websocket: WebSocket, *args, **kwargs):
    user_id = kwargs.get('user_id')
    client_ip = kwargs.get('client_ip')
    correlation_id = kwargs.get('correlation_id')
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            token = data.get('token')
            if not token:
                await websocket.send_json({'error': 'Missing required field: token'})
                continue
            task = celery_app.send_task(
                'save_hf_token_to_env_task',
                args=[token, user_id, client_ip, correlation_id]
            )
            log_json(f"Triggered save_hf_token_to_env: {task.id}", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
            await websocket.send_json({'task_id': task.id})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (save_hf_token_to_env)", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    except Exception as e:
        log_json(f"WebSocket error (save_hf_token_to_env): {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        await websocket.close()

@app.websocket("/ws/huggingface_login")
@require_jwt_auth
@enrich_logging
async def ws_huggingface_login(websocket: WebSocket, *args, **kwargs):
    user_id = kwargs.get('user_id')
    client_ip = kwargs.get('client_ip')
    correlation_id = kwargs.get('correlation_id')
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            token = data.get('token')
            if not token:
                await websocket.send_json({'error': 'Missing required field: token'})
                continue
            task = celery_app.send_task(
                'huggingface_login_task',
                args=[token, user_id, client_ip, correlation_id]
            )
            log_json(f"Triggered huggingface_login: {task.id}", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
            await websocket.send_json({'task_id': task.id})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (huggingface_login)", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    except Exception as e:
        log_json(f"WebSocket error (huggingface_login): {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        await websocket.close()

# Speech log pincode management (using SQLite config)
import hashlib
import sqlite3

CONFIG_DB_PATH = os.path.expanduser('~/.instyper/config.db')
CONFIG_TABLE_NAME = 'config'

@app.websocket("/ws/set_speech_log_pincode")
async def ws_set_speech_log_pincode(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            pincode = data.get('pincode')
            if not pincode:
                await websocket.send_json({'error': 'Missing required field: pincode'})
                continue
            hash_ = hashlib.sha256(pincode.encode('utf-8')).hexdigest()
            conn = sqlite3.connect(CONFIG_DB_PATH)
            cur = conn.cursor()
            cur.execute(f"CREATE TABLE IF NOT EXISTS {CONFIG_TABLE_NAME} (key TEXT PRIMARY KEY, value TEXT)")
            cur.execute(f"INSERT OR REPLACE INTO {CONFIG_TABLE_NAME} (key, value) VALUES (?, ?)", ('pincode', f'"{hash_}"'))
            conn.commit()
            conn.close()
            log_json("Set speech log pincode", level='INFO')
            await websocket.send_json({'status': 'ok'})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (set_speech_log_pincode)", level='INFO')
    except Exception as e:
        log_json(f"WebSocket error (set_speech_log_pincode): {e}", level='ERROR')
        await websocket.close()

@app.websocket("/ws/verify_speech_log_pincode")
async def ws_verify_speech_log_pincode(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            pincode = data.get('pincode')
            if not pincode:
                await websocket.send_json({'error': 'Missing required field: pincode'})
                continue
            hash_ = hashlib.sha256(pincode.encode('utf-8')).hexdigest()
            conn = sqlite3.connect(CONFIG_DB_PATH)
            cur = conn.cursor()
            cur.execute(f"CREATE TABLE IF NOT EXISTS {CONFIG_TABLE_NAME} (key TEXT PRIMARY KEY, value TEXT)")
            cur.execute(f"SELECT value FROM {CONFIG_TABLE_NAME} WHERE key = ?", ('pincode',))
            row = cur.fetchone()
            conn.close()
            is_valid = False
            if row and row[0].strip('"') == hash_:
                is_valid = True
            log_json("Verified speech log pincode", level='INFO')
            await websocket.send_json({'valid': is_valid})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (verify_speech_log_pincode)", level='INFO')
    except Exception as e:
        log_json(f"WebSocket error (verify_speech_log_pincode): {e}", level='ERROR')
        await websocket.close()

@app.websocket("/ws/is_speech_log_pincode_set")
async def ws_is_speech_log_pincode_set(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.receive_text()  # Just to keep the connection
            conn = sqlite3.connect(CONFIG_DB_PATH)
            cur = conn.cursor()
            cur.execute(f"CREATE TABLE IF NOT EXISTS {CONFIG_TABLE_NAME} (key TEXT PRIMARY KEY, value TEXT)")
            cur.execute(f"SELECT value FROM {CONFIG_TABLE_NAME} WHERE key = ?", ('pincode',))
            row = cur.fetchone()
            conn.close()
            is_set = bool(row and row[0])
            log_json("Checked if speech log pincode is set", level='INFO')
            await websocket.send_json({'is_set': is_set})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (is_speech_log_pincode_set)", level='INFO')
    except Exception as e:
        log_json(f"WebSocket error (is_speech_log_pincode_set): {e}", level='ERROR')
        await websocket.close()

@app.websocket("/ws/get_backend_models")
async def ws_get_backend_models(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            backend = data.get('backend')
            if not backend:
                await websocket.send_json({'error': 'Missing required field: backend'})
                continue
            models = models_config_api.get_backend_models(backend)
            log_json(f"Fetched models for backend {backend}", level='INFO')
            await websocket.send_json({'models': models})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (get_backend_models)", level='INFO')
    except Exception as e:
        log_json(f"WebSocket error (get_backend_models): {e}", level='ERROR')
        await websocket.close()

@app.websocket("/ws/get_model_by_id")
async def ws_get_model_by_id(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            backend = data.get('backend')
            model_id = data.get('model_id')
            if not backend or not model_id:
                await websocket.send_json({'error': 'Missing required fields: backend, model_id'})
                continue
            model = models_config_api.get_model_by_id(backend, model_id)
            log_json(f"Fetched model by id {model_id} for backend {backend}", level='INFO')
            await websocket.send_json({'model': model})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (get_model_by_id)", level='INFO')
    except Exception as e:
        log_json(f"WebSocket error (get_model_by_id): {e}", level='ERROR')
        await websocket.close()

@app.websocket("/ws/get_model_by_name")
async def ws_get_model_by_name(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            backend = data.get('backend')
            model_name = data.get('model_name')
            if not backend or not model_name:
                await websocket.send_json({'error': 'Missing required fields: backend, model_name'})
                continue
            model = models_config_api.get_model_by_name(backend, model_name)
            log_json(f"Fetched model by name {model_name} for backend {backend}", level='INFO')
            await websocket.send_json({'model': model})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (get_model_by_name)", level='INFO')
    except Exception as e:
        log_json(f"WebSocket error (get_model_by_name): {e}", level='ERROR')
        await websocket.close()

@app.websocket("/ws/get_default_backend")
async def ws_get_default_backend(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.receive_text()  # Just to keep the connection
            backend = models_config_api.get_default_backend()
            log_json(f"Fetched default backend", level='INFO')
            await websocket.send_json({'default_backend': backend})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (get_default_backend)", level='INFO')
    except Exception as e:
        log_json(f"WebSocket error (get_default_backend): {e}", level='ERROR')
        await websocket.close()

@app.websocket("/ws/get_default_model_for_backend")
async def ws_get_default_model_for_backend(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            backend = data.get('backend')
            if not backend:
                await websocket.send_json({'error': 'Missing required field: backend'})
                continue
            model = models_config_api.get_default_model_for_backend(backend)
            log_json(f"Fetched default model for backend {backend}", level='INFO')
            await websocket.send_json({'default_model': model})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (get_default_model_for_backend)", level='INFO')
    except Exception as e:
        log_json(f"WebSocket error (get_default_model_for_backend): {e}", level='ERROR')
        await websocket.close()

@app.websocket("/ws/initialize_user_directory")
async def ws_initialize_user_directory(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.receive_text()  # Just to keep the connection
            try:
                # Create user directories
                user_models_dir = os.path.expanduser('~/.instyper/models')
                os.makedirs(user_models_dir, exist_ok=True)
                # Copy README if not present
                repo_readme = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'README.md')
                user_readme = os.path.expanduser('~/.instyper/README.md')
                if os.path.isfile(repo_readme) and not os.path.isfile(user_readme):
                    shutil.copy2(repo_readme, user_readme)
                # Copy models if user models directory is empty
                repo_models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
                if not os.listdir(user_models_dir) and os.path.isdir(repo_models_dir):
                    for item in os.listdir(repo_models_dir):
                        src = os.path.join(repo_models_dir, item)
                        dst = os.path.join(user_models_dir, item)
                        if os.path.isdir(src):
                            shutil.copytree(src, dst, dirs_exist_ok=True)
                # Copy models.json if not present
                user_models_json = os.path.expanduser('~/.instyper/models.json')
                models_json_src = os.path.join(os.path.dirname(__file__), 'models.json')
                if not os.path.isfile(user_models_json) and os.path.isfile(models_json_src):
                    shutil.copy2(models_json_src, user_models_json)
                log_json("Initialized user directory", level='INFO')
                await websocket.send_json({'status': 'ok'})
            except Exception as e:
                log_json(f"Error initializing user directory: {e}", level='ERROR')
                await websocket.send_json({'error': str(e)})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (initialize_user_directory)", level='INFO')
    except Exception as e:
        log_json(f"WebSocket error (initialize_user_directory): {e}", level='ERROR')
        await websocket.close()

@app.websocket("/ws/human_size")
@require_jwt_auth
@enrich_logging
async def ws_human_size(websocket: WebSocket, *args, **kwargs):
    user_id = kwargs.get('user_id')
    client_ip = kwargs.get('client_ip')
    correlation_id = kwargs.get('correlation_id')
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            nbytes = data.get('nbytes')
            if nbytes is None:
                await websocket.send_json({'error': 'Missing required field: nbytes'})
                continue
            task = celery_app.send_task(
                'human_size_task',
                args=[nbytes, user_id, client_ip, correlation_id]
            )
            log_json(f"Triggered human_size: {task.id}", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
            await websocket.send_json({'task_id': task.id})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (human_size)", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    except Exception as e:
        log_json(f"WebSocket error (human_size): {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        await websocket.close()

@app.websocket("/ws/show_notification")
@require_jwt_auth
@enrich_logging
async def ws_show_notification(websocket: WebSocket, *args, **kwargs):
    user_id = kwargs.get('user_id')
    client_ip = kwargs.get('client_ip')
    correlation_id = kwargs.get('correlation_id')
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            title = data.get('title')
            message = data.get('message')
            level = data.get('level', 'info')
            if not title or not message:
                await websocket.send_json({'error': 'Missing required fields: title, message'})
                continue
            task = celery_app.send_task(
                'show_notification_task',
                args=[title, message, level, user_id, client_ip, correlation_id]
            )
            log_json(f"Triggered show_notification: {task.id}", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
            await websocket.send_json({'task_id': task.id})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (show_notification)", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    except Exception as e:
        log_json(f"WebSocket error (show_notification): {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        await websocket.close()

class AudioDeviceManagerAPI:
    def __init__(self):
        self.mic_names = []
        self.selected_mic_index = None
        self._discover_microphones()

    def _discover_microphones(self) -> None:
        p = pyaudio.PyAudio()
        try:
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info.get('maxInputChannels', 0) > 0:
                    self.mic_names.append(info['name'])
            self.selected_mic_index = 0 if self.mic_names else None
        finally:
            p.terminate()

    def get_mic_names(self) -> List[str]:
        return self.mic_names

    def set_mic_index(self, index: Optional[int]) -> None:
        self.selected_mic_index = index

@app.websocket("/ws/get_mic_names")
async def ws_get_mic_names(websocket: WebSocket):
    await websocket.accept()
    try:
        adm = AudioDeviceManagerAPI()
        while True:
            await websocket.receive_text()  # Just to keep the connection
            mic_names = adm.get_mic_names()
            log_json(f"Listed {len(mic_names)} microphones", level='INFO')
            await websocket.send_json({'mic_names': mic_names})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (get_mic_names)", level='INFO')
    except Exception as e:
        log_json(f"WebSocket error (get_mic_names): {e}", level='ERROR')
        await websocket.close()

@app.websocket("/ws/set_mic_index")
async def ws_set_mic_index(websocket: WebSocket):
    await websocket.accept()
    try:
        adm = AudioDeviceManagerAPI()
        while True:
            data = await websocket.receive_json()
            index = data.get('index')
            if index is None:
                await websocket.send_json({'error': 'Missing required field: index'})
                continue
            try:
                index = int(index)
                adm.set_mic_index(index)
                log_json(f"Set microphone index to {index}", level='INFO')
                await websocket.send_json({'status': 'ok'})
            except Exception as e:
                log_json(f"Error setting mic index: {e}", level='ERROR')
                await websocket.send_json({'error': str(e)})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (set_mic_index)", level='INFO')
    except Exception as e:
        log_json(f"WebSocket error (set_mic_index): {e}", level='ERROR')
        await websocket.close()

@app.websocket("/ws/celery_download_model")
@require_jwt_auth
@enrich_logging
async def ws_celery_download_model(websocket: WebSocket, *args, **kwargs):
    user_id = kwargs.get('user_id')
    client_ip = kwargs.get('client_ip')
    correlation_id = kwargs.get('correlation_id')
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            backend = data.get('backend')
            model_info = data.get('model_info')
            models_dir = data.get('models_dir')
            if not backend or not model_info or not models_dir:
                await websocket.send_json({'error': 'Missing required fields: backend, model_info, models_dir'})
                continue
            task = celery_app.send_task(
                'celery_download_model',
                args=[backend, model_info, models_dir, user_id, client_ip, correlation_id]
            )
            log_json(f"Triggered celery_download_model: {task.id}", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
            await websocket.send_json({'task_id': task.id})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (celery_download_model)", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    except Exception as e:
        log_json(f"WebSocket error (celery_download_model): {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        await websocket.close()

@app.websocket("/ws/task_status")
@require_jwt_auth
@enrich_logging
async def ws_task_status(websocket: WebSocket, *args, **kwargs):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            task_id = data.get('task_id')
            if not task_id:
                await websocket.send_json({'error': 'Missing required field: task_id'})
                continue
            result = celery_app.AsyncResult(task_id)
            response = {'task_id': task_id, 'status': result.status}
            if result.ready():
                response['result'] = result.result
            await websocket.send_json(response)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({'error': str(e)})
        await websocket.close()

@app.websocket("/ws/task_progress")
@require_jwt_auth
@enrich_logging
async def ws_task_progress(websocket: WebSocket, *args, **kwargs):
    user_id = kwargs.get('user_id')
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            task_id = data.get('task_id')
            if not task_id:
                await websocket.send_json({'error': 'Missing required field: task_id'})
                continue
            result = celery_app.AsyncResult(task_id)
            # Security: Only allow user to see their own tasks
            meta = result.info if isinstance(result.info, dict) else {}
            task_user_id = meta.get('user_id')
            if task_user_id and task_user_id != user_id:
                log_json(f"User {user_id} tried to access task {task_id} owned by {task_user_id}", level='WARN', user_id=user_id)
                await websocket.send_json({'error': 'Forbidden'})
                continue
            # Poll for progress until done
            while not result.ready():
                meta = result.info if isinstance(result.info, dict) else {}
                await websocket.send_json({'task_id': task_id, 'status': result.status, 'progress': meta.get('progress', 0)})
                await asyncio.sleep(1)
                result = celery_app.AsyncResult(task_id)
            # Send final result
            meta = result.info if isinstance(result.info, dict) else {}
            await websocket.send_json({'task_id': task_id, 'status': result.status, 'progress': meta.get('progress', 100), 'result': result.result})
            break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({'error': str(e)})
        await websocket.close()

@app.websocket("/ws/celery_change_config")
@require_jwt_auth
@enrich_logging
async def ws_celery_change_config(websocket: WebSocket, *args, **kwargs):
    user_id = kwargs.get('user_id')
    client_ip = kwargs.get('client_ip')
    correlation_id = kwargs.get('correlation_id')
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            key = data.get('key')
            value = data.get('value')
            if not key or value is None:
                await websocket.send_json({'error': 'Missing required fields: key, value'})
                continue
            task = celery_app.send_task(
                'celery_change_config',
                args=[key, value, user_id, client_ip, correlation_id]
            )
            log_json(f"Triggered celery_change_config: {task.id}", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
            await websocket.send_json({'task_id': task.id})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (celery_change_config)", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    except Exception as e:
        log_json(f"WebSocket error (celery_change_config): {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        await websocket.close()

@app.websocket("/ws/celery_set_backend")
@require_jwt_auth
@enrich_logging
async def ws_celery_set_backend(websocket: WebSocket, *args, **kwargs):
    user_id = kwargs.get('user_id')
    client_ip = kwargs.get('client_ip')
    correlation_id = kwargs.get('correlation_id')
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            backend_name = data.get('backend_name')
            if not backend_name:
                await websocket.send_json({'error': 'Missing required field: backend_name'})
                continue
            task = celery_app.send_task(
                'celery_set_backend',
                args=[backend_name, user_id, client_ip, correlation_id]
            )
            log_json(f"Triggered celery_set_backend: {task.id}", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
            await websocket.send_json({'task_id': task.id})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (celery_set_backend)", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    except Exception as e:
        log_json(f"WebSocket error (celery_set_backend): {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        await websocket.close()

@app.websocket("/ws/celery_set_model")
@require_jwt_auth
@enrich_logging
async def ws_celery_set_model(websocket: WebSocket, *args, **kwargs):
    user_id = kwargs.get('user_id')
    client_ip = kwargs.get('client_ip')
    correlation_id = kwargs.get('correlation_id')
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            model_name = data.get('model_name')
            if not model_name:
                await websocket.send_json({'error': 'Missing required field: model_name'})
                continue
            task = celery_app.send_task(
                'celery_set_model',
                args=[model_name, user_id, client_ip, correlation_id]
            )
            log_json(f"Triggered celery_set_model: {task.id}", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
            await websocket.send_json({'task_id': task.id})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (celery_set_model)", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    except Exception as e:
        log_json(f"WebSocket error (celery_set_model): {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        await websocket.close()

@app.websocket("/ws/celery_load_config")
@require_jwt_auth
@enrich_logging
async def ws_celery_load_config(websocket: WebSocket, *args, **kwargs):
    user_id = kwargs.get('user_id')
    client_ip = kwargs.get('client_ip')
    correlation_id = kwargs.get('correlation_id')
    await websocket.accept()
    try:
        while True:
            await websocket.receive_text()  # Just to keep the connection
            task = celery_app.send_task(
                'celery_load_config',
                args=[user_id, client_ip, correlation_id]
            )
            log_json(f"Triggered celery_load_config: {task.id}", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
            await websocket.send_json({'task_id': task.id})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (celery_load_config)", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    except Exception as e:
        log_json(f"WebSocket error (celery_load_config): {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        await websocket.close()

@app.websocket("/ws/celery_save_config")
@require_jwt_auth
@enrich_logging
async def ws_celery_save_config(websocket: WebSocket, *args, **kwargs):
    user_id = kwargs.get('user_id')
    client_ip = kwargs.get('client_ip')
    correlation_id = kwargs.get('correlation_id')
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            config_data = data.get('config_data')
            if not config_data:
                await websocket.send_json({'error': 'Missing required field: config_data'})
                continue
            task = celery_app.send_task(
                'celery_save_config',
                args=[config_data, user_id, client_ip, correlation_id]
            )
            log_json(f"Triggered celery_save_config: {task.id}", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
            await websocket.send_json({'task_id': task.id})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (celery_save_config)", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    except Exception as e:
        log_json(f"WebSocket error (celery_save_config): {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        await websocket.close()

@app.websocket("/ws/celery_reset_config")
@require_jwt_auth
@enrich_logging
async def ws_celery_reset_config(websocket: WebSocket, *args, **kwargs):
    user_id = kwargs.get('user_id')
    client_ip = kwargs.get('client_ip')
    correlation_id = kwargs.get('correlation_id')
    await websocket.accept()
    try:
        while True:
            await websocket.receive_text()  # Just to keep the connection
            task = celery_app.send_task(
                'celery_reset_config',
                args=[user_id, client_ip, correlation_id]
            )
            log_json(f"Triggered celery_reset_config: {task.id}", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
            await websocket.send_json({'task_id': task.id})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (celery_reset_config)", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    except Exception as e:
        log_json(f"WebSocket error (celery_reset_config): {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        await websocket.close()

@app.websocket("/ws/celery_load_speech_model")
@require_jwt_auth
@enrich_logging
async def ws_celery_load_speech_model(websocket: WebSocket, *args, **kwargs):
    user_id = kwargs.get('user_id')
    client_ip = kwargs.get('client_ip')
    correlation_id = kwargs.get('correlation_id')
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            backend = data.get('backend')
            model_name = data.get('model_name')
            models_dir = data.get('models_dir')
            if not backend or not model_name or not models_dir:
                await websocket.send_json({'error': 'Missing required fields: backend, model_name, models_dir'})
                continue
            task = celery_app.send_task(
                'celery_load_speech_model',
                args=[backend, model_name, models_dir, user_id, client_ip, correlation_id]
            )
            log_json(f"Triggered celery_load_speech_model: {task.id}", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
            await websocket.send_json({'task_id': task.id})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (celery_load_speech_model)", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    except Exception as e:
        log_json(f"WebSocket error (celery_load_speech_model): {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        await websocket.close()

@app.websocket("/ws/is_useless_whisper_output")
@require_jwt_auth
@enrich_logging
async def ws_is_useless_whisper_output(websocket: WebSocket, *args, **kwargs):
    user_id = kwargs.get('user_id')
    client_ip = kwargs.get('client_ip')
    correlation_id = kwargs.get('correlation_id')
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            text = data.get('text')
            if text is None:
                await websocket.send_json({'error': 'Missing required field: text'})
                continue
            task = celery_app.send_task(
                'is_useless_whisper_output_task',
                args=[text, user_id, client_ip, correlation_id]
            )
            log_json(f"Triggered is_useless_whisper_output: {task.id}", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
            await websocket.send_json({'task_id': task.id})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (is_useless_whisper_output)", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    except Exception as e:
        log_json(f"WebSocket error (is_useless_whisper_output): {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        await websocket.close()

@app.websocket("/ws/find_ckpts")
@require_jwt_auth
@enrich_logging
async def ws_find_ckpts(websocket: WebSocket, *args, **kwargs):
    user_id = kwargs.get('user_id')
    client_ip = kwargs.get('client_ip')
    correlation_id = kwargs.get('correlation_id')
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            obj = data.get('obj')
            if obj is None:
                await websocket.send_json({'error': 'Missing required field: obj'})
                continue
            task = celery_app.send_task(
                'find_ckpts_task',
                args=[obj, user_id, client_ip, correlation_id]
            )
            log_json(f"Triggered find_ckpts: {task.id}", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
            await websocket.send_json({'task_id': task.id})
    except WebSocketDisconnect:
        log_json("WebSocket disconnected (find_ckpts)", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    except Exception as e:
        log_json(f"WebSocket error (find_ckpts): {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        await websocket.close()
