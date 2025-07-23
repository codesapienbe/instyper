import os
import logging
import json
from celery import Celery
from datetime import datetime
from celery import Task
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import base64
import secrets

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

@celery_app.task(bind=True, name='celery_download_model')
def celery_download_model(self, backend, model_info, models_dir, user_id=None, client_ip=None, correlation_id=None):
    log_json(
        f"Model download requested: backend={backend}, model_info={model_info}",
        level='INFO',
        user_id=user_id,
        client_ip=client_ip,
        correlation_id=correlation_id
    )
    try:
        # Simulate progress
        self.update_state(state='PROGRESS', meta={'progress': 0, 'user_id': user_id})
        import time
        time.sleep(1)
        self.update_state(state='PROGRESS', meta={'progress': 50, 'user_id': user_id})
        time.sleep(1)
        # Here you would call the actual model download logic
        self.update_state(state='PROGRESS', meta={'progress': 100, 'user_id': user_id})
        log_json(
            f"Model download completed: backend={backend}, model_info={model_info}",
            level='INFO',
            user_id=user_id,
            client_ip=client_ip,
            correlation_id=correlation_id
        )
        return {
            'status': 'ok',
            'backend': backend,
            'model_info': model_info,
            'models_dir': models_dir
        }
    except Exception as e:
        log_json(
            f"Model download failed: {e}",
            level='ERROR',
            user_id=user_id,
            client_ip=client_ip,
            correlation_id=correlation_id
        )
        return {'status': 'error', 'error': str(e)}

@celery_app.task(bind=True, name='celery_change_config')
def celery_change_config(self, key, value, user_id=None, client_ip=None, correlation_id=None):
    log_json(f"Config change requested: {key}={value}", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    try:
        self.update_state(state='PROGRESS', meta={'progress': 0, 'user_id': user_id})
        import time
        time.sleep(1)
        self.update_state(state='PROGRESS', meta={'progress': 50, 'user_id': user_id})
        time.sleep(1)
        # Simulate config change
        self.update_state(state='PROGRESS', meta={'progress': 100, 'user_id': user_id})
        log_json(f"Config change completed: {key}={value}", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'ok', 'key': key, 'value': value}
    except Exception as e:
        log_json(f"Config change failed: {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'error', 'error': str(e)}

@celery_app.task(bind=True, name='celery_set_backend')
def celery_set_backend(self, backend_name, user_id=None, client_ip=None, correlation_id=None):
    return celery_app.tasks['celery_change_config'].apply_async(args=['backend', backend_name, user_id, client_ip, correlation_id]).get()

@celery_app.task(bind=True, name='celery_set_model')
def celery_set_model(self, model_name, user_id=None, client_ip=None, correlation_id=None):
    return celery_app.tasks['celery_change_config'].apply_async(args=['model', model_name, user_id, client_ip, correlation_id]).get()

@celery_app.task(bind=True, name='celery_load_config')
def celery_load_config(self, user_id=None, client_ip=None, correlation_id=None):
    log_json(f"Load config requested", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    try:
        self.update_state(state='PROGRESS', meta={'progress': 0, 'user_id': user_id})
        import time
        time.sleep(1)
        self.update_state(state='PROGRESS', meta={'progress': 100, 'user_id': user_id})
        # Simulate config load
        config = {'example': 'config'}
        log_json(f"Config loaded", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'ok', 'config': config}
    except Exception as e:
        log_json(f"Config load failed: {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'error', 'error': str(e)}

@celery_app.task(bind=True, name='celery_save_config')
def celery_save_config(self, data, user_id=None, client_ip=None, correlation_id=None):
    log_json(f"Save config requested", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    try:
        self.update_state(state='PROGRESS', meta={'progress': 0, 'user_id': user_id})
        import time
        time.sleep(1)
        self.update_state(state='PROGRESS', meta={'progress': 100, 'user_id': user_id})
        # Simulate config save
        log_json(f"Config saved", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'ok'}
    except Exception as e:
        log_json(f"Config save failed: {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'error', 'error': str(e)}

@celery_app.task(bind=True, name='celery_reset_config')
def celery_reset_config(self, user_id=None, client_ip=None, correlation_id=None):
    log_json(f"Reset config requested", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    try:
        self.update_state(state='PROGRESS', meta={'progress': 0, 'user_id': user_id})
        import time
        time.sleep(1)
        self.update_state(state='PROGRESS', meta={'progress': 100, 'user_id': user_id})
        # Simulate config reset
        log_json(f"Config reset", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'ok'}
    except Exception as e:
        log_json(f"Config reset failed: {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'error', 'error': str(e)}

@celery_app.task(bind=True, name='celery_load_speech_model')
def celery_load_speech_model(self, backend, model_name, models_dir, user_id=None, client_ip=None, correlation_id=None):
    log_json(f"Speech model load requested: backend={backend}, model_name={model_name}", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    try:
        self.update_state(state='PROGRESS', meta={'progress': 0, 'user_id': user_id})
        import time
        time.sleep(1)
        self.update_state(state='PROGRESS', meta={'progress': 50, 'user_id': user_id})
        time.sleep(1)
        self.update_state(state='PROGRESS', meta={'progress': 100, 'user_id': user_id})
        # Simulate speech model load
        log_json(f"Speech model loaded: backend={backend}, model_name={model_name}", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'ok', 'backend': backend, 'model_name': model_name, 'models_dir': models_dir}
    except Exception as e:
        log_json(f"Speech model load failed: {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'error', 'error': str(e)}

# Helper for key derivation (copied from main app)
def _get_speech_log_key(pincode: str) -> bytes:
    salt_path = os.path.expanduser('~/.instyper/speech.log.salt')
    if not os.path.isfile(salt_path):
        salt = secrets.token_bytes(16)
        with open(salt_path, 'wb') as f:
            f.write(salt)
    else:
        with open(salt_path, 'rb') as f:
            salt = f.read()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(pincode.encode('utf-8')))
    return key

@celery_app.task(bind=True, name='append_encrypted_speech_log')
def append_encrypted_speech_log_task(self, text, pincode, user_id=None, client_ip=None, correlation_id=None):
    log_json(f"Append encrypted speech log requested", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    try:
        self.update_state(state='PROGRESS', meta={'progress': 0, 'user_id': user_id})
        import time
        time.sleep(1)
        key = _get_speech_log_key(pincode)
        f = Fernet(key)
        enc = f.encrypt(text.encode('utf-8'))
        log_path = os.path.expanduser('~/.instyper/speech.log.enc')
        with open(log_path, 'ab') as logf:
            logf.write(enc + b'\n')
        self.update_state(state='PROGRESS', meta={'progress': 100, 'user_id': user_id})
        log_json(f"Encrypted speech log appended", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'ok'}
    except Exception as e:
        log_json(f"Append encrypted speech log failed: {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'error', 'error': str(e)}

@celery_app.task(bind=True, name='decrypt_speech_log')
def decrypt_speech_log_task(self, pincode, user_id=None, client_ip=None, correlation_id=None):
    log_json(f"Decrypt speech log requested", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    try:
        self.update_state(state='PROGRESS', meta={'progress': 0, 'user_id': user_id})
        import time
        time.sleep(1)
        key = _get_speech_log_key(pincode)
        f = Fernet(key)
        log_path = os.path.expanduser('~/.instyper/speech.log.enc')
        lines = []
        with open(log_path, 'rb') as logf:
            for line in logf:
                line = line.strip()
                if not line:
                    continue
                try:
                    dec = f.decrypt(line).decode('utf-8')
                    lines.append(dec)
                except InvalidToken:
                    lines.append('[DECRYPTION FAILED]')
        self.update_state(state='PROGRESS', meta={'progress': 100, 'user_id': user_id})
        log_json(f"Speech log decrypted", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'ok', 'log': '\n'.join(lines)}
    except Exception as e:
        log_json(f"Decrypt speech log failed: {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'error', 'error': str(e)}

@celery_app.task(bind=True, name='get_hf_token_from_env')
def get_hf_token_from_env_task(self, user_id=None, client_ip=None, correlation_id=None):
    log_json(f"Get HuggingFace token from env requested", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    try:
        self.update_state(state='PROGRESS', meta={'progress': 0, 'user_id': user_id})
        import time
        time.sleep(1)
        env_path = os.path.expanduser('~/.instyper/.env')
        token = None
        if os.path.isfile(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip().startswith('HF_READONLY_TOKEN='):
                        token = line.strip().split('=', 1)[1]
                        break
        self.update_state(state='PROGRESS', meta={'progress': 100, 'user_id': user_id})
        log_json(f"HuggingFace token fetched", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'ok', 'token': token}
    except Exception as e:
        log_json(f"Get HuggingFace token failed: {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'error', 'error': str(e)}

@celery_app.task(bind=True, name='save_hf_token_to_env')
def save_hf_token_to_env_task(self, token, user_id=None, client_ip=None, correlation_id=None):
    log_json(f"Save HuggingFace token to env requested", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    try:
        self.update_state(state='PROGRESS', meta={'progress': 0, 'user_id': user_id})
        import time
        time.sleep(1)
        env_path = os.path.expanduser('~/.instyper/.env')
        if not os.path.isdir(os.path.dirname(env_path)):
            os.makedirs(os.path.dirname(env_path), exist_ok=True)
        already_present = False
        if os.path.isfile(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip().startswith('HF_READONLY_TOKEN='):
                        already_present = True
                        break
        if not already_present:
            with open(env_path, 'a', encoding='utf-8') as f:
                f.write(f'\nHF_READONLY_TOKEN={token}\n')
        self.update_state(state='PROGRESS', meta={'progress': 100, 'user_id': user_id})
        log_json(f"HuggingFace token saved", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'ok'}
    except Exception as e:
        log_json(f"Save HuggingFace token failed: {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'error', 'error': str(e)}

@celery_app.task(bind=True, name='huggingface_login')
def huggingface_login_task(self, token, user_id=None, client_ip=None, correlation_id=None):
    log_json(f"HuggingFace login requested", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    try:
        self.update_state(state='PROGRESS', meta={'progress': 0, 'user_id': user_id})
        import time
        time.sleep(1)
        try:
            from huggingface_hub import login as hf_login
        except ImportError:
            self.update_state(state='PROGRESS', meta={'progress': 100, 'user_id': user_id})
            log_json(f"huggingface_hub not installed", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
            return {'status': 'error', 'error': 'huggingface_hub not installed'}
        try:
            hf_login(token=token)
            # Save to env as well
            env_path = os.path.expanduser('~/.instyper/.env')
            if not os.path.isdir(os.path.dirname(env_path)):
                os.makedirs(os.path.dirname(env_path), exist_ok=True)
            already_present = False
            if os.path.isfile(env_path):
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip().startswith('HF_READONLY_TOKEN='):
                            already_present = True
                            break
            if not already_present:
                with open(env_path, 'a', encoding='utf-8') as f:
                    f.write(f'\nHF_READONLY_TOKEN={token}\n')
            self.update_state(state='PROGRESS', meta={'progress': 100, 'user_id': user_id})
            log_json(f"HuggingFace login succeeded", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
            return {'status': 'ok'}
        except Exception as e:
            self.update_state(state='PROGRESS', meta={'progress': 100, 'user_id': user_id})
            log_json(f"HuggingFace login failed: {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
            return {'status': 'error', 'error': f'HuggingFace login failed: {e}'}
    except Exception as e:
        log_json(f"HuggingFace login task failed: {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'error', 'error': str(e)}

@celery_app.task(bind=True, name='human_size')
def human_size_task(self, nbytes, user_id=None, client_ip=None, correlation_id=None):
    log_json(f"Human size requested: {nbytes}", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    try:
        self.update_state(state='PROGRESS', meta={'progress': 0, 'user_id': user_id})
        import time
        time.sleep(0.5)
        nbytes = int(nbytes)
        suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
        i = 0
        while nbytes >= 1024 and i < len(suffixes) - 1:
            nbytes /= 1024.0
            i += 1
        result = f"{nbytes:.1f} {suffixes[i]}"
        self.update_state(state='PROGRESS', meta={'progress': 100, 'user_id': user_id})
        log_json(f"Human size computed: {result}", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'ok', 'human_size': result}
    except Exception as e:
        log_json(f"Human size failed: {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'error', 'error': str(e)}

@celery_app.task(bind=True, name='show_notification')
def show_notification_task(self, title, message, level='info', user_id=None, client_ip=None, correlation_id=None):
    log_json(f"Show notification requested: {title} - {message}", level=level.upper(), user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    try:
        self.update_state(state='PROGRESS', meta={'progress': 0, 'user_id': user_id})
        import time
        time.sleep(0.5)
        # No actual UI popup, just log
        self.update_state(state='PROGRESS', meta={'progress': 100, 'user_id': user_id})
        log_json(f"Notification logged: {title} - {message}", level=level.upper(), user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'ok'}
    except Exception as e:
        log_json(f"Show notification failed: {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'error', 'error': str(e)}

@celery_app.task(bind=True, name='is_useless_whisper_output')
def is_useless_whisper_output_task(self, text, user_id=None, client_ip=None, correlation_id=None):
    log_json(f"Check useless whisper output requested: {text}", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    try:
        self.update_state(state='PROGRESS', meta={'progress': 0, 'user_id': user_id})
        import time
        time.sleep(0.5)
        import string
        IGNORE_WHISPER_OUTPUTS = {
            "thank you.", "i'm sorry, i cannot help with that.", "i'm sorry.",
            "sorry.", "hello.", "hi.", "yes.", "no.", "okay.", "ok."
        }
        text_low = text.lower().strip()
        is_useless = False
        if not text_low or all(c in string.punctuation for c in text_low):
            is_useless = True
        elif len(text_low) < 3:
            is_useless = True
        elif text_low in IGNORE_WHISPER_OUTPUTS:
            is_useless = True
        self.update_state(state='PROGRESS', meta={'progress': 100, 'user_id': user_id})
        log_json(f"Checked is_useless_whisper_output: {is_useless}", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'ok', 'is_useless': is_useless}
    except Exception as e:
        log_json(f"is_useless_whisper_output failed: {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'error', 'error': str(e)}

@celery_app.task(bind=True, name='find_ckpts')
def find_ckpts_task(self, obj, user_id=None, client_ip=None, correlation_id=None):
    log_json(f"Find ckpts requested", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
    try:
        self.update_state(state='PROGRESS', meta={'progress': 0, 'user_id': user_id})
        import time
        time.sleep(0.5)
        def find_ckpts_api(obj):
            if isinstance(obj, dict):
                for v in obj.values():
                    yield from find_ckpts_api(v)
            elif isinstance(obj, list):
                for v in obj:
                    yield from find_ckpts_api(v)
            elif isinstance(obj, str) and obj.endswith('.ckpt'):
                yield obj
        ckpts = list(find_ckpts_api(obj))
        self.update_state(state='PROGRESS', meta={'progress': 100, 'user_id': user_id})
        log_json(f"Checked find_ckpts, found {len(ckpts)} .ckpt files", level='INFO', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'ok', 'ckpt_files': ckpts}
    except Exception as e:
        log_json(f"find_ckpts failed: {e}", level='ERROR', user_id=user_id, client_ip=client_ip, correlation_id=correlation_id)
        return {'status': 'error', 'error': str(e)}
