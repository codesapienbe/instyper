import os
import sys
import time
import threading
import platform
import atexit
import pyautogui
from plyer import notification
import pystray
from PIL import Image, ImageDraw
import tkinter as tk
from tkinter import ttk
import pyttsx3
import pyaudio
import json
from vosk import Model, KaldiRecognizer
import pyperclip
import shutil
import tempfile
import requests
import zipfile
from bs4 import BeautifulSoup
import wave
import pathlib
import urllib.request
import math
import numpy as np
import tkinter.messagebox
import logging
import abc

# Setup logging to file and console
LOG_PATH = os.path.expanduser('~/.instyper/instyper.log')
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
def log(msg, level='info'):
    getattr(logging, level)(msg)

# Central models directory in user home
USER_MODELS_DIR = os.path.expanduser('~/.instyper/models')
REPO_MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')

# Ensure ~/.instyper/models exists
os.makedirs(USER_MODELS_DIR, exist_ok=True)

# Copy README.md to ~/.instyper if not already present
REPO_README = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'README.md')
USER_README = os.path.expanduser('~/.instyper/README.md')
if os.path.isfile(REPO_README) and not os.path.isfile(USER_README):
    shutil.copy2(REPO_README, USER_README)

# If ~/.instyper/models is empty and repo models/ exists, copy all models
if not os.listdir(USER_MODELS_DIR) and os.path.isdir(REPO_MODELS_DIR):
    for item in os.listdir(REPO_MODELS_DIR):
        src = os.path.join(REPO_MODELS_DIR, item)
        dst = os.path.join(USER_MODELS_DIR, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)

CONFIG_PATH = os.path.expanduser('~/.instyper/config.json')

def load_config():
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(data):
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        # Log config save (summary)
        log(f"Config saved: {list(data.keys())}")
    except Exception as e:
        log(f"Error saving config: {e}")

def create_icon(is_active=False):
    """Create a simple icon for the system tray"""
    # Create a 64x64 image with a transparent background
    image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    
    # Platform-specific styling
    system = platform.system()
    if system == 'Darwin':  # macOS style
        color = '#FF3B30' if is_active else '#4CAF50'  # Red if active, green if inactive
        outline = None
    elif system == 'Windows':  # Windows style
        color = '#FF0000' if is_active else '#4CAF50'  # Red if active, green if inactive
        outline = '#2E7D32'
    else:  # Linux style
        color = '#FF0000' if is_active else '#4CAF50'  # Red if active, green if inactive
        outline = '#2E7D32'
    
    # Draw the microphone icon with platform-specific styling
    dc.ellipse((12, 12, 52, 52), fill=color, outline=outline)
    dc.rectangle((28, 28, 36, 52), fill=color, outline=outline)
    
    return image

def show_notification(title, message):
    """Show a platform-specific notification"""
    log(f"Notification: {title} - {message}")
    system = platform.system()
    if system == 'Darwin':  # macOS
        notification.notify(
            title=title,
            message=message,
            app_name='instyper',
            timeout=2,
            app_icon=None  # Use system default
        )
    elif system == 'Windows':  # Windows
        notification.notify(
            title=title,
            message=message,
            app_name='instyper',
            timeout=2,
            app_icon=None  # Use system default
        )
    else:  # Linux
        notification.notify(
            title=title,
            message=message,
            app_name='instyper',
            timeout=2,
            app_icon=None  # Use system default
        )

class ListeningIndicator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.configure(bg='#1DE9B6')
        self.label = tk.Label(self.root, text='...', font=('Arial', 18, 'bold'), fg='#00BFAE', bg='#1DE9B6')
        self.label.pack(ipadx=8, ipady=2)
        self.root.withdraw()
        self.update_position()
    def update_position(self):
        if self.root.winfo_viewable():
            x, y = pyautogui.position()
            self.root.geometry(f'+{x+20}+{y+20}')
        self.root.after(50, self.update_position)
    def show(self):
        self.root.deiconify()
    def hide(self):
        self.root.withdraw()
    def destroy(self):
        self.root.destroy()

# Ensure ~/.instyper/models.json exists and is up to date if missing
REPO_MODELS_JSON = os.path.join(os.path.dirname(__file__), 'models.json')
USER_MODELS_JSON = os.path.expanduser('~/.instyper/models.json')
if not os.path.isfile(USER_MODELS_JSON):
    shutil.copy2(REPO_MODELS_JSON, USER_MODELS_JSON)

# Load models.json (user copy) and get defaults
with open(USER_MODELS_JSON, 'r', encoding='utf-8') as f:
    MODELS_JSON = json.load(f)
ALL_MODELS = MODELS_JSON['models']
MODEL_DEFAULTS = MODELS_JSON.get('defaults', {})

def get_backend_models(backend):
    return [m for m in ALL_MODELS if m['backend'] == backend]

# Helper: get model by backend+id or backend+model
def get_model_by_id(backend, model_id):
    for m in ALL_MODELS:
        if m['backend'] == backend and m['id'] == model_id:
            return m
    return None

def get_model_by_name(backend, model_name):
    for m in ALL_MODELS:
        if m['backend'] == backend and m['model'] == model_name:
            return m
    return None

class ModelManagerDialog:
    def __init__(self, parent, backend, models_dir, on_download):
        self.top = tk.Toplevel(parent)
        self.top.title(f"Model Manager - {backend}")
        self.top.geometry("420x340")
        self.models_dir = models_dir
        self.backend = backend
        self.on_download = on_download
        self.model_var = tk.StringVar()
        self.progress_var = tk.StringVar(value='')
        tk.Label(self.top, text=f"Available models for {backend}", font=("Arial", 12, "bold")).pack(pady=8)
        self.listbox = tk.Listbox(self.top, width=60, height=10)
        self.listbox.pack(padx=10, pady=5, fill=tk.BOTH, expand=False)
        self.progress_label = tk.Label(self.top, textvariable=self.progress_var, font=("Arial", 10), fg="#00796B")
        self.progress_label.pack(pady=2)
        self.refresh_models()
        self.download_btn = tk.Button(self.top, text="Download selected model", command=self.download_or_select_model, state=tk.DISABLED)
        self.download_btn.pack(pady=8)
        tk.Button(self.top, text="Close", command=self.top.destroy).pack(pady=2)
        self.listbox.bind('<<ListboxSelect>>', self.on_select)
        self.selected_model = None
        self.downloading = False
        self.downloaded_models = set()
        self.selected_downloaded_model = None

    def refresh_models(self):
        self.listbox.delete(0, tk.END)
        self.available_models = []
        self.downloaded_models = set()
        if self.backend == 'vosk':
            try:
                resp = requests.get(REPO_MODELS_JSON, timeout=10)
                models = resp.json()
                for m in models:
                    name = m.get('name')
                    lang = m.get('lang', '')
                    size = m.get('filesize', None)
                    size_str = human_size(size)
                    notes = m.get('notes', '')
                    model_dir = os.path.join(self.models_dir, name)
                    is_downloaded = os.path.isdir(model_dir)
                    display = f"{name} | {lang} | {size_str} | {notes}"
                    if is_downloaded:
                        display += " (downloaded)"
                        self.downloaded_models.add(name)
                    self.listbox.insert(tk.END, display)
                    self.available_models.append(m)
            except Exception as e:
                self.listbox.insert(tk.END, f"Error fetching model list: {e}")
        elif self.backend == 'whisper':
            for m in get_backend_models('whisper'):
                model_dir = os.path.join(self.models_dir, m['model'])
                is_downloaded = os.path.isdir(model_dir) or any(f.startswith(m['model']) for f in os.listdir(self.models_dir))
                display = m['model']
                if is_downloaded:
                    display += " (downloaded)"
                    self.downloaded_models.add(m['model'])
                self.listbox.insert(tk.END, display)
                self.available_models.append(m)
        self.progress_var.set('')
        self.selected_model = None
        self.selected_downloaded_model = None
        self.download_btn.config(state=tk.DISABLED, text="Download selected model")

    def on_select(self, event):
        idx = self.listbox.curselection()
        if idx:
            model = self.available_models[idx[0]]
            name = model.get('name', model) if isinstance(model, dict) else model
            if name in self.downloaded_models:
                self.selected_model = model
                self.selected_downloaded_model = name
                self.progress_var.set('Model already downloaded. You can select it.')
                self.download_btn.config(state=tk.NORMAL, text="Select model")
            else:
                self.selected_model = model
                self.selected_downloaded_model = None
                self.download_btn.config(state=tk.NORMAL, text="Download selected model")
        else:
            self.selected_model = None
            self.selected_downloaded_model = None
            self.download_btn.config(state=tk.DISABLED, text="Download selected model")

    def download_or_select_model(self):
        if self.downloading or not self.selected_model:
            return
        name = self.selected_model.get('name', self.selected_model) if isinstance(self.selected_model, dict) else self.selected_model
        if name in self.downloaded_models:
            # Select the model as active for the backend
            self.set_active_model(name)
            self.progress_var.set(f"Model '{name}' selected as active.")
            return
        self.downloading = True
        self.progress_var.set('Starting download...')
        self.download_btn.config(state=tk.DISABLED)
        threading.Thread(target=self._download_model_thread, daemon=True).start()

    def set_active_model(self, name):
        # For Vosk, set the language in config to match the selected model
        if self.backend == 'vosk':
            # Find the language code for the selected model
            from .. import VoiceTyper  # relative import for context
            for lang_code, model_dir in VoiceTyper.LANG_MODELS.items():
                if model_dir == name:
                    config = load_config()
                    config['lang'] = lang_code
                    config.pop('custom_vosk_model', None)
                    save_config(config)
                    break
        elif self.backend == 'whisper':
            # For Whisper, set the model in config if needed (extend as needed)
            config = load_config()
            config['whisper_model'] = name
            save_config(config)
        # Optionally, trigger a reload in the main app if needed

    def download_model(self):
        # Deprecated, replaced by download_or_select_model
        pass

    def _download_model_thread(self):
        try:
            if self.backend == 'vosk':
                url = self.selected_model.get('url')
                name = self.selected_model.get('name')
                if not url or not name:
                    self.progress_var.set('Invalid model info.')
                    return
                dest_zip = os.path.join(self.models_dir, name + '.zip')
                # Download with progress
                def reporthook(blocknum, blocksize, totalsize):
                    if totalsize > 0:
                        percent = min(100, blocknum * blocksize * 100 // totalsize)
                        self.progress_var.set(f"Downloading: {percent}% ({human_size(blocknum*blocksize)} / {human_size(totalsize)})")
                        self.progress_label.update_idletasks()
                urllib.request.urlretrieve(url, dest_zip, reporthook)
                self.progress_var.set('Extracting...')
                with zipfile.ZipFile(dest_zip, 'r') as zip_ref:
                    zip_ref.extractall(self.models_dir)
                os.remove(dest_zip)
                self.progress_var.set('Done!')
                self.refresh_models()
            elif self.backend == 'whisper':
                import whisper
                model_name = self.selected_model['model']
                self.progress_var.set(f"Downloading {model_name} via whisper.load_model...")
                # Whisper does not provide progress, so just show a spinner
                spinner = ['|', '/', '-', '\\']
                done = [False]
                def spin():
                    i = 0
                    while not done[0]:
                        self.progress_var.set(f"Downloading {model_name}... {spinner[i%4]}")
                        self.progress_label.update_idletasks()
                        i += 1
                        time.sleep(0.2)
                spin_thread = threading.Thread(target=spin, daemon=True)
                spin_thread.start()
                try:
                    whisper.load_model(model_name, download_root=self.models_dir)
                finally:
                    done[0] = True
                self.progress_var.set('Done!')
                self.refresh_models()
            elif self.backend == 'speechbrain':
                try:
                    from speechbrain.pretrained import EncoderDecoderASR
                except ImportError:
                    self.progress_var.set('Please install speechbrain: pip install speechbrain')
                    return
                model_name = self.selected_model['model']
                self.progress_var.set(f"Downloading {model_name} via SpeechBrain API...")
                # Show a spinner while downloading/loading
                spinner = ['|', '/', '-', '\\']
                done = [False]
                def spin():
                    i = 0
                    while not done[0]:
                        self.progress_var.set(f"Downloading {model_name}... {spinner[i%4]}")
                        self.progress_label.update_idletasks()
                        i += 1
                        time.sleep(0.2)
                spin_thread = threading.Thread(target=spin, daemon=True)
                spin_thread.start()
                try:
                    EncoderDecoderASR.from_hparams(source=model_name, savedir=os.path.join(self.models_dir, model_name.replace('/', '_')))
                finally:
                    done[0] = True
                self.progress_var.set('Done!')
                self.refresh_models()
            elif self.backend == 'coqui-stt':
                try:
                    from huggingface_hub import snapshot_download
                except ImportError:
                    self.progress_var.set('Please install huggingface_hub: pip install huggingface_hub')
                    return
                model_name = self.selected_model['model']
                self.progress_var.set(f"Downloading {model_name} from HuggingFace...")
                spinner = ['|', '/', '-', '\\']
                done = [False]
                def spin():
                    i = 0
                    while not done[0]:
                        self.progress_var.set(f"Downloading {model_name}... {spinner[i%4]}")
                        self.progress_label.update_idletasks()
                        i += 1
                        time.sleep(0.2)
                spin_thread = threading.Thread(target=spin, daemon=True)
                spin_thread.start()
                try:
                    snapshot_download(repo_id=model_name, local_dir=os.path.join(self.models_dir, model_name.replace('/', '_')))
                finally:
                    done[0] = True
                self.progress_var.set('Done!')
                self.refresh_models()
            elif self.backend == 'paddlepaddle':
                try:
                    from paddlespeech.cli.asr.infer import ASRExecutor
                except ImportError:
                    self.progress_var.set('Please install paddlespeech and huggingface_hub: pip install paddlespeech huggingface_hub')
                    return
                model_name = self.selected_model['model']
                self.progress_var.set(f"Downloading {model_name} from HuggingFace...")
                spinner = ['|', '/', '-', '\\']
                done = [False]
                def spin():
                    i = 0
                    while not done[0]:
                        self.progress_var.set(f"Downloading {model_name}... {spinner[i%4]}")
                        self.progress_label.update_idletasks()
                        i += 1
                        time.sleep(0.2)
                spin_thread = threading.Thread(target=spin, daemon=True)
                spin_thread.start()
                try:
                    snapshot_download(repo_id=model_name, local_dir=os.path.join(self.models_dir, model_name.replace('/', '_')))
                finally:
                    done[0] = True
                self.progress_var.set('Done!')
                self.refresh_models()
            else:
                self.progress_var.set('Download not implemented for this backend.')
        except Exception as e:
            self.progress_var.set(f'Error: {e}')
        finally:
            self.downloading = False
            self.download_btn.config(state=tk.NORMAL)

class VoiceTyper:
    def __init__(self, indicator=None):
        self.is_listening = False
        self.recognition_thread = None
        self.stop_event = threading.Event()
        self.tts_engine = pyttsx3.init()
        self.indicator = indicator
        # Microphone selection using PyAudio
        p = pyaudio.PyAudio()
        self.mic_names = []
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info.get('maxInputChannels', 0) > 0:
                self.mic_names.append(info['name'])
        config = load_config()
        self.selected_mic_index = config.get('mic_index', 0 if self.mic_names else None)
        if not self.mic_names:
            self.tts_engine.say('No microphone was detected. Please check your audio settings.')
            self.tts_engine.runAndWait()
        else:
            self.tts_engine.say('Microphone found.')
            self.tts_engine.runAndWait()
        p.terminate()
        self.MODELS_ROOT = USER_MODELS_DIR
        self.MODELS_DIR = os.path.join(self.MODELS_ROOT, 'vosk')
        os.makedirs(self.MODELS_DIR, exist_ok=True)
        config = load_config()
        if platform.system() == 'Windows':
            self.BACKENDS = ['vosk', 'whisper', 'speechbrain', 'coqui-stt']
        else:
            self.BACKENDS = ['vosk', 'whisper', 'speechbrain', 'coqui-stt', 'paddlepaddle']
        self.selected_backend = config.get('backend', 'vosk')
        # Use default model from models.json if not set
        default_lang = MODEL_DEFAULTS.get('vosk', 'en').upper()
        self.selected_lang = config.get('lang', default_lang)
        self.LANG_MODELS = {m['id'].upper(): m['model'] for m in get_backend_models('vosk')}
        self.LANG_UI_NAMES = {m['id'].upper(): m['name'] for m in get_backend_models('vosk')}
        self.MODEL_META = {m['model']: m for m in get_backend_models('vosk')}
        if self.selected_backend == 'vosk' and self.selected_lang not in self.LANG_MODELS:
            log(f"Language {self.selected_lang} not supported. Defaulting to {default_lang}.")
            self.selected_lang = default_lang
        self.model_path = self.get_model_path(self.selected_lang)
        if self.selected_backend == 'vosk' and self.model_path and os.path.isdir(self.model_path):
            expected = all(os.path.isdir(os.path.join(self.model_path, d)) for d in ['conf', 'am', 'graph'])
            if expected:
                try:
                    self.model = Model(self.model_path)
                    show_notification('Instant Typer', f'Model loaded: {self.model_path}')
                except Exception as e:
                    show_notification('Instant Typer', f'Error loading model: {e}')
            else:
                log(f"Vosk model directory {self.model_path} does not contain expected model files.")
                show_notification('Instant Typer', f'Vosk model directory {self.model_path} is invalid.')
                self.model = None
        else:
            self.model = None

    def set_language(self, lang_code):
        config = load_config()
        custom_model = config.get('custom_vosk_model')
        self.selected_lang = lang_code
        self.MODELS_DIR = os.path.join(self.MODELS_ROOT, self.selected_backend)
        os.makedirs(self.MODELS_DIR, exist_ok=True)
        if self.selected_backend == 'vosk' and custom_model:
            self.model_path = os.path.join(self.MODELS_DIR, custom_model)
            if not os.path.isdir(self.model_path):
                show_notification('Instant Typer', f'Custom Vosk model directory {self.model_path} not found.')
                self.model = None
                return
            try:
                self.model = Model(self.model_path)
                show_notification('Instant Typer', f'Model loaded: {self.model_path}')
            except Exception as e:
                show_notification('Instant Typer', f'Error loading model: {e}')
            log(f"Switched to custom Vosk model: {custom_model}")
            self.tts_engine.say(f"Vosk model changed")
            self.tts_engine.runAndWait()
            return
        # Normal Vosk language switching
        if self.selected_backend == 'vosk':
            model_dir = self.LANG_MODELS.get(lang_code)
            if not model_dir:
                log(f"Language {lang_code} not supported for Vosk.")
                show_notification('Instant Typer', f'Language {lang_code} not supported for Vosk.')
                self.model = None
                return
            self.model_path = os.path.join(self.MODELS_DIR, model_dir)
            if not os.path.isdir(self.model_path):
                # Download model if missing
                model_info = next((m for m in get_backend_models('vosk') if m['model'] == model_dir), None)
                if model_info:
                    show_notification('Instant Typer', f'Downloading {model_info["name"]}...')
                    try:
                        VoskModelDownloader(model_info, self.MODELS_DIR, lambda: self.set_language(lang_code)).download()
                        show_notification('Instant Typer', f'Downloading and extracting {model_info["name"]}...')
                    except Exception as e:
                        show_notification('Instant Typer', f'Error downloading {model_info["name"]}: {e}')
                    self.model = None
                    return
                else:
                    show_notification('Instant Typer', f'Model info for {lang_code} not found.')
                    self.model = None
                    return
            try:
                self.model = Model(self.model_path)
                show_notification('Instant Typer', f'Model loaded: {self.model_path}')
            except Exception as e:
                show_notification('Instant Typer', f'Error loading model: {e}')
            log(f"Switched to Vosk language: {lang_code}")
            self.tts_engine.say(f"Language changed")
            self.tts_engine.runAndWait()
            return
        # Whisper: check and download model if missing
        if self.selected_backend == 'whisper':
            whisper_model = config.get('whisper_model', 'tiny')
            models_dir = os.path.join(USER_MODELS_DIR, 'whisper')
            files = os.listdir(models_dir) if os.path.isdir(models_dir) else []
            model_present = os.path.isdir(os.path.join(models_dir, whisper_model)) or any(f.startswith(whisper_model) for f in files)
            if not model_present:
                show_notification('Instant Typer', f'Downloading Whisper model {whisper_model}...')
                try:
                    WhisperModelDownloader(whisper_model, models_dir, lambda: self.set_language(lang_code)).download()
                    show_notification('Instant Typer', f'Downloading and extracting Whisper model {whisper_model}...')
                except Exception as e:
                    show_notification('Instant Typer', f'Error downloading Whisper model {whisper_model}: {e}')
                self.model = None
                return
            # Model is present, nothing else to do for Whisper here
        # Add logic for other backends if needed

    def get_model_path(self, lang_code):
        # Use backend-specific logic for model path
        if self.selected_backend == 'vosk':
            model_dir = self.LANG_MODELS.get(lang_code)
            if not model_dir:
                log(f"Language {lang_code} not supported for Vosk.")
                return None
            path = os.path.join(self.MODELS_DIR, model_dir)
            if not os.path.isdir(path):
                log(f"Model directory not found: {path}")
                # Do not attempt to auto-download here; just return None
                return None
            return path
        elif self.selected_backend == 'whisper':
            return self.MODELS_DIR
        elif self.selected_backend == 'speechbrain':
            return self.MODELS_DIR
        else:
            return self.MODELS_DIR

    def set_backend(self, backend_name):
        if backend_name not in self.BACKENDS:
            log(f"Backend {backend_name} not supported.")
            return
        # Use default model for backend if not set
        config = load_config()
        if backend_name == 'vosk':
            default_lang = MODEL_DEFAULTS.get('vosk', 'en').upper()
            if 'lang' not in config or config['lang'] not in self.LANG_MODELS:
                config['lang'] = default_lang
                save_config(config)
                self.set_language(default_lang)
        elif backend_name == 'whisper':
            default_model = MODEL_DEFAULTS.get('whisper', 'tiny')
            if 'whisper_model' not in config:
                config['whisper_model'] = default_model
                save_config(config)
        # Add similar logic for other backends if needed
        save_config({'backend': backend_name, 'lang': config.get('lang', MODEL_DEFAULTS.get('vosk', 'en').upper()), 'mic_index': self.selected_mic_index})
        was_listening = self.is_listening
        if was_listening:
            self.toggle_listening()  # Stop
        self.selected_backend = backend_name
        self.MODELS_DIR = os.path.join(self.MODELS_ROOT, backend_name)
        os.makedirs(self.MODELS_DIR, exist_ok=True)
        log(f"Switched to backend: {backend_name}")
        show_notification('Instant Typer', f'Switched to backend: {backend_name}')
        self.tts_engine.say(f"Backend changed to {backend_name}")
        self.tts_engine.runAndWait()
        if was_listening:
            self.toggle_listening()  # Restart
        self.refresh_menu()
        self.update_icon_title()
        # Check if model is available after switching backend
        if not self.is_model_available():
            self.notify_and_prompt_model_download(backend_name)

    def start(self):
        log("Instant Typer is running. Use the tray icon to start/stop voice typing.")
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.cleanup()

    def toggle_listening(self):
        self.is_listening = not self.is_listening
        if self.is_listening:
            show_notification('Instant Typer', 'Voice typing started')
            log("Voice typing started...")
            if self.indicator:
                self.indicator.label.config(text='Listening...')
                self.indicator.show()
            self.stop_event.clear()
            self.recognition_thread = threading.Thread(target=self.recognize_speech)
            self.recognition_thread.daemon = True
            self.recognition_thread.start()
        else:
            show_notification('Instant Typer', 'Voice typing stopped')
            log("Voice typing stopped.")
            self.stop_event.set()
            if self.recognition_thread:
                self.recognition_thread.join(timeout=2)
            if self.indicator:
                self.indicator.label.config(text='...')
                self.indicator.hide()

    def set_mic_index(self, idx):
        save_config({'backend': self.selected_backend, 'lang': self.selected_lang, 'mic_index': idx})
        was_listening = self.is_listening
        if was_listening:
            self.toggle_listening()  # Stop
        self.selected_mic_index = idx if idx >= 0 else None
        if was_listening:
            self.toggle_listening()  # Restart

    def recognize_speech(self):
        if self.selected_backend == 'vosk':
            if self.model is None:
                log("Vosk model is not loaded. Please download or select a valid model.")
                show_notification('Instant Typer', 'Vosk model is not loaded. Please download or select a valid model.')
                return
            if self.selected_mic_index is None:
                log("No microphone selected.")
                return
            p = pyaudio.PyAudio()
            try:
                stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, input_device_index=self.selected_mic_index, frames_per_buffer=8000)
                stream.start_stream()
                rec = KaldiRecognizer(self.model, 16000)
                log("Speak into your microphone. Press Ctrl+C to stop.")
                while not self.stop_event.is_set():
                    data = stream.read(4000, exception_on_overflow=False)
                    if rec.AcceptWaveform(data):
                        result = rec.Result()
                        text = json.loads(result).get('text', '')
                        if text and not self.stop_event.is_set():
                            log(f"Typing: {text}")
                            if self.indicator:
                                self.indicator.label.config(text='Typing...')
                            pyperclip.copy(text + " ")
                            pyautogui.hotkey('ctrl', 'v')
                            if self.indicator:
                                self.indicator.label.config(text='Listening...')
            except Exception as e:
                log(f"Error with Vosk recognition: {e}", 'error')
                show_notification('Instant Typer', f'Vosk error: {e}')
                if self.indicator:
                    self.indicator.label.config(text='Error')
            finally:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
                p.terminate()
        elif self.selected_backend == 'whisper':
            try:
                import whisper
            except ImportError:
                log("Whisper is not installed. Please install it with 'pip install openai-whisper'.")
                show_notification('Instant Typer', 'Whisper is not installed. Please install openai-whisper.')
                return
            if self.selected_mic_index is None:
                log("No microphone selected.")
                return
            p = pyaudio.PyAudio()
            try:
                stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, input_device_index=self.selected_mic_index, frames_per_buffer=8000)
                stream.start_stream()
                log("Speak into your microphone. Press Ctrl+C to stop.")
                config = load_config()
                whisper_model = config.get('whisper_model', 'base')
                model = whisper.load_model(whisper_model, download_root=self.MODELS_DIR)
                chunk = 4000
                buffer = b''
                min_audio_seconds = 2  # Minimum audio length for Whisper
                max_audio_seconds = 8  # Max segment before forced transcription
                min_audio_bytes = 16000 * 2 * min_audio_seconds  # 16kHz, 16bit
                max_audio_bytes = 16000 * 2 * max_audio_seconds
                while not self.stop_event.is_set():
                    data = stream.read(chunk, exception_on_overflow=False)
                    buffer += data
                    if len(buffer) >= min_audio_bytes:
                        # Save buffer to temp WAV file
                        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_wav:
                            wf = wave.open(tmp_wav, 'wb')
                            wf.setnchannels(1)
                            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
                            wf.setframerate(16000)
                            wf.writeframes(buffer[:max_audio_bytes])
                            wf.close()
                            wav_path = tmp_wav.name
                        log("Transcribing with Whisper...")
                        result = model.transcribe(wav_path, language=self.selected_lang.lower())
                        text = result.get('text', '').strip()
                        if text and not self.stop_event.is_set():
                            log(f"Typing: {text}")
                            if self.indicator:
                                self.indicator.label.config(text='Typing...')
                            pyperclip.copy(text + " ")
                            pyautogui.hotkey('ctrl', 'v')
                            if self.indicator:
                                self.indicator.label.config(text='Listening...')
                        buffer = b''
            except Exception as e:
                log(f"Error with Whisper recognition: {e}", 'error')
                show_notification('Instant Typer', f'Whisper error: {e}')
                if self.indicator:
                    self.indicator.label.config(text='Error')
            finally:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
                p.terminate()
        elif self.selected_backend == 'speechbrain':
            try:
                from speechbrain.pretrained import EncoderDecoderASR
            except ImportError:
                log("SpeechBrain is not installed. Please install it with 'pip install speechbrain'.")
                show_notification('Instant Typer', 'SpeechBrain is not installed. Please install speechbrain.')
                return
            if self.selected_mic_index is None:
                log("No microphone selected.")
                return
            p = pyaudio.PyAudio()
            try:
                stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, input_device_index=self.selected_mic_index, frames_per_buffer=8000)
                stream.start_stream()
                log("Speak into your microphone. Press Ctrl+C to stop.")
                chunk = 4000
                buffer = b''
                min_audio_seconds = 2
                max_audio_seconds = 8
                min_audio_bytes = 16000 * 2 * min_audio_seconds
                max_audio_bytes = 16000 * 2 * max_audio_seconds
                asr = EncoderDecoderASR.from_hparams(source='speechbrain/asr-transformer-transformerlm-librispeech', savedir=os.path.join(self.MODELS_DIR, 'speechbrain_asr-transformer-transformerlm-librispeech'))
                while not self.stop_event.is_set():
                    data = stream.read(chunk, exception_on_overflow=False)
                    buffer += data
                    if len(buffer) >= min_audio_bytes:
                        # Save buffer to temp WAV file
                        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_wav:
                            wf = wave.open(tmp_wav, 'wb')
                            wf.setnchannels(1)
                            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
                            wf.setframerate(16000)
                            wf.writeframes(buffer[:max_audio_bytes])
                            wf.close()
                            wav_path = tmp_wav.name
                        log("Transcribing with SpeechBrain...")
                        text = asr.transcribe_file(wav_path)
                        if text and not self.stop_event.is_set():
                            log(f"Typing: {text}")
                            if self.indicator:
                                self.indicator.label.config(text='Typing...')
                            pyperclip.copy(text + " ")
                            pyautogui.hotkey('ctrl', 'v')
                            if self.indicator:
                                self.indicator.label.config(text='Listening...')
                        buffer = b''
            except Exception as e:
                log(f"Error with SpeechBrain recognition: {e}", 'error')
                show_notification('Instant Typer', f'SpeechBrain error: {e}')
                if self.indicator:
                    self.indicator.label.config(text='Error')
            finally:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
                p.terminate()
        elif self.selected_backend == 'coqui-stt':
            try:
                import stt
            except ImportError:
                log("Coqui STT is not installed. Please install it with 'pip install stt huggingface_hub'.")
                show_notification('Instant Typer', 'Coqui STT is not installed. Please install stt and huggingface_hub.')
                return
            if self.selected_mic_index is None:
                log("No microphone selected.")
                return
            p = pyaudio.PyAudio()
            try:
                stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, input_device_index=self.selected_mic_index, frames_per_buffer=8000)
                stream.start_stream()
                log("Speak into your microphone. Press Ctrl+C to stop.")
                chunk = 4000
                buffer = b''
                min_audio_seconds = 2
                max_audio_seconds = 8
                min_audio_bytes = 16000 * 2 * min_audio_seconds
                max_audio_bytes = 16000 * 2 * max_audio_seconds
                model_dir = os.path.join(self.MODELS_DIR, 'coqui_stt-en')
                model_path = None
                scorer_path = None
                # Find .tflite or .pbmm model file
                for f in os.listdir(model_dir):
                    if f.endswith('.tflite') or f.endswith('.pbmm'):
                        model_path = os.path.join(model_dir, f)
                    if f.endswith('.scorer'):
                        scorer_path = os.path.join(model_dir, f)
                if not model_path:
                    show_notification('Instant Typer', 'No Coqui STT model found. Please download first.')
                    return
                model = stt.Model(model_path)
                if scorer_path:
                    model.enableExternalScorer(scorer_path)
                while not self.stop_event.is_set():
                    data = stream.read(chunk, exception_on_overflow=False)
                    buffer += data
                    if len(buffer) >= min_audio_bytes:
                        # Save buffer to temp WAV file
                        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_wav:
                            wf = wave.open(tmp_wav, 'wb')
                            wf.setnchannels(1)
                            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
                            wf.setframerate(16000)
                            wf.writeframes(buffer[:max_audio_bytes])
                            wf.close()
                            wav_path = tmp_wav.name
                        log("Transcribing with Coqui STT...")
                        import numpy as np
                        import wave as pywave
                        with pywave.open(wav_path, 'rb') as wf:
                            frames = wf.readframes(wf.getnframes())
                            audio = np.frombuffer(frames, np.int16)
                        text = model.stt(audio)
                        if text and not self.stop_event.is_set():
                            log(f"Typing: {text}")
                            if self.indicator:
                                self.indicator.label.config(text='Typing...')
                            pyperclip.copy(text + " ")
                            pyautogui.hotkey('ctrl', 'v')
                            if self.indicator:
                                self.indicator.label.config(text='Listening...')
                        buffer = b''
            except Exception as e:
                log(f"Error with Coqui STT recognition: {e}", 'error')
                show_notification('Instant Typer', f'Coqui STT error: {e}')
                if self.indicator:
                    self.indicator.label.config(text='Error')
            finally:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
                p.terminate()
        elif self.selected_backend == 'paddlepaddle' and platform.system() != 'Windows':
            try:
                from paddlespeech.cli.asr.infer import ASRExecutor
            except ImportError:
                log("PaddleSpeech is not installed. Please install it with 'pip install paddlespeech huggingface_hub'.")
                show_notification('Instant Typer', 'PaddleSpeech is not installed. Please install paddlespeech and huggingface_hub.')
                return
            if self.selected_mic_index is None:
                log("No microphone selected.")
                return
            p = pyaudio.PyAudio()
            try:
                stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, input_device_index=self.selected_mic_index, frames_per_buffer=8000)
                stream.start_stream()
                log("Speak into your microphone. Press Ctrl+C to stop.")
                chunk = 4000
                buffer = b''
                min_audio_seconds = 2
                max_audio_seconds = 8
                min_audio_bytes = 16000 * 2 * min_audio_seconds
                max_audio_bytes = 16000 * 2 * max_audio_seconds
                model_dir = os.path.join(self.MODELS_DIR, 'paddlespeech_asr-conformer-en')
                asr = ASRExecutor()
                while not self.stop_event.is_set():
                    data = stream.read(chunk, exception_on_overflow=False)
                    buffer += data
                    if len(buffer) >= min_audio_bytes:
                        # Save buffer to temp WAV file
                        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_wav:
                            wf = wave.open(tmp_wav, 'wb')
                            wf.setnchannels(1)
                            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
                            wf.setframerate(16000)
                            wf.writeframes(buffer[:max_audio_bytes])
                            wf.close()
                            wav_path = tmp_wav.name
                        log("Transcribing with PaddleSpeech...")
                        text = asr(audio_file=wav_path, model='conformer', lang='en', sample_rate=16000, config=None, ckpt_path=None, device='cpu')
                        if text and not self.stop_event.is_set():
                            log(f"Typing: {text}")
                            if self.indicator:
                                self.indicator.label.config(text='Typing...')
                            pyperclip.copy(text + " ")
                            pyautogui.hotkey('ctrl', 'v')
                            if self.indicator:
                                self.indicator.label.config(text='Listening...')
                        buffer = b''
            except Exception as e:
                log(f"Error with PaddleSpeech recognition: {e}", 'error')
                show_notification('Instant Typer', f'PaddleSpeech error: {e}')
                if self.indicator:
                    self.indicator.label.config(text='Error')
            finally:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
                p.terminate()
        else:
            log(f"Unknown backend: {self.selected_backend}", 'error')
            show_notification('Instant Typer', f'Unknown backend: {self.selected_backend}')

    def cleanup(self):
        log("Cleaning up...")
        self.stop_event.set()
        if self.recognition_thread and self.recognition_thread.is_alive():
            self.recognition_thread.join(timeout=2)
        log("Instant Typer stopped.")

    def show_model_manager(self):
        def on_download(backend, models_dir):
            show_notification('Model Manager', f'Download for {backend} not implemented yet.')
        ModelManagerDialog(self.indicator.root, self.selected_backend, self.MODELS_DIR, on_download)

    def refresh_menu(self):
        icon = pystray.Icon("instyper")
        icon.icon = create_icon()
        self.update_icon_title()
        icon.update_menu()

    def update_icon_title(self):
        backend, model = self.selected_backend, self.model_path
        icon = pystray.Icon("instyper")
        icon.title = f"Instant Typer ({backend}: {model})"

    def notify_and_prompt_model_download(self, backend, lang_code=None):
        # Show notification and open Model menu if model is missing
        if backend == 'vosk':
            model_name = None
            if lang_code:
                model_name = self.LANG_MODELS.get(lang_code)
            else:
                config = load_config()
                lang = config.get('lang', 'EN')
                model_name = self.LANG_MODELS.get(lang)
            show_notification('Instant Typer', f'Model for {lang_code or lang} is missing. Please download it from the Model menu.')
        elif backend == 'whisper':
            config = load_config()
            model_name = config.get('whisper_model', 'base')
            show_notification('Instant Typer', f'Whisper model "{model_name}" is missing. Please download it from the Model menu.')
        else:
            show_notification('Instant Typer', f'Model for {backend} is missing. Please download it from the Model menu.')
        # Try to open the Model menu automatically (simulate click)
        # This is not natively supported by pystray, so show a Tkinter dialog as fallback
        try:
            root = self.indicator.root
            root.after(100, lambda: tk.messagebox.showinfo('Model Required', 'Please open the tray icon, go to the Model menu, and download the required model.'))
        except Exception:
            pass

    def is_model_available(self):
        backend = self.selected_backend
        if backend == 'vosk':
            config = load_config()
            custom_model = config.get('custom_vosk_model')
            if custom_model:
                model_dir = os.path.join(USER_MODELS_DIR, 'vosk', custom_model)
                return os.path.isdir(model_dir)
            lang = config.get('lang', 'EN')
            model_dir = self.LANG_MODELS.get(lang)
            if not model_dir:
                return False
            path = os.path.join(USER_MODELS_DIR, 'vosk', model_dir)
            return os.path.isdir(path)
        elif backend == 'whisper':
            config = load_config()
            model = config.get('whisper_model', 'base')
            models_dir = os.path.join(USER_MODELS_DIR, 'whisper')
            files = os.listdir(models_dir) if os.path.isdir(models_dir) else []
            return os.path.isdir(models_dir) and (os.path.isdir(os.path.join(models_dir, model)) or any(f.startswith(model) for f in files))
        # Add similar checks for other backends if needed
        return True

    def on_select_lang(self, lang_code):
        self.set_language(lang_code)
        self.refresh_menu()
        # Check if model is available after switching language
        if self.selected_backend == 'vosk' and not self.is_model_available():
            self.notify_and_prompt_model_download('vosk', lang_code)

    def on_select_backend(self, backend_name):
        self.set_backend(backend_name)
        # Ensure default model/language for new backend if missing
        config = load_config()
        if backend_name == 'vosk':
            if 'lang' not in config or config['lang'] not in self.LANG_MODELS:
                config['lang'] = 'EN'
                save_config(config)
                self.set_language('EN')
        elif backend_name == 'whisper':
            if 'whisper_model' not in config:
                config['whisper_model'] = 'base'
                save_config(config)
        self.refresh_menu()
        self.update_icon_title()
        # Check if model is available after switching backend
        if not self.is_model_available():
            self.notify_and_prompt_model_download(backend_name)

    def on_toggle(self, icon, item):
        if not self.is_model_available():
            self.notify_and_prompt_model_download(self.selected_backend)
            return
        self.toggle_listening()
        icon.icon = create_icon(self.is_listening)
        self.update_icon_title()
        icon.update_menu()
        if self.is_listening:
            self.indicator.root.after(0, self.indicator.show)
        else:
            self.indicator.root.after(0, self.indicator.hide)

class TutorialManager:
    def __init__(self, root, tray_icon):
        self.root = root
        self.tray_icon = tray_icon
        self.steps = [
            self.show_tray_icon_step,
            self.show_toggle_step,
            self.show_language_step,
            self.show_microphone_step,
            self.show_done_step
        ]
        self.current_step = 0
        self.toplevel = None
        # Mark tutorial as complete as soon as it starts
        flag_path = os.path.expanduser('~/.instyper/.first_run_complete')
        if not os.path.isfile(flag_path):
            with open(flag_path, 'w') as f:
                f.write('done')

    def start(self):
        self.show_step(0)

    def show_step(self, idx):
        self.current_step = idx
        if self.toplevel:
            self.toplevel.destroy()
        if idx < len(self.steps):
            self.steps[idx]()

    def next_step(self):
        self.show_step(self.current_step + 1)

    def show_popup(self, title, message, x=200, y=200):
        self.toplevel = tk.Toplevel(self.root)
        self.toplevel.title(title)
        self.toplevel.geometry(f"350x120+{x}+{y}")
        self.toplevel.attributes('-topmost', True)
        self.toplevel.grab_set()
        label = tk.Label(self.toplevel, text=message, wraplength=320, justify='left', font=('Arial', 12))
        label.pack(pady=10, padx=10)
        btn = tk.Button(self.toplevel, text="Next", command=self.next_step)
        btn.pack(pady=8)

    def show_tray_icon_step(self):
        self.show_popup(
            "Welcome to Instyper!",
            "This is your system tray icon. Right-click it to access the main features of Instyper."
        )

    def show_toggle_step(self):
        self.show_popup(
            "Toggle Voice Typing",
            "Click 'Toggle Voice Typing' in the tray menu to start or stop voice typing."
        )

    def show_language_step(self):
        self.show_popup(
            "Language Selection",
            "You can change the recognition language from the 'Language' submenu in the tray icon."
        )

    def show_microphone_step(self):
        self.show_popup(
            "Microphone Selection",
            "Choose your preferred microphone from the 'Microphone' submenu in the tray icon."
        )

    def show_done_step(self):
        self.show_popup(
            "You're Ready!",
            "That's it! You're ready to use Instyper. You can revisit this tutorial by deleting the '.first_run_complete' file in your ~/.instyper folder.")

def main():
    log("Starting Instant Typer...")
    indicator = ListeningIndicator()
    voice_typer = VoiceTyper(indicator=indicator)
    atexit.register(voice_typer.cleanup)

    # Always ensure default models are present before starting main UI
    # Vosk default
    vosk_default_model = MODEL_DEFAULTS.get('vosk', 'en')
    vosk_model_dir = os.path.join(USER_MODELS_DIR, 'vosk', voice_typer.LANG_MODELS.get(vosk_default_model.upper(), 'vosk-model-small-en-us-0.15'))
    if not os.path.isdir(vosk_model_dir):
        try:
            download_vosk_english_small()
        except Exception as e:
            log(f"Error downloading Vosk English model: {e}", 'error')
    # Whisper default
    whisper_default_model = MODEL_DEFAULTS.get('whisper', 'tiny')
    whisper_models_dir = os.path.join(USER_MODELS_DIR, 'whisper')
    whisper_model_present = False
    if os.path.isdir(whisper_models_dir):
        files = os.listdir(whisper_models_dir)
        whisper_model_present = any(f.startswith(whisper_default_model) for f in files)
    if not whisper_model_present:
        try:
            download_whisper_tiny()
        except Exception as e:
            log(f"Error downloading Whisper tiny model: {e}", 'error')

    def get_active_backend_and_model():
        backend = voice_typer.selected_backend
        if backend == 'vosk':
            config = load_config()
            lang = config.get('lang', 'EN')
            model = voice_typer.LANG_MODELS.get(lang, '?')
        elif backend == 'whisper':
            config = load_config()
            model = config.get('whisper_model', 'base')
        else:
            model = '(not implemented)'
        return backend, model

    def update_icon_title(icon):
        backend, model = get_active_backend_and_model()
        icon.title = f"Instant Typer ({backend}: {model})"

    icon = pystray.Icon("instyper")
    icon.icon = create_icon()
    update_icon_title(icon)
    threads = {}

    def on_select_mic(idx):
        voice_typer.set_mic_index(idx - 1)
        icon.update_menu()
        update_icon_title(icon)
    def mic_checked(idx):
        if idx == 0:
            return voice_typer.selected_mic_index is None
        return voice_typer.selected_mic_index == (idx - 1)
    def make_mic_menu_item(idx, name):
        def on_select(icon, item):
            on_select_mic(idx)
        def is_checked(item):
            return mic_checked(idx)
        return pystray.MenuItem(name, on_select, checked=is_checked)
    mic_names = ["Default"] + (voice_typer.mic_names if voice_typer.mic_names else [])
    mic_menu_items = [make_mic_menu_item(idx, name) for idx, name in enumerate(mic_names)]

    def on_select_lang(lang_code):
        voice_typer.set_language(lang_code)
        icon.update_menu()
        update_icon_title(icon)
        # Check if model is available after switching language
        if voice_typer.selected_backend == 'vosk' and not voice_typer.is_model_available():
            voice_typer.notify_and_prompt_model_download('vosk', lang_code)
    def lang_checked(lang_code):
        return voice_typer.selected_lang == lang_code
    def make_lang_menu_item(lang_code):
        def on_select(icon, item):
            on_select_lang(lang_code)
        def is_checked(item):
            return lang_checked(lang_code)
        # Use UI name from JSON
        label = voice_typer.LANG_UI_NAMES.get(lang_code, lang_code)
        return pystray.MenuItem(label, on_select, checked=is_checked)
    lang_menu_items = [make_lang_menu_item(lang) for lang in voice_typer.LANG_MODELS.keys()]

    # --- Backend menu (flat) ---
    def on_select_backend(backend_name):
        voice_typer.set_backend(backend_name)
        # Ensure default model/language for new backend if missing
        config = load_config()
        if backend_name == 'vosk':
            if 'lang' not in config or config['lang'] not in voice_typer.LANG_MODELS:
                config['lang'] = 'EN'
                save_config(config)
                voice_typer.set_language('EN')
        elif backend_name == 'whisper':
            if 'whisper_model' not in config:
                config['whisper_model'] = 'base'
                save_config(config)
        refresh_menu()
        update_icon_title(icon)
        # Check if model is available after switching backend
        if not voice_typer.is_model_available():
            voice_typer.notify_and_prompt_model_download(backend_name)
    def backend_checked(backend_name):
        return voice_typer.selected_backend == backend_name
    def make_backend_menu_item(backend_name):
        def on_select(icon, item):
            on_select_backend(backend_name)
        def is_checked(item):
            return backend_checked(backend_name)
        return pystray.MenuItem(backend_name, on_select, checked=is_checked)
    backend_menu_items = [make_backend_menu_item(backend) for backend in voice_typer.BACKENDS]

    # --- Model menu (for current backend only) ---
    def get_vosk_models():
        return get_backend_models('vosk')
    def get_whisper_models():
        return get_backend_models('whisper')
    def get_downloaded_vosk_models(models_dir):
        if not os.path.isdir(models_dir):
            return set()
        return set([m['model'] for m in get_vosk_models() if os.path.isdir(os.path.join(models_dir, m['model']))])
    def get_downloaded_whisper_models(models_dir):
        if not os.path.isdir(models_dir):
            return set()
        files = os.listdir(models_dir)
        return set([m['model'] for m in get_whisper_models() if os.path.isdir(os.path.join(models_dir, m['model'])) or any(f.startswith(m['model']) for f in files)])
    def get_active_model(backend):
        config = load_config()
        if backend == 'vosk':
            lang = config.get('lang', 'EN').upper()
            return voice_typer.LANG_MODELS.get(lang)
        elif backend == 'whisper':
            return config.get('whisper_model', 'base')
        return None
    def set_active_model(backend, model_name):
        config = load_config()
        if backend == 'vosk':
            found = False
            for lang_code, model_dir in voice_typer.LANG_MODELS.items():
                if model_dir == model_name:
                    config['lang'] = lang_code
                    config.pop('custom_vosk_model', None)
                    save_config(config)
                    voice_typer.set_language(lang_code)
                    found = True
                    break
            if not found:
                # Custom/unmapped model
                config['custom_vosk_model'] = model_name
                save_config(config)
                # Force reload
                if voice_typer.is_listening:
                    voice_typer.toggle_listening()
                    voice_typer.toggle_listening()
        elif backend == 'whisper':
            config['whisper_model'] = model_name
            save_config(config)
        if voice_typer.is_listening and backend != 'vosk':
            voice_typer.toggle_listening()
            voice_typer.toggle_listening()
        update_icon_title(icon)
    def download_vosk_model(model, models_dir, on_done):
        url = model.get('url')
        name = model.get('name')
        if not url or not name:
            show_notification('Instant Typer', 'Invalid Vosk model info.')
            return
        dest_zip = os.path.join(models_dir, name + '.zip')
        def do_download():
            try:
                show_notification('Instant Typer', f'Downloading {name}...')
                urllib.request.urlretrieve(url, dest_zip)
                show_notification('Instant Typer', f'Extracting {name}...')
                log(f"Extracting {dest_zip} to {models_dir}")
                with zipfile.ZipFile(dest_zip, 'r') as zip_ref:
                    zip_ref.extractall(models_dir)
                log(f"Extraction complete: {models_dir}")
                os.remove(dest_zip)
                show_notification('Instant Typer', f'Model {name} ready!')
                if on_done:
                    on_done()
            except Exception as e:
                show_notification('Instant Typer', f'Error downloading {name}: {e}')
                log(f"Error downloading/extracting {name}: {e}", 'error')
        threading.Thread(target=do_download, daemon=True).start()
    def download_whisper_model(model_name, models_dir, on_done):
        import whisper
        def do_download():
            try:
                show_notification('Instant Typer', f'Downloading {model_name}...')
                whisper.load_model(model_name, download_root=models_dir)
                show_notification('Instant Typer', f'Model {model_name} ready!')
                if on_done:
                    on_done()
            except Exception as e:
                show_notification('Instant Typer', f'Error downloading {model_name}: {e}')
        threading.Thread(target=do_download, daemon=True).start()
    def make_model_menu_items():
        backend = voice_typer.selected_backend
        models_dir = os.path.join(USER_MODELS_DIR, backend)
        os.makedirs(models_dir, exist_ok=True)
        active_model = get_active_model(backend)
        items = []
        if backend == 'vosk':
            available_models = get_vosk_models()
            downloaded = get_downloaded_vosk_models(models_dir)
            for m in available_models:
                name = m['name']
                model_dir = m['model']
                label = name
                if model_dir in downloaded:
                    label += ' (downloaded)'
                def make_on_select(model_dir=model_dir, m=m):
                    def on_select(icon, item):
                        if model_dir in get_downloaded_vosk_models(models_dir):
                            set_active_model('vosk', model_dir)
                            icon.update_menu()
                        else:
                            def after_download():
                                set_active_model('vosk', model_dir)
                                icon.update_menu()
                            VoskModelDownloader(m, models_dir, after_download).download()
                    return on_select
                def make_is_checked(model_dir=model_dir):
                    def is_checked(item):
                        return active_model == model_dir
                    return is_checked
                items.append(pystray.MenuItem(label, make_on_select(), checked=make_is_checked(), enabled=True))
        elif backend == 'whisper':
            available_models = get_whisper_models()
            downloaded = get_downloaded_whisper_models(models_dir)
            for m in available_models:
                label = m['name']
                model_dir = m['model']
                if model_dir in downloaded:
                    label += ' (downloaded)'
                def make_on_select(model_dir=model_dir, m=m):
                    def on_select(icon, item):
                        if model_dir in get_downloaded_whisper_models(models_dir):
                            set_active_model('whisper', model_dir)
                            icon.update_menu()
                        else:
                            def after_download():
                                set_active_model('whisper', model_dir)
                                icon.update_menu()
                            WhisperModelDownloader(model_dir, models_dir, after_download).download()
                    return on_select
                def make_is_checked(model_dir=model_dir):
                    def is_checked(item):
                        return active_model == model_dir
                    return is_checked
                items.append(pystray.MenuItem(label, make_on_select(), checked=make_is_checked(), enabled=True))
        else:
            items.append(pystray.MenuItem('Not implemented', None, enabled=False))
        return items
    model_menu_items = make_model_menu_items

    def on_exit(icon, item):
        icon.stop()
        indicator.destroy()
        voice_typer.cleanup()
        for t in threads.values():
            if t.is_alive():
                t.join(timeout=2)
        os._exit(0)
    def is_model_available():
        backend = voice_typer.selected_backend
        if backend == 'vosk':
            config = load_config()
            custom_model = config.get('custom_vosk_model')
            if custom_model:
                model_dir = os.path.join(USER_MODELS_DIR, 'vosk', custom_model)
                return os.path.isdir(model_dir)
            lang = config.get('lang', 'EN')
            model_dir = voice_typer.LANG_MODELS.get(lang)
            if not model_dir:
                return False
            path = os.path.join(USER_MODELS_DIR, 'vosk', model_dir)
            return os.path.isdir(path)
        elif backend == 'whisper':
            config = load_config()
            model = config.get('whisper_model', 'base')
            models_dir = os.path.join(USER_MODELS_DIR, 'whisper')
            files = os.listdir(models_dir) if os.path.isdir(models_dir) else []
            return os.path.isdir(models_dir) and (os.path.isdir(os.path.join(models_dir, model)) or any(f.startswith(model) for f in files))
        # Add similar checks for other backends if needed
        return True

    def on_toggle(icon, item):
        if not is_model_available():
            notify_and_prompt_model_download(voice_typer.selected_backend)
            return
        voice_typer.toggle_listening()
        icon.icon = create_icon(voice_typer.is_listening)
        update_icon_title(icon)
        icon.update_menu()
        if voice_typer.is_listening:
            indicator.root.after(0, indicator.show)
        else:
            indicator.root.after(0, indicator.hide)

    def restart_app():
        nonlocal indicator, voice_typer
        if not tkinter.messagebox.askyesno("Confirm", "Are you sure you want to restart the app? This will stop all running tasks and reset the app state."):
            return
        log("Soft restarting app...")
        # Stop voice typing and threads
        voice_typer.cleanup()
        # Destroy indicator window
        try:
            indicator.destroy()
        except Exception:
            pass
        # Re-initialize indicator and voice_typer
        new_indicator = ListeningIndicator()
        new_voice_typer = VoiceTyper(indicator=new_indicator)
        atexit.register(new_voice_typer.cleanup)
        # Replace references
        indicator = new_indicator
        voice_typer = new_voice_typer
        # Rebuild menu and icon
        icon.icon = create_icon()
        update_icon_title(icon)
        icon.menu = build_menu()
        show_notification('Instant Typer', 'App state has been reset.')

    def make_system_menu():
        return pystray.Menu(
            pystray.MenuItem('Purge All Models', lambda icon, item: purge_all_models()),
            pystray.MenuItem('Reset User Settings', lambda icon, item: reset_user_settings()),
            pystray.MenuItem('Restart App', lambda icon, item: restart_app()),
        )

    def build_menu():
        return pystray.Menu(
            pystray.MenuItem(
                'Toggle Voice Typing',
                on_toggle,
                checked=lambda item: voice_typer.is_listening,
                enabled=is_model_available()
            ),
            pystray.MenuItem(
                'Language',
                pystray.Menu(*lang_menu_items)
            ),
            pystray.MenuItem(
                'Microphone',
                pystray.Menu(*mic_menu_items)
            ),
            pystray.MenuItem(
                'Backend',
                pystray.Menu(*backend_menu_items)
            ),
            pystray.MenuItem(
                'Model',
                pystray.Menu(*model_menu_items())
            ),
            pystray.MenuItem(
                'System',
                make_system_menu()
            ),
            pystray.MenuItem(
                'Exit',
                on_exit
            )
        )

    icon.menu = build_menu()

    def refresh_menu():
        icon.menu = build_menu()
        update_icon_title(icon)

    icon_thread = threading.Thread(target=icon.run)
    icon_thread.daemon = True
    icon_thread.start()
    threads['icon'] = icon_thread

    voice_typer_thread = threading.Thread(target=voice_typer.start)
    voice_typer_thread.daemon = True
    voice_typer_thread.start()
    threads['voice_typer'] = voice_typer_thread

    # First-run tutorial logic
    flag_path = os.path.expanduser('~/.instyper/.first_run_complete')
    if not os.path.isfile(flag_path):
        tutorial = TutorialManager(indicator.root, icon)
        indicator.root.after(1000, tutorial.start)

    indicator.root.mainloop()

def vosk_multilang_recognize():
    """
    Multi-language speech recognition using Vosk.
    Lets the user select a language, loads the corresponding model, and prints recognized text from the microphone.
    """
    import os
    import sys
    import json
    import pyaudio
    from vosk import Model, KaldiRecognizer
    import shutil

    USER_MODELS_DIR = os.path.expanduser('~/.instyper/models')
    REPO_MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
    os.makedirs(USER_MODELS_DIR, exist_ok=True)
    if not os.listdir(USER_MODELS_DIR) and os.path.isdir(REPO_MODELS_DIR):
        for item in os.listdir(REPO_MODELS_DIR):
            src = os.path.join(REPO_MODELS_DIR, item)
            dst = os.path.join(USER_MODELS_DIR, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)

    LANG_MODELS = {
        'EN': 'vosk-model-small-en-us-0.15',
        'DE': 'vosk-model-small-de-zamia-0.3',
        'NL': 'vosk-model-small-nl-0.22',
        'FR': 'vosk-model-small-fr-0.22',
        'TR': 'vosk-model-small-tr-0.3',
    }
    MODELS_DIR = USER_MODELS_DIR

    def select_language():
        log("Select a language:")
        for idx, lang in enumerate(LANG_MODELS.keys(), 1):
            log(f"  {idx}. {lang}")
        choice = input("Enter number: ").strip()
        try:
            idx = int(choice) - 1
            lang = list(LANG_MODELS.keys())[idx]
            return lang
        except (ValueError, IndexError):
            log("Invalid selection.")
            sys.exit(1)

    def get_model_path(lang_code):
        model_dir = LANG_MODELS[lang_code]
        path = os.path.join(MODELS_DIR, model_dir)
        if not os.path.isdir(path):
            log(f"Model directory not found: {path}")
            log("Please ensure the model is extracted correctly.")
            sys.exit(1)
        return path

    log("Vosk Multi-language Speech Recognition")
    lang = select_language()
    model_path = get_model_path(lang)
    log(f"Loading model for {lang} from {model_path} ...")
    model = Model(model_path)

    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)
    stream.start_stream()

    rec = KaldiRecognizer(model, 16000)
    log("Speak into your microphone. Press Ctrl+C to stop.")
    try:
        while True:
            data = stream.read(4000, exception_on_overflow=False)
            if rec.AcceptWaveform(data):
                result = rec.Result()
                text = json.loads(result).get('text', '')
                if text:
                    log(f"Recognized: {text}")
    except KeyboardInterrupt:
        log("\nExiting...")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

def download_vosk_english_small():
    import requests, zipfile, os, tempfile
    EN_MODEL_NAME = 'vosk-model-small-en-us-0.15'
    EN_MODEL_URL = 'https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip'
    models_dir = os.path.join(USER_MODELS_DIR, 'vosk')
    model_dir = os.path.join(models_dir, EN_MODEL_NAME)
    if os.path.isdir(model_dir):
        log(f"Vosk English model already present: {model_dir}")
        return
    os.makedirs(models_dir, exist_ok=True)
    log(f"Downloading Vosk English model from {EN_MODEL_URL}")
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmpf:
        r = requests.get(EN_MODEL_URL, stream=True)
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                tmpf.write(chunk)
        tmpf.flush()
        log(f"Extracting {EN_MODEL_NAME} to {models_dir}")
        with zipfile.ZipFile(tmpf.name, 'r') as zip_ref:
            zip_ref.extractall(models_dir)
        try:
            os.remove(tmpf.name)
            log(f"Removed archive: {tmpf.name}")
        except Exception as e:
            log(f"Could not remove archive {tmpf.name}: {e}", 'warning')
    log(f"Vosk English model {EN_MODEL_NAME} extracted.")

def download_whisper_tiny():
    import whisper
    models_dir = os.path.join(USER_MODELS_DIR, 'whisper')
    os.makedirs(models_dir, exist_ok=True)
    # Check if already present
    files = os.listdir(models_dir)
    if any(f.startswith('tiny') for f in files):
        log("Whisper 'tiny' model already present.")
        return
    log("Downloading Whisper 'tiny' model...")
    whisper.load_model('tiny', download_root=models_dir)
    log("Whisper 'tiny' model downloaded.")

def purge_all_models():
    if not tkinter.messagebox.askyesno("Confirm", "Are you sure you want to delete ALL downloaded models except the currently selected one? This cannot be undone."):
        return
    import glob
    config = load_config()
    kept = []
    deleted = []
    # Vosk
    vosk_dir = os.path.join(USER_MODELS_DIR, 'vosk')
    custom_vosk_model = config.get('custom_vosk_model')
    lang = config.get('lang', 'EN')
    selected_vosk_model = custom_vosk_model or (voice_typer.LANG_MODELS.get(lang) if hasattr(voice_typer, 'LANG_MODELS') else None)
    if os.path.isdir(vosk_dir):
        for item in glob.glob(os.path.join(vosk_dir, '*')):
            if os.path.basename(item) == selected_vosk_model:
                kept.append(item)
                continue
            try:
                if os.path.isdir(item):
                    shutil.rmtree(item)
                else:
                    os.remove(item)
                deleted.append(item)
                log(f"Deleted: {item}")
            except Exception as e:
                log(f"Error deleting {item}: {e}", 'error')
    # Whisper
    whisper_dir = os.path.join(USER_MODELS_DIR, 'whisper')
    selected_whisper_model = config.get('whisper_model', 'base')
    if os.path.isdir(whisper_dir):
        for item in glob.glob(os.path.join(whisper_dir, '*')):
            if os.path.basename(item).startswith(selected_whisper_model):
                kept.append(item)
                continue
            try:
                if os.path.isdir(item):
                    shutil.rmtree(item)
                else:
                    os.remove(item)
                deleted.append(item)
                log(f"Deleted: {item}")
            except Exception as e:
                log(f"Error deleting {item}: {e}", 'error')
    # TODO: Add similar logic for other backends if needed
    msg = 'All models purged except:\n' + '\n'.join(os.path.basename(k) for k in kept) if kept else 'All models purged.'
    show_notification('Instant Typer', msg)
    # Optionally, refresh menu

def reset_user_settings():
    if not tkinter.messagebox.askyesno("Confirm", "Are you sure you want to reset all user settings? This cannot be undone."):
        return
    try:
        if os.path.isfile(CONFIG_PATH):
            os.remove(CONFIG_PATH)
            log(f"Deleted config: {CONFIG_PATH}")
        show_notification('Instant Typer', 'User settings reset.')
    except Exception as e:
        log(f"Error resetting user settings: {e}", 'error')

class BaseModelDownloader(abc.ABC):
    def __init__(self, model_info, models_dir, on_done=None):
        self.model_info = model_info
        self.models_dir = models_dir
        self.on_done = on_done

    @abc.abstractmethod
    def is_present(self):
        pass

    @abc.abstractmethod
    def download(self):
        pass

    @abc.abstractmethod
    def extract(self, archive_path):
        pass

class VoskModelDownloader(BaseModelDownloader):
    def is_present(self):
        name = self.model_info.get('name')
        return os.path.isdir(os.path.join(self.models_dir, name))

    def download(self):
        import urllib.request
        import threading
        import zipfile
        url = self.model_info.get('url')
        name = self.model_info.get('name')
        dest_zip = os.path.join(self.models_dir, name + '.zip')
        def do_download():
            try:
                show_notification('Instant Typer', f'Downloading {name}...')
                urllib.request.urlretrieve(url, dest_zip)
                show_notification('Instant Typer', f'Extracting {name}...')
                self.extract(dest_zip)
                os.remove(dest_zip)
                show_notification('Instant Typer', f'Model {name} ready!')
                if self.on_done:
                    self.on_done()
            except Exception as e:
                show_notification('Instant Typer', f'Error downloading {name}: {e}')
                log(f"Error downloading/extracting {name}: {e}", 'error')
        threading.Thread(target=do_download, daemon=True).start()

    def extract(self, archive_path):
        import zipfile
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(self.models_dir)

class WhisperModelDownloader(BaseModelDownloader):
    def is_present(self):
        model_name = self.model_info
        files = os.listdir(self.models_dir) if os.path.isdir(self.models_dir) else []
        return os.path.isdir(os.path.join(self.models_dir, model_name)) or any(f.startswith(model_name) for f in files)

    def download(self):
        import whisper
        import threading
        model_name = self.model_info
        def do_download():
            try:
                show_notification('Instant Typer', f'Downloading {model_name}...')
                whisper.load_model(model_name, download_root=self.models_dir)
                show_notification('Instant Typer', f'Model {model_name} ready!')
                if self.on_done:
                    self.on_done()
            except Exception as e:
                show_notification('Instant Typer', f'Error downloading {model_name}: {e}')
        threading.Thread(target=do_download, daemon=True).start()

    def extract(self, archive_path):
        pass  # Not needed for Whisper

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Instant Typer")
    parser.add_argument('--download-models', action='store_true', help='Download and extract all small Vosk models')
    args = parser.parse_args()
    if args.download_models:
        download_and_extract_small_vosk_models()
    else:
        main()
