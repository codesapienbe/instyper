#!/usr/bin/env python3

"""
Instant Typer - Voice-to-Text Application

A cross-platform voice typing application that supports multiple speech recognition backends
including Vosk, Whisper, SpeechBrain, Coqui STT, and PaddlePaddle. Features system tray
integration, multiple language support, and real-time speech transcription.

Author: Instant Typer Team (managed by @codesapienbe)
License: MIT
"""

# =============================================================================
# IMPORTS AND DEPENDENCIES
# =============================================================================

import os
import sys
import time
import threading
import platform
import atexit
import json
import tempfile
import shutil
import pathlib
import urllib.request
import zipfile
import wave
import math
import string
import logging
import abc
from typing import Optional, Dict, List, Callable, Any, Tuple
import sqlite3
import hashlib
import socket
try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
except ImportError:
    Fernet = None  # Will error if used
    PBKDF2HMAC = None
    hashes = None
    default_backend = None
import base64
import secrets

# Third-party imports - Core functionality
import pyautogui
import pyaudio
import pyperclip
import pyttsx3
import numpy as np
from plyer import notification
from vosk import Model, KaldiRecognizer

# Third-party imports - UI components
import pystray
from PIL import Image, ImageDraw
import tkinter as tk
from tkinter import ttk, messagebox

# Third-party imports - Additional backends
import pynput
from bs4 import BeautifulSoup
import requests

# Celery integration
from celery import Celery

# =============================================================================
# CONSTANTS AND CONFIGURATION
# =============================================================================

class AppConstants:
    """Application-wide constants and configuration values."""
    
    # Application metadata
    APP_NAME = 'Instant Typer'
    APP_ID = 'instyper'
    
    # File paths
    USER_HOME_DIR = os.path.expanduser('~/.instyper')
    USER_MODELS_DIR = os.path.expanduser('~/.instyper/models')
    CONFIG_PATH = os.path.expanduser('~/.instyper/config.json')
    LOG_PATH = os.path.expanduser('~/.instyper/instyper.log')
    USER_MODELS_JSON = os.path.expanduser('~/.instyper/models.json')
    USER_README = os.path.expanduser('~/.instyper/README.md')
    FIRST_RUN_FLAG = os.path.expanduser('~/.instyper/.first_run_complete')
    SPEECH_LOG_PATH = os.path.expanduser('~/.instyper/speech.log.enc')
    SPEECH_LOG_SALT_PATH = os.path.expanduser('~/.instyper/speech.log.salt')
    
    # Repository paths (for initial setup)
    REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
    REPO_MODELS_DIR = os.path.join(REPO_ROOT, 'models')
    REPO_MODELS_JSON = '@models.json'
    REPO_README = os.path.join(REPO_ROOT, 'README.md')
    
    # Audio settings
    AUDIO_RATE = 16000
    AUDIO_CHUNK = 4000
    AUDIO_FORMAT = pyaudio.paInt16
    AUDIO_CHANNELS = 1
    FRAMES_PER_BUFFER = 8000
    
    # Speech recognition settings
    MIN_AUDIO_SECONDS = 2
    MAX_AUDIO_SECONDS = 8
    MIN_AUDIO_BYTES = AUDIO_RATE * 2 * MIN_AUDIO_SECONDS
    MAX_AUDIO_BYTES = AUDIO_RATE * 2 * MAX_AUDIO_SECONDS
    
    # Global hotkey
    GLOBAL_HOTKEY = '<ctrl>+<alt>+<space>'
    
    # UI settings
    ICON_SIZE = (64, 64)
    NOTIFICATION_TIMEOUT = 2
    INDICATOR_POSITION_OFFSET = (20, 20)
    INDICATOR_UPDATE_INTERVAL = 50  # milliseconds
    
    # Whisper output filtering
    IGNORE_WHISPER_OUTPUTS = {
        "thank you.", "i'm sorry, i cannot help with that.", "i'm sorry.",
        "sorry.", "hello.", "hi.", "yes.", "no.", "okay.", "ok.",
    }

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

def setup_logging() -> None:
    """Initialize logging configuration for the application."""
    os.makedirs(os.path.dirname(AppConstants.LOG_PATH), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(AppConstants.LOG_PATH, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def log(msg: str, level: str = 'info') -> None:
    """Log a message with the specified level."""
    getattr(logging, level)(msg)

# Initialize logging
setup_logging()

# =============================================================================
# INITIALIZATION AND SETUP
# =============================================================================

def initialize_user_directory() -> None:
    """Initialize the user's .instyper directory with necessary files and models."""
    # Create user directories
    os.makedirs(AppConstants.USER_MODELS_DIR, exist_ok=True)
    
    # Copy README if not present
    if os.path.isfile(AppConstants.REPO_README) and not os.path.isfile(AppConstants.USER_README):
        shutil.copy2(AppConstants.REPO_README, AppConstants.USER_README)
    
    # Copy models if user models directory is empty
    if not os.listdir(AppConstants.USER_MODELS_DIR) and os.path.isdir(AppConstants.REPO_MODELS_DIR):
        for item in os.listdir(AppConstants.REPO_MODELS_DIR):
            src = os.path.join(AppConstants.REPO_MODELS_DIR, item)
            dst = os.path.join(AppConstants.USER_MODELS_DIR, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
    
    # Copy models.json if not present
    if not os.path.isfile(AppConstants.USER_MODELS_JSON):
        models_json_src = os.path.join(os.path.dirname(__file__), 'models.json')
        if os.path.isfile(models_json_src):
            shutil.copy2(models_json_src, AppConstants.USER_MODELS_JSON)

# Initialize user directory on import
initialize_user_directory()

# =============================================================================
# CONFIGURATION MANAGEMENT
# =============================================================================

class ConfigManager:
    """Manages application configuration persistence using SQLite."""
    DB_PATH = os.path.expanduser('~/.instyper/config.db')
    TABLE_NAME = 'config'
    
    DEFAULT_CONFIG = {
        'mic_index': None,  # Default microphone
        'backend': 'vosk',  # Default backend
        'model': None,      # Will be set to default model for backend
        'lang': 'en',       # Default language
        'pincode': None  # SHA-256 hash of pincode
    }

    @staticmethod
    def _get_conn():
        os.makedirs(os.path.dirname(ConfigManager.DB_PATH), exist_ok=True)
        conn = sqlite3.connect(ConfigManager.DB_PATH)
        conn.execute(f"CREATE TABLE IF NOT EXISTS {ConfigManager.TABLE_NAME} (key TEXT PRIMARY KEY, value TEXT)")
        return conn

    @staticmethod
    def load() -> Dict[str, Any]:
        """Load configuration from SQLite database."""
        conn = ConfigManager._get_conn()
        cur = conn.cursor()
        cur.execute(f"SELECT key, value FROM {ConfigManager.TABLE_NAME}")
        rows = cur.fetchall()
        config = ConfigManager.DEFAULT_CONFIG.copy()  # Start with defaults
        for k, v in rows:
            try:
                config[k] = json.loads(v)
            except Exception:
                config[k] = v
        conn.close()
        return config

    @staticmethod
    def save(data: Dict[str, Any]) -> None:
        """Save configuration to SQLite database."""
        conn = ConfigManager._get_conn()
        cur = conn.cursor()
        
        # Ensure we're only updating valid config keys
        valid_data = {k: v for k, v in data.items() if k in ConfigManager.DEFAULT_CONFIG}
        
        for k, v in valid_data.items():
            cur.execute(f"REPLACE INTO {ConfigManager.TABLE_NAME} (key, value) VALUES (?, ?)", 
                       (k, json.dumps(v)))
        
        conn.commit()
        conn.close()
        log(f"Config saved (sqlite): {list(valid_data.keys())}")

    @staticmethod
    def reset() -> None:
        """Reset configuration to defaults."""
        ConfigManager.save(ConfigManager.DEFAULT_CONFIG)
        log("Config reset to defaults")

    @staticmethod
    def set_speech_log_pincode(pincode: str) -> None:
        hash_ = hashlib.sha256(pincode.encode('utf-8')).hexdigest()
        config = ConfigManager.load()
        config['pincode'] = hash_
        ConfigManager.save(config)

    @staticmethod
    def verify_speech_log_pincode(pincode: str) -> bool:
        config = ConfigManager.load()
        hash_ = hashlib.sha256(pincode.encode('utf-8')).hexdigest()
        return config.get('pincode') == hash_

    @staticmethod
    def is_speech_log_pincode_set() -> bool:
        config = ConfigManager.load()
        return bool(config.get('pincode'))

class ModelsConfig:
    """Manages models configuration from models.json."""
    
    def __init__(self):
        self._load_models_config()
    
    def _load_models_config(self) -> None:
        """Load models configuration from models.json."""
        try:
            with open(AppConstants.USER_MODELS_JSON, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.all_models = config['models']
                self.defaults = config.get('defaults', {})
        except Exception as e:
            log(f"Error loading models config: {e}", 'error')
            self.all_models = []
            self.defaults = {}
    
    def get_backend_models(self, backend: str) -> List[Dict[str, Any]]:
        """Get all models for a specific backend."""
        return [m for m in self.all_models if m['backend'] == backend]
    
    def get_model_by_id(self, backend: str, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model by backend and ID."""
        for m in self.all_models:
            if m['backend'] == backend and m['id'] == model_id:
                return m
        return None
    
    def get_model_by_name(self, backend: str, model_name: str) -> Optional[Dict[str, Any]]:
        """Get model by backend and model name."""
        for m in self.all_models:
            if m['backend'] == backend and m['model'] == model_name:
                return m
        return None
    
    def get_default_backend(self) -> Optional[str]:
        """Get the default backend, preferring Vosk if available."""
        backends = [m['backend'] for m in self.all_models]
        if 'vosk' in backends:
            return 'vosk'
        return backends[0] if backends else None
    
    def get_default_model_for_backend(self, backend: str) -> Optional[str]:
        """Get the default model for a specific backend."""
        for m in self.all_models:
            if m['backend'] == backend and m.get('is_default'):
                return m['model']
        # Fallback: first model for backend
        for m in self.all_models:
            if m['backend'] == backend:
                return m['model']
        return None

# Global models configuration instance
models_config = ModelsConfig()

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def human_size(nbytes: Optional[int]) -> str:
    """Convert bytes to human-readable format."""
    if nbytes is None:
        return ''
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    while nbytes >= 1024 and i < len(suffixes) - 1:
        nbytes /= 1024.0
        i += 1
    return f"{nbytes:.1f} {suffixes[i]}"

def show_notification(title: str, message: str) -> None:
    """Show a cross-platform notification."""
    log(f"Notification: {title} - {message}")
    notification.notify(
        title=title,
        message=message,
        app_name=AppConstants.APP_NAME,
        timeout=AppConstants.NOTIFICATION_TIMEOUT,
        app_icon=None
    )

def create_icon(is_active: bool = False) -> Image.Image:
    """Create a system tray icon image."""
    image = Image.new('RGBA', AppConstants.ICON_SIZE, (0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    
    # Platform-specific styling
    system = platform.system()
    if system == 'Darwin':  # macOS
        color = '#FF3B30' if is_active else '#4CAF50'
        outline = None
    else:  # Windows/Linux
        color = '#FF0000' if is_active else '#4CAF50'
        outline = '#2E7D32'
    
    # Draw microphone icon
    dc.ellipse((12, 12, 52, 52), fill=color, outline=outline)
    dc.rectangle((28, 28, 36, 52), fill=color, outline=outline)
    
    return image

def is_useless_whisper_output(text: str) -> bool:
    """Check if Whisper output should be filtered out as noise."""
    text_low = text.lower().strip()
    if not text_low or all(c in string.punctuation for c in text_low):
        return True
    if len(text_low) < 3:
        return True
    return text_low in AppConstants.IGNORE_WHISPER_OUTPUTS

# =============================================================================
# AUDIO DEVICE MANAGEMENT
# =============================================================================

class AudioDeviceManager:
    """Manages audio input devices and microphone selection."""
    
    def __init__(self):
        self.mic_names = []
        self.selected_mic_index = None
        self._discover_microphones()
    
    def _discover_microphones(self) -> None:
        """Discover available microphone devices."""
        p = pyaudio.PyAudio()
        try:
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info.get('maxInputChannels', 0) > 0:
                    self.mic_names.append(info['name'])
            
            self.selected_mic_index = 0 if self.mic_names else None
            
            if not self.mic_names:
                log("No microphones detected", 'warning')
            else:
                log(f"Found {len(self.mic_names)} microphone(s)")
        finally:
            p.terminate()
    
    def get_mic_names(self) -> List[str]:
        """Get list of available microphone names."""
        return self.mic_names
    
    def set_mic_index(self, index: Optional[int]) -> None:
        """Set the selected microphone index."""
        self.selected_mic_index = index

# =============================================================================
# MODEL DOWNLOAD AND MANAGEMENT
# =============================================================================

class ModelDownloader(abc.ABC):
    """Abstract base class for all model downloaders."""
    def __init__(self, model_info: Any, models_dir: str, on_done: Optional[Callable] = None):
        self.model_info = model_info
        self.models_dir = models_dir
        self.on_done = on_done
    @abc.abstractmethod
    def is_present(self) -> bool:
        pass
    @abc.abstractmethod
    def download(self) -> None:
        pass
    def _notify_progress(self, message: str) -> None:
        show_notification(AppConstants.APP_NAME, message)

class VoskModelDownloader(ModelDownloader):
    """Downloads and manages Vosk models."""
    def is_present(self) -> bool:
        model_name = self.model_info.get('model')
        return os.path.isdir(os.path.join(self.models_dir, model_name))
    def download(self) -> None:
        def download_thread():
            try:
                url = self.model_info.get('url')
                name = self.model_info.get('name')
                model_dir = self.model_info.get('model')
                if not url or not name:
                    self._notify_progress('Invalid model info.')
                    return
                dest_zip = os.path.join(self.models_dir, f"{model_dir}.zip")
                self._notify_progress(f'Downloading {name}...')
                urllib.request.urlretrieve(url, dest_zip)
                self._notify_progress(f'Extracting {name}...')
                with zipfile.ZipFile(dest_zip, 'r') as zip_ref:
                    zip_ref.extractall(self.models_dir)
                os.remove(dest_zip)
                self._notify_progress(f'Model {name} ready!')
                if self.on_done:
                    self.on_done()
            except Exception as e:
                self._notify_progress(f'Error downloading {name}: {e}')
                log(f"Error downloading Vosk model: {e}", 'error')
        threading.Thread(target=download_thread, daemon=True).start()

class WhisperModelDownloader(ModelDownloader):
    """Downloads and manages Whisper models."""
    def is_present(self) -> bool:
        model_name = self.model_info
        if not os.path.isdir(self.models_dir):
            return False
        files = os.listdir(self.models_dir)
        return any(f.startswith(model_name) for f in files)
    def download(self) -> None:
        def download_thread():
            try:
                import whisper
                model_name = self.model_info
                self._notify_progress(f'Downloading {model_name}...')
                whisper.load_model(model_name, download_root=self.models_dir)
                self._notify_progress(f'Model {model_name} ready!')
                if self.on_done:
                    self.on_done()
            except Exception as e:
                self._notify_progress(f'Error downloading {model_name}: {e}')
                log(f"Error downloading Whisper model: {e}", 'error')
        threading.Thread(target=download_thread, daemon=True).start()

class SpeechBrainModelDownloader(ModelDownloader):
    def is_present(self) -> bool:
        # Implement logic to check if SpeechBrain model is present
        pass

    def download(self) -> None:
        # Implement logic to download SpeechBrain model
        pass

class CoquiSTTModelDownloader(ModelDownloader):
    def is_present(self) -> bool:
        # Implement logic to check if Coqui STT model is present
        pass

    def download(self) -> None:
        # Implement logic to download Coqui STT model
        pass

MODEL_DOWNLOADER_CLASSES = {
    'vosk': VoskModelDownloader,
    'whisper': WhisperModelDownloader,
    'speechbrain': SpeechBrainModelDownloader,
    'coqui-stt': CoquiSTTModelDownloader,
    # ...
}

# =============================================================================
# USER INTERFACE COMPONENTS
# =============================================================================

class ListeningIndicator:
    """Visual indicator showing when the app is listening for speech."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.configure(bg='#1DE9B6')
        
        self.label = tk.Label(
            self.root, 
            text='...', 
            font=('Arial', 9, 'bold'), 
            fg='#00BFAE', 
            bg='#1DE9B6'
        )
        self.label.pack(ipadx=4, ipady=1)
        self.root.withdraw()
        self._update_position()
    
    def _update_position(self) -> None:
        """Update indicator position to follow mouse cursor."""
        if self.root.winfo_viewable():
            x, y = pyautogui.position()
            offset_x, offset_y = AppConstants.INDICATOR_POSITION_OFFSET
            self.root.geometry(f'+{x + offset_x}+{y + offset_y}')
        self.root.after(AppConstants.INDICATOR_UPDATE_INTERVAL, self._update_position)
    
    def show(self) -> None:
        """Show the listening indicator."""
        self.root.deiconify()
    
    def hide(self) -> None:
        """Hide the listening indicator."""
        self.root.withdraw()
    
    def destroy(self) -> None:
        """Destroy the indicator window."""
        self.root.destroy()

class ModelManagerDialog:
    """Dialog for managing and downloading models."""
    
    def __init__(self, parent: tk.Widget, backend: str, models_dir: str, on_download: Optional[Callable] = None, parent_app=None):
        self.top = tk.Toplevel(parent)
        self.top.title(f"Model Manager - {backend}")
        self.top.geometry("420x340")
        self.backend = backend
        self.models_dir = models_dir
        self.on_download = on_download
        self.downloading = False
        self.selected_model = None
        self.parent = parent_app
        self._setup_ui()
        self._refresh_models()
    
    def _setup_ui(self) -> None:
        """Setup the dialog UI components."""
        # Title
        tk.Label(
            self.top, 
            text=f"Available models for {self.backend}", 
            font=("Arial", 12, "bold")
        ).pack(pady=8)
        
        # Model list
        self.listbox = tk.Listbox(self.top, width=60, height=10)
        self.listbox.pack(padx=10, pady=5, fill=tk.BOTH, expand=False)
        self.listbox.bind('<<ListboxSelect>>', self._on_select)
        
        # Progress label
        self.progress_var = tk.StringVar(value='')
        self.progress_label = tk.Label(
            self.top, 
            textvariable=self.progress_var, 
            font=("Arial", 10), 
            fg="#00796B"
        )
        self.progress_label.pack(pady=2)
        
        # Buttons
        self.download_btn = tk.Button(
            self.top, 
            text="Download selected model", 
            command=self._download_or_select_model, 
            state=tk.DISABLED
        )
        self.download_btn.pack(pady=8)
        
        tk.Button(self.top, text="Close", command=self.top.destroy).pack(pady=2)
    
    def _refresh_models(self) -> None:
        """Refresh the list of available models."""
        self.listbox.delete(0, tk.END)
        self.available_models = []
        # Get the currently active model for this backend
        config = ConfigManager.load()
        active_model = None
        if self.backend == 'vosk':
            active_model = config.get('model')
        elif self.backend == 'whisper':
            active_model = config.get('model')
        backend_models = models_config.get_backend_models(self.backend)
        for model in backend_models:
            model_name = model.get('name', model.get('model', 'Unknown'))
            size_str = human_size(model.get('size'))
            notes = model.get('notes', '')
            display = f"{model_name}"
            if size_str:
                display += f" | {size_str}"
            if notes:
                display += f" | {notes}"
            # Unified model downloader usage
            downloader = None
            downloader_cls = MODEL_DOWNLOADER_CLASSES.get(self.backend)
            if downloader_cls:
                if self.backend == 'whisper':
                    downloader = downloader_cls(model['model'], self.models_dir)
                else:
                    downloader = downloader_cls(model, self.models_dir)
            is_downloaded = downloader.is_present() if downloader else False
            if is_downloaded:
                display += " (downloaded)"
            # Indicate if this is the active model
            if model['model'] == active_model:
                display += " (active)"
            self.listbox.insert(tk.END, display)
            self.available_models.append(model)
    
    def _on_select(self, event) -> None:
        """Handle model selection."""
        idx = self.listbox.curselection()
        if idx:
            self.selected_model = self.available_models[idx[0]]
            downloader = None
            downloader_cls = MODEL_DOWNLOADER_CLASSES.get(self.backend)
            if downloader_cls:
                if self.backend == 'whisper':
                    downloader = downloader_cls(self.selected_model['model'], self.models_dir)
                else:
                    downloader = downloader_cls(self.selected_model, self.models_dir)
            is_downloaded = downloader.is_present() if downloader else False
            if is_downloaded:
                self.download_btn.config(state=tk.NORMAL, text="Select model")
                self.progress_var.set('Model already downloaded. You can select it.')
            else:
                self.download_btn.config(state=tk.NORMAL, text="Download selected model")
                self.progress_var.set('')
    
    def _download_or_select_model(self) -> None:
        """Download or select the chosen model."""
        if self.downloading or not self.selected_model:
            return
        
        model_dir = os.path.join(self.models_dir, self.selected_model['model'])
        if os.path.isdir(model_dir):
            # Model already exists, just select it
            self._set_active_model(self.selected_model['model'])
            self.progress_var.set(f"Model '{self.selected_model['name']}' selected as active.")
        else:
            # Download the model
            self._download_model()
    
    def _download_model(self) -> None:
        """Download the selected model."""
        self.downloading = True
        self.download_btn.config(state=tk.DISABLED)
        
        downloader = None
        downloader_cls = MODEL_DOWNLOADER_CLASSES.get(self.backend)
        if downloader_cls:
            if self.backend == 'whisper':
                downloader = downloader_cls(self.selected_model['model'], self.models_dir)
            else:
                downloader = downloader_cls(self.selected_model, self.models_dir)
        else:
            self.progress_var.set('Download not implemented for this backend.')
            self.downloading = False
            self.download_btn.config(state=tk.NORMAL)
            return
        
        downloader.download()
    
    def _on_download_complete(self) -> None:
        """Handle download completion."""
        self.downloading = False
        self.download_btn.config(state=tk.NORMAL)
        self._refresh_models()
        if self.on_download:
            self.on_download(self.backend, self.models_dir)
    
    def _set_active_model(self, model_name: str) -> None:
        """Set the model as active in configuration and reload backend."""
        if hasattr(self.parent, 'set_model'):
            self.parent.set_model(model_name)
            show_notification(AppConstants.APP_NAME, f"Model '{model_name}' is now set as active.")
            self.top.destroy()

class TutorialManager:
    """Manages the first-run tutorial for new users."""
    
    def __init__(self, root: tk.Tk, tray_icon):
        self.root = root
        self.tray_icon = tray_icon
        self.current_step = 0
        self.toplevel = None
        
        self.steps = [
            self._show_tray_icon_step,
            self._show_toggle_step,
            self._show_microphone_step,
            self._show_done_step
        ]
        
        # Mark tutorial as seen
        with open(AppConstants.FIRST_RUN_FLAG, 'w') as f:
            f.write('done')
    
    def start(self) -> None:
        """Start the tutorial."""
        self._show_step(0)
    
    def _show_step(self, idx: int) -> None:
        """Show a specific tutorial step."""
        self.current_step = idx
        if self.toplevel:
            self.toplevel.destroy()
        if idx < len(self.steps):
            self.steps[idx]()
    
    def _next_step(self) -> None:
        """Move to the next tutorial step."""
        self._show_step(self.current_step + 1)
    
    def _show_popup(self, title: str, message: str, x: int = 200, y: int = 200) -> None:
        """Show a tutorial popup window."""
        self.toplevel = tk.Toplevel(self.root)
        self.toplevel.title(title)
        self.toplevel.geometry(f"350x120+{x}+{y}")
        self.toplevel.attributes('-topmost', True)
        self.toplevel.grab_set()
        
        label = tk.Label(
            self.toplevel, 
            text=message, 
            wraplength=320, 
            justify='left', 
            font=('Arial', 12)
        )
        label.pack(pady=10, padx=10)
        
        btn = tk.Button(self.toplevel, text="Next", command=self._next_step)
        btn.pack(pady=8)
    
    def _show_tray_icon_step(self) -> None:
        """Show tray icon tutorial step."""
        self._show_popup(
            "Tray Icon",
            "You can control Instant Typer from the tray icon."
        )
    
    def _show_toggle_step(self) -> None:
        """Show toggle tutorial step."""
        self._show_popup(
            "Toggle Voice Typing",
            "Use the tray icon to start or stop voice typing."
        )
    
    def _show_microphone_step(self) -> None:
        """Show microphone tutorial step."""
        self._show_popup(
            "Microphone Selection",
            "Choose your preferred microphone from the 'Microphone' submenu in the tray icon."
        )
    
    def _show_done_step(self) -> None:
        """Show completion tutorial step."""
        self._show_popup(
            "You're Ready!",
            "That's it! You're ready to use Instant Typer. You can revisit this tutorial by deleting the '.first_run_complete' file in your ~/.instyper folder."
        )

# =============================================================================
# SPEECH RECOGNITION BACKENDS
# =============================================================================

class SpeechRecognitionBackend(abc.ABC):
    """Abstract base class for speech recognition backends."""
    
    def __init__(self, config: Dict[str, Any], models_dir: str):
        self.config = config
        self.models_dir = models_dir
    
    @abc.abstractmethod
    def is_available(self) -> bool:
        """Check if the backend is available and properly configured."""
        pass
    
    @abc.abstractmethod
    def recognize_speech(self, stop_event: threading.Event, 
                        mic_index: Optional[int], 
                        indicator: Optional[ListeningIndicator]) -> None:
        """Main speech recognition loop."""
        pass

class VoskBackend(SpeechRecognitionBackend):
    """Vosk speech recognition backend."""
    
    def __init__(self, config: Dict[str, Any], models_dir: str):
        super().__init__(config, models_dir)
        self.model = None
        self._load_model()
    
    def _load_model(self) -> None:
        """Load the Vosk model."""
        try:
            model_name = self.config.get('model')
            if not model_name:
                # Use default from models.json
                model_name = models_config.get_default_model_for_backend('vosk')
                if not model_name:
                    log("No default Vosk model found in models.json", 'error')
                    show_notification(AppConstants.APP_NAME, 'No default Vosk model found in models.json')
                    return
                self.config['model'] = model_name  # Optionally update config

            model_path = os.path.join(self.models_dir, model_name)
            if not os.path.isdir(model_path):
                log(f"Vosk model not found: {model_path}", 'warning')
                show_notification(AppConstants.APP_NAME, f'Vosk model not found: {model_path}')
                return

            self.model = Model(model_path)
            log(f"Loaded Vosk model: {model_path}")

        except Exception as e:
            log(f"Error loading Vosk model: {e}", 'error')
            self.model = None
    
    def is_available(self) -> bool:
        """Check if Vosk backend is available."""
        return self.model is not None
    
    def recognize_speech(self, stop_event: threading.Event, 
                        mic_index: Optional[int], 
                        indicator: Optional[ListeningIndicator]) -> None:
        """Vosk speech recognition main loop."""
        if not self.is_available():
            log("Vosk model not available", 'error')
            return
        
        if mic_index is None:
            log("No microphone selected", 'error')
            return
        
        p = pyaudio.PyAudio()
        stream = None
        
        try:
            stream = p.open(
                format=AppConstants.AUDIO_FORMAT,
                channels=AppConstants.AUDIO_CHANNELS,
                rate=AppConstants.AUDIO_RATE,
                input=True,
                input_device_index=mic_index,
                frames_per_buffer=AppConstants.FRAMES_PER_BUFFER
            )
            stream.start_stream()
            
            rec = KaldiRecognizer(self.model, AppConstants.AUDIO_RATE)
            log("Vosk recognition started. Speak into your microphone.")
            
            while not stop_event.is_set():
                data = stream.read(AppConstants.AUDIO_CHUNK, exception_on_overflow=False)
                
                if rec.AcceptWaveform(data):
                    result = rec.Result()
                    text = json.loads(result).get('text', '')
                    
                    if text and not stop_event.is_set():
                        # --- Encrypted speech log ---
                        if ConfigManager.is_speech_log_pincode_set():
                            try:
                                # Use a special marker to indicate logging is possible, but do not prompt
                                # Use the hash as a dummy pincode for key derivation (not secure, but avoids prompt)
                                # In production, you may want to store the real pincode in memory at set time
                                append_encrypted_speech_log(text, ConfigManager.load()['speech_log_pincode_hash'])
                            except Exception as e:
                                log(f"Error logging encrypted speech: {e}", 'error')
                        self._type_text(text, indicator)
                        
        except Exception as e:
            log(f"Error in Vosk recognition: {e}", 'error')
            show_notification(AppConstants.APP_NAME, f'Vosk error: {e}')
            
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            p.terminate()
    
    def _type_text(self, text: str, indicator: Optional[ListeningIndicator]) -> None:
        """Type the recognized text."""
        if indicator:
            indicator.label.config(text='Typing...')
        
        pyperclip.copy(text + " ")
        pyautogui.hotkey('ctrl', 'v')
        
        if indicator:
            indicator.label.config(text='Listening...')

class WhisperBackend(SpeechRecognitionBackend):
    """Whisper speech recognition backend."""
    
    def __init__(self, config: Dict[str, Any], models_dir: str):
        super().__init__(config, models_dir)
        self.model = None
        self._load_model()
    
    def _load_model(self) -> None:
        """Load the Whisper model."""
        try:
            import whisper
            model_name = self.config.get('model', 'base')
            self.model = whisper.load_model(model_name, download_root=self.models_dir)
            log(f"Loaded Whisper model: {model_name}")
            
        except ImportError:
            log("Whisper not installed. Please install with 'pip install openai-whisper'", 'error')
        except Exception as e:
            log(f"Error loading Whisper model: {e}", 'error')
            self.model = None
    
    def is_available(self) -> bool:
        """Check if Whisper backend is available."""
        return self.model is not None
    
    def recognize_speech(self, stop_event: threading.Event, 
                        mic_index: Optional[int], 
                        indicator: Optional[ListeningIndicator]) -> None:
        """Whisper speech recognition main loop."""
        if not self.is_available():
            log("Whisper model not available", 'error')
            return
        
        if mic_index is None:
            log("No microphone selected", 'error')
            return
        
        p = pyaudio.PyAudio()
        stream = None
        
        try:
            stream = p.open(
                format=AppConstants.AUDIO_FORMAT,
                channels=AppConstants.AUDIO_CHANNELS,
                rate=AppConstants.AUDIO_RATE,
                input=True,
                input_device_index=mic_index,
                frames_per_buffer=AppConstants.FRAMES_PER_BUFFER
            )
            stream.start_stream()
            
            log("Whisper recognition started. Speak into your microphone.")
            buffer = b''
            
            while not stop_event.is_set():
                data = stream.read(AppConstants.AUDIO_CHUNK, exception_on_overflow=False)
                buffer += data
                
                if len(buffer) >= AppConstants.MIN_AUDIO_BYTES:
                    self._process_audio_buffer(buffer[:AppConstants.MAX_AUDIO_BYTES], 
                                             p, stop_event, indicator)
                    buffer = b''
                    
        except Exception as e:
            log(f"Error in Whisper recognition: {e}", 'error')
            show_notification(AppConstants.APP_NAME, f'Whisper error: {e}')
            
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            p.terminate()
    
    def _process_audio_buffer(self, buffer: bytes, p: pyaudio.PyAudio, 
                             stop_event: threading.Event, 
                             indicator: Optional[ListeningIndicator]) -> None:
        """Process audio buffer with Whisper."""
        try:
            # Save buffer to temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_wav:
                wf = wave.open(tmp_wav, 'wb')
                wf.setnchannels(AppConstants.AUDIO_CHANNELS)
                wf.setsampwidth(p.get_sample_size(AppConstants.AUDIO_FORMAT))
                wf.setframerate(AppConstants.AUDIO_RATE)
                wf.writeframes(buffer)
                wf.close()
                wav_path = tmp_wav.name
            
            # Transcribe with Whisper
            log("Transcribing with Whisper...")
            lang = self.config.get('lang', 'en').lower()
            result = self.model.transcribe(wav_path, language=lang)
            text = result.get('text', '').strip()
            
            # Clean up temp file
            try:
                os.unlink(wav_path)
            except Exception:
                pass
            
            # Filter and type text
            if text and not is_useless_whisper_output(text) and not stop_event.is_set():
                # --- Encrypted speech log ---
                if ConfigManager.is_speech_log_pincode_set():
                    try:
                        append_encrypted_speech_log(text, ConfigManager.load()['speech_log_pincode_hash'])
                    except Exception as e:
                        log(f"Error logging encrypted speech: {e}", 'error')
                self._type_text(text, indicator)
                
        except Exception as e:
            log(f"Error processing Whisper audio: {e}", 'error')
    
    def _type_text(self, text: str, indicator: Optional[ListeningIndicator]) -> None:
        """Type the recognized text."""
        if indicator:
            indicator.label.config(text='Typing...')
        
        pyperclip.copy(text + " ")
        pyautogui.hotkey('ctrl', 'v')
        
        if indicator:
            indicator.label.config(text='Listening...')

# =============================================================================
# MAIN APPLICATION LOGIC
# =============================================================================

class VoiceTyper:
    """Main voice typing application class."""
    
    def __init__(self, indicator: Optional[ListeningIndicator] = None):
        self.indicator = indicator
        self.is_listening = False
        self.recognition_thread = None
        self.stop_event = threading.Event()
        self.tts_engine = pyttsx3.init()
        self.audio_manager = AudioDeviceManager()
        
        # Load configuration
        self.config = ConfigManager.load()
        
        # Set microphone from config
        mic_index = self.config.get('mic_index')
        if mic_index is not None:
            self.audio_manager.set_mic_index(mic_index)
        
        # Initialize backend and model
        self.selected_backend = self.config.get('backend', models_config.get_default_backend())
        self._ensure_model_for_backend()
        self.backend_instance = None
        self._initialize_backend()
        self.available_backends = self._get_available_backends()
        log(f"VoiceTyper initialized with backend: {self.selected_backend}")
    
    def _ensure_model_for_backend(self):
        """Ensure the selected model is valid for the current backend."""
        model_name = self.config.get('model')
        # Check if model matches backend
        valid = False
        if model_name:
            for m in models_config.get_backend_models(self.selected_backend):
                if m['model'] == model_name:
                    valid = True
                    break
        if not valid:
            default_model = models_config.get_default_model_for_backend(self.selected_backend)
            if default_model:
                self.config['model'] = default_model
                ConfigManager.save(self.config)
    
    def set_backend(self, backend_name: str) -> None:
        """Change the speech recognition backend."""
        if backend_name not in self.available_backends:
            log(f"Backend {backend_name} not available", 'error')
            return
        
        was_listening = self.is_listening
        if was_listening:
            self.toggle_listening()
        
        # Update backend in config
        self.config['backend'] = backend_name
        self.selected_backend = backend_name
        
        # Ensure model matches backend or set to default
        self._ensure_model_for_backend()
        
        # Save config
        ConfigManager.save(self.config)
        
        # Initialize new backend
        self._initialize_backend()
        
        log(f"Switched to backend: {backend_name}")
        show_notification(AppConstants.APP_NAME, f'Switched to backend: {backend_name}')
        
        if was_listening:
            self.toggle_listening()
    
    def set_microphone(self, mic_index: Optional[int]) -> None:
        """Set the microphone index."""
        was_listening = self.is_listening
        if was_listening:
            self.toggle_listening()
        
        # Update microphone selection
        self.audio_manager.set_mic_index(mic_index)
        self.config['mic_index'] = mic_index
        ConfigManager.save(self.config)
        
        if was_listening:
            self.toggle_listening()
    
    def set_model(self, model_name: str) -> None:
        """Set the model for the current backend."""
        was_listening = self.is_listening
        if was_listening:
            self.toggle_listening()
        
        # Update model in config
        self.config['model'] = model_name
        ConfigManager.save(self.config)
        
        # Reinitialize backend with new model
        self._initialize_backend()
        
        if was_listening:
            self.toggle_listening()
    
    def toggle_listening(self) -> None:
        """Toggle voice typing on/off."""
        self.is_listening = not self.is_listening
        
        if self.is_listening:
            if not self.backend_instance or not self.backend_instance.is_available():
                show_notification(AppConstants.APP_NAME, 'Backend not available. Please configure a model.')
                self.is_listening = False
                return
            
            show_notification(AppConstants.APP_NAME, 'Voice typing started')
            log("Voice typing started...")
            
            if self.indicator:
                self.indicator.label.config(text='Listening...')
                self.indicator.show()
            
            self.stop_event.clear()
            self.recognition_thread = threading.Thread(target=self._recognition_worker)
            self.recognition_thread.daemon = True
            self.recognition_thread.start()
        else:
            show_notification(AppConstants.APP_NAME, 'Voice typing stopped')
            log("Voice typing stopped.")
            
            self.stop_event.set()
            if self.recognition_thread:
                self.recognition_thread.join(timeout=2)
            
            if self.indicator:
                self.indicator.label.config(text='...')
                self.indicator.hide()
    
    def _recognition_worker(self) -> None:
        """Worker thread for speech recognition."""
        try:
            self.backend_instance.recognize_speech(
                self.stop_event,
                self.audio_manager.selected_mic_index,
                self.indicator
            )
        except Exception as e:
            log(f"Error in recognition worker: {e}", 'error')
            show_notification(AppConstants.APP_NAME, f'Recognition error: {e}')
    
    def show_model_manager(self, backend: str) -> None:
        """Show the model manager dialog for a specific backend."""
        if not self.indicator:
            return
        
        models_dir = os.path.join(AppConstants.USER_MODELS_DIR, backend)
        os.makedirs(models_dir, exist_ok=True)
        
        def on_download(backend: str, models_dir: str):
            log(f"Model download requested for {backend}")
        
        ModelManagerDialog(self.indicator.root, backend, models_dir, on_download, parent_app=self)
    
    def cleanup(self) -> None:
        """Clean up resources."""
        log("Cleaning up VoiceTyper...")
        self.stop_event.set()
        if self.recognition_thread and self.recognition_thread.is_alive():
            self.recognition_thread.join(timeout=2)
        log("VoiceTyper cleanup complete.")

    def _get_available_backends(self) -> List[str]:
        """Get list of available backends for current platform."""
        all_backends = ['vosk', 'whisper', 'speechbrain', 'coqui-stt']
        if platform.system() != 'Windows':
            all_backends.append('paddlepaddle')
        
        # Filter by what's actually available in models config
        available = list(set([m['backend'] for m in models_config.all_models]))
        return [b for b in all_backends if b in available]

    def _initialize_backend(self) -> None:
        """Initialize the speech recognition backend asynchronously using Celery, with fallback to sync if worker is not running."""
        model_name = self.config.get('model')
        backend = self.selected_backend
        if backend == 'vosk':
            models_dir = os.path.join(AppConstants.USER_MODELS_DIR, 'vosk')
            try:
                # Try Celery first
                async_result = celery_load_speech_model.delay('vosk', model_name, models_dir)
                result = async_result.get(timeout=10)
                if result.get('status') == 'ok':
                    self.backend_instance = VoskBackend({'model': model_name}, models_dir)
                else:
                    log(f"Error loading Vosk model (celery): {result.get('error')}", 'error')
                    self.backend_instance = None
            except Exception as e:
                log(f"Celery unavailable or timed out, loading Vosk model synchronously: {e}", 'warning')
                try:
                    self.backend_instance = VoskBackend({'model': model_name}, models_dir)
                except Exception as e2:
                    log(f"Error loading Vosk model (sync): {e2}", 'error')
                    self.backend_instance = None
        elif backend == 'whisper':
            models_dir = os.path.join(AppConstants.USER_MODELS_DIR, 'whisper')
            try:
                async_result = celery_load_speech_model.delay('whisper', model_name, models_dir)
                result = async_result.get(timeout=10)
                if result.get('status') == 'ok':
                    self.backend_instance = WhisperBackend({'model': model_name}, models_dir)
                else:
                    log(f"Error loading Whisper model (celery): {result.get('error')}", 'error')
                    self.backend_instance = None
            except Exception as e:
                log(f"Celery unavailable or timed out, loading Whisper model synchronously: {e}", 'warning')
                try:
                    self.backend_instance = WhisperBackend({'model': model_name}, models_dir)
                except Exception as e2:
                    log(f"Error loading Whisper model (sync): {e2}", 'error')
                    self.backend_instance = None
        else:
            log(f"Backend {backend} not implemented yet", 'warning')
            self.backend_instance = None

# =============================================================================
# SYSTEM TRAY INTEGRATION
# =============================================================================

class SystemTrayManager:
    """Manages the system tray icon and menu."""
    
    def __init__(self, voice_typer: VoiceTyper, indicator: ListeningIndicator):
        self.voice_typer = voice_typer
        self.indicator = indicator
        self.icon = None
        self._setup_icon()
    
    def _setup_icon(self) -> None:
        """Setup the system tray icon."""
        self.icon = pystray.Icon(AppConstants.APP_ID)
        self.icon.icon = create_icon()
        self.icon.title = self._get_icon_title()
        self.icon.menu = self._build_menu()
    
    def _get_icon_title(self) -> str:
        """Get the icon title showing current backend and model."""
        backend = self.voice_typer.selected_backend
        config = self.voice_typer.config
        model = None
        if backend == 'vosk':
            model = config.get('model')
        elif backend == 'whisper':
            model = config.get('model')
        if model:
            return f"{AppConstants.APP_NAME} ({backend}: {model})"
        return f"{AppConstants.APP_NAME} ({backend})"
    
    def _build_menu(self) -> pystray.Menu:
        """Build the system tray context menu."""
        return pystray.Menu(
            pystray.MenuItem(
                'Toggle Voice Typing',
                self._on_toggle,
                checked=lambda item: self.voice_typer.is_listening
            ),
            pystray.MenuItem(
                'Microphone',
                self._build_microphone_menu()
            ),
            pystray.MenuItem(
                'Backend',
                self._build_backend_menu()
            ),
            pystray.MenuItem(
                'Models',
                self._build_models_menu()
            ),
            pystray.MenuItem(
                'Settings',
                self._build_settings_menu()
            ),
            pystray.MenuItem('Exit', self._on_exit)
        )
    
    def _build_microphone_menu(self) -> pystray.Menu:
        """Build the microphone selection submenu."""
        mic_items = []
        # Add "Default" option
        def on_select_default(icon, item):
            self.voice_typer.set_microphone(None)
        def checked_default(item):
            return self.voice_typer.audio_manager.selected_mic_index is None
        mic_items.append(pystray.MenuItem(
            'Default',
            on_select_default,
            checked=checked_default
        ))
        # Add available microphones
        for idx, name in enumerate(self.voice_typer.audio_manager.get_mic_names()):
            def make_on_select(i):
                def on_select(icon, item):
                    self.voice_typer.set_microphone(i)
                return on_select
            def make_checked(i):
                def checked(item):
                    return self.voice_typer.audio_manager.selected_mic_index == i
                return checked
            mic_items.append(pystray.MenuItem(
                name,
                make_on_select(idx),
                checked=make_checked(idx)
            ))
        return pystray.Menu(*mic_items)
    
    def _build_backend_menu(self) -> pystray.Menu:
        """Build the backend selection submenu."""
        backend_items = []
        for backend in self.voice_typer.available_backends:
            def make_on_select(b):
                def on_select(icon, item):
                    self.voice_typer.set_backend(b)
                return on_select
            def make_checked(b):
                def checked(item):
                    return self.voice_typer.selected_backend == b
                return checked
            backend_items.append(pystray.MenuItem(
                backend,
                make_on_select(backend),
                checked=make_checked(backend)
            ))
        return pystray.Menu(*backend_items)
    
    def _build_models_menu(self) -> pystray.Menu:
        """Build the models management submenu."""
        model_items = []
        for backend in self.voice_typer.available_backends:
            def make_on_select(b):
                def on_select(icon, item):
                    self.voice_typer.show_model_manager(b)
                return on_select
            model_items.append(pystray.MenuItem(
                f"Manage {backend} models",
                make_on_select(backend)
            ))
        return pystray.Menu(*model_items)
    
    def _build_settings_menu(self) -> pystray.Menu:
        """Build the settings submenu."""
        return pystray.Menu(
            pystray.MenuItem('Set Speech Log Pincode', self._set_speech_log_pincode_gui),
            pystray.MenuItem('View Encrypted Speech Log', self._view_encrypted_speech_log_gui),
            pystray.MenuItem('Reset Settings', self._reset_settings),
            pystray.MenuItem('Show Tutorial', self._show_tutorial),
            pystray.MenuItem('Open Config Folder', self._open_config_folder)
        )
    
    def _on_toggle(self, icon, item) -> None:
        """Handle toggle voice typing."""
        self.voice_typer.toggle_listening()
        self.icon.icon = create_icon(self.voice_typer.is_listening)
        self.icon.title = self._get_icon_title()
        
        if self.voice_typer.is_listening:
            self.indicator.root.after(0, self.indicator.show)
        else:
            self.indicator.root.after(0, self.indicator.hide)
    
    def _reset_settings(self, icon, item) -> None:
        """Reset application settings."""
        if messagebox.askyesno("Confirm", "Reset all settings?"):
            try:
                ConfigManager.reset()
                show_notification(AppConstants.APP_NAME, 'Settings reset successfully.')
            except Exception as e:
                log(f"Error resetting settings: {e}", 'error')
    
    def _show_tutorial(self, icon, item) -> None:
        """Show the tutorial."""
        tutorial = TutorialManager(self.indicator.root, self.icon)
        self.indicator.root.after(100, tutorial.start)
    
    def _open_config_folder(self, icon, item) -> None:
        """Open the configuration folder."""
        try:
            if platform.system() == 'Windows':
                os.startfile(AppConstants.USER_HOME_DIR)
            elif platform.system() == 'Darwin':
                os.system(f'open "{AppConstants.USER_HOME_DIR}"')
            else:
                os.system(f'xdg-open "{AppConstants.USER_HOME_DIR}"')
        except Exception as e:
            log(f"Error opening config folder: {e}", 'error')
    
    def _on_exit(self, icon, item) -> None:
        """Handle application exit with warm shutdown and download check."""
        # Check for any open ModelManagerDialog with download in progress
        import tkinter.messagebox
        for w in self.indicator.root.winfo_children():
            if hasattr(w, 'downloading') and getattr(w, 'downloading', False):
                if not tkinter.messagebox.askyesno("Download in progress", "A model download is in progress. Do you want to stop the download and exit?"):
                    return  # Abort exit
        icon.stop()
        self.indicator.destroy()
        self.voice_typer.cleanup()
        # Join all non-daemon threads except the main thread
        import threading, time
        main_thread = threading.current_thread()
        for t in threading.enumerate():
            if t is not main_thread and t.is_alive() and not t.daemon:
                t.join(timeout=2)
        time.sleep(0.2)  # Give a moment for cleanup
        os._exit(0)
    
    def run(self) -> None:
        """Run the system tray icon."""
        self.icon.run()

    def _set_speech_log_pincode_gui(self, icon, item):
        # Tkinter dialog for pincode entry/confirmation
        def on_ok():
            pin = entry.get()
            pin2 = entry2.get()
            if not (pin.isdigit() and len(pin) == 6):
                messagebox.showerror("Invalid Pincode", "Pincode must be 6 digits.")
                return
            if pin != pin2:
                messagebox.showerror("Mismatch", "Pincodes do not match.")
                return
            ConfigManager.set_speech_log_pincode(pin)
            top.destroy()
            show_notification(AppConstants.APP_NAME, "Speech log pincode set.")
        top = tk.Toplevel(None)
        top.title("Set Speech Log Pincode")
        tk.Label(top, text="Enter 6-digit pincode:").pack(padx=10, pady=(10,2))
        entry = tk.Entry(top, show='*', width=10)
        entry.pack(padx=10)
        tk.Label(top, text="Confirm pincode:").pack(padx=10, pady=(10,2))
        entry2 = tk.Entry(top, show='*', width=10)
        entry2.pack(padx=10)
        btn = tk.Button(top, text="OK", command=on_ok)
        btn.pack(pady=10)
        entry.focus_set()

    def _view_encrypted_speech_log_gui(self, icon, item):
        import tkinter.simpledialog
        import tkinter.scrolledtext
        # Prompt for pincode
        pin = tkinter.simpledialog.askstring("Speech Log Pincode", "Enter 6-digit pincode to view speech log:", show='*', parent=None)
        if not pin:
            return
        if not ConfigManager.verify_speech_log_pincode(pin):
            messagebox.showerror("Incorrect Pincode", "The pincode you entered is incorrect.")
            return
        # Try to decrypt log
        try:
            if not os.path.isfile(AppConstants.SPEECH_LOG_PATH):
                messagebox.showinfo("Speech Log", "No speech log data found.")
                return
            data = decrypt_speech_log(pin)
            if not data.strip():
                messagebox.showinfo("Speech Log", "Speech log is empty.")
                return
            # Show in scrollable dialog
            top = tk.Toplevel(None)
            top.title("Decrypted Speech Log")
            top.geometry("600x400")
            st = tkinter.scrolledtext.ScrolledText(top, wrap=tk.WORD, font=("Arial", 11))
            st.pack(fill=tk.BOTH, expand=True)
            st.insert(tk.END, data)
            st.config(state=tk.DISABLED)
            tk.Button(top, text="Close", command=top.destroy).pack(pady=5)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to decrypt speech log: {e}")

# =============================================================================
# GLOBAL HOTKEY HANDLER
# =============================================================================

def setup_global_hotkey(voice_typer: VoiceTyper) -> None:
    """Setup global hotkey for toggling voice typing."""
    def on_hotkey():
        voice_typer.toggle_listening()
        show_notification(AppConstants.APP_NAME, 'Voice typing toggled by keyboard shortcut')
    
    def keyboard_listener():
        try:
            from pynput.keyboard import GlobalHotKeys
            with GlobalHotKeys({AppConstants.GLOBAL_HOTKEY: on_hotkey}) as h:
                h.join()
        except Exception as e:
            log(f"Error setting up global hotkey: {e}", 'error')
    
    threading.Thread(target=keyboard_listener, daemon=True).start()
    log(f"Global hotkey registered: {AppConstants.GLOBAL_HOTKEY}")

# =============================================================================
# MAIN APPLICATION ENTRY POINT
# =============================================================================

def main() -> None:
    """Main application entry point."""
    log(f"Starting {AppConstants.APP_NAME}...")
    
    # Initialize components
    indicator = ListeningIndicator()
    voice_typer = VoiceTyper(indicator=indicator)
    tray_manager = SystemTrayManager(voice_typer, indicator)
    
    # Setup cleanup
    atexit.register(voice_typer.cleanup)
    
    # Setup global hotkey
    setup_global_hotkey(voice_typer)
    
    # Show tutorial for first-time users
    if not os.path.isfile(AppConstants.FIRST_RUN_FLAG):
        tutorial = TutorialManager(indicator.root, tray_manager.icon)
        indicator.root.after(1000, tutorial.start)
    
    # Ensure default model for every backend is present
    for backend in set(m['backend'] for m in models_config.all_models):
        default_model = models_config.get_default_model_for_backend(backend)
        if not default_model:
            continue
        model_dir = os.path.join(AppConstants.USER_MODELS_DIR, backend, default_model)
        if not os.path.isdir(model_dir):
            try:
                download_model = None
                for m in models_config.get_backend_models(backend):
                    if m['model'] == default_model:
                        download_model = m
                        break
                if download_model:
                    if backend == 'vosk':
                        VoskModelDownloader(download_model, os.path.join(AppConstants.USER_MODELS_DIR, backend)).download()
                    elif backend == 'whisper':
                        WhisperModelDownloader(download_model['model'], os.path.join(AppConstants.USER_MODELS_DIR, backend)).download()
                    # Add similar logic for other backends if needed
            except Exception as e:
                log(f"Error downloading {backend} default model: {e}", 'error')
    
    # Start system tray in separate thread
    tray_thread = threading.Thread(target=tray_manager.run, daemon=True)
    tray_thread.start()
    
    # Run main UI loop
    try:
        indicator.root.mainloop()
    except KeyboardInterrupt:
        log("Application interrupted by user")
    finally:
        voice_typer.cleanup()

# =============================================================================
# STANDALONE FUNCTIONS FOR COMMAND LINE USAGE
# =============================================================================

def vosk_multilang_recognize() -> None:
    """
    Standalone function for multi-language Vosk recognition.
    Useful for testing and command-line usage.
    """
    import pyaudio
    from vosk import Model, KaldiRecognizer
    
    # Simple language model mapping for standalone use
    lang_models = {
        'EN': 'vosk-model-small-en-us-0.15',
        'DE': 'vosk-model-small-de-zamia-0.3',
        'NL': 'vosk-model-small-nl-0.22',
        'FR': 'vosk-model-small-fr-0.22',
        'TR': 'vosk-model-small-tr-0.3',
    }
    
    def select_language():
        print("Select a language:")
        for idx, lang in enumerate(lang_models.keys(), 1):
            print(f"  {idx}. {lang}")
        choice = input("Enter number: ").strip()
        try:
            idx = int(choice) - 1
            return list(lang_models.keys())[idx]
        except (ValueError, IndexError):
            print("Invalid selection.")
            sys.exit(1)
    
    # Get language and model
    lang = select_language()
    model_dir = lang_models[lang]
    model_path = os.path.join(AppConstants.USER_MODELS_DIR, 'vosk', model_dir)
    
    if not os.path.isdir(model_path):
        print(f"Model directory not found: {model_path}")
        print("Please ensure the model is downloaded.")
        sys.exit(1)
    
    # Initialize Vosk
    print(f"Loading model for {lang} from {model_path}...")
    model = Model(model_path)
    
    # Setup audio
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=8000
    )
    stream.start_stream()
    
    rec = KaldiRecognizer(model, 16000)
    print("Speak into your microphone. Press Ctrl+C to stop.")
    
    try:
        while True:
            data = stream.read(4000, exception_on_overflow=False)
            if rec.AcceptWaveform(data):
                result = rec.Result()
                text = json.loads(result).get('text', '')
                if text:
                    print(f"Recognized: {text}")
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

# =============================================================================
# SCRIPT ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--vosk-test':
        vosk_multilang_recognize()
    else:
        main()

# Encryption utilities for speech log

def _get_speech_log_key(pincode: str) -> bytes:
    """Derive a Fernet key from the pincode using PBKDF2 and a persistent salt."""
    if not Fernet:
        raise ImportError("cryptography is required for encrypted speech log.")
    salt_path = AppConstants.SPEECH_LOG_SALT_PATH
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

def append_encrypted_speech_log(text: str, pincode: str) -> None:
    key = _get_speech_log_key(pincode)
    f = Fernet(key)
    enc = f.encrypt(text.encode('utf-8'))
    with open(AppConstants.SPEECH_LOG_PATH, 'ab') as logf:
        logf.write(enc + b'\n')

def decrypt_speech_log(pincode: str) -> str:
    key = _get_speech_log_key(pincode)
    f = Fernet(key)
    lines = []
    with open(AppConstants.SPEECH_LOG_PATH, 'rb') as logf:
        for line in logf:
            line = line.strip()
            if not line:
                continue
            try:
                dec = f.decrypt(line).decode('utf-8')
                lines.append(dec)
            except InvalidToken:
                lines.append('[DECRYPTION FAILED]')
    return '\n'.join(lines)

# Use in-memory broker for local development if not specified
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'memory://')
CELERY_BACKEND_URL = os.environ.get('CELERY_BACKEND_URL', 'rpc://')
celery_app = Celery('instyper', broker=CELERY_BROKER_URL, backend=CELERY_BACKEND_URL)

# Celery tasks for model management and config changes
@celery_app.task
def celery_download_model(backend, model_info, models_dir):
    """Download a model for a backend (runs in background)."""
    try:
        downloader_cls = MODEL_DOWNLOADER_CLASSES.get(backend)
        if not downloader_cls:
            return f"No downloader for backend {backend}"
        if backend == 'whisper':
            downloader = downloader_cls(model_info['model'], models_dir)
        else:
            downloader = downloader_cls(model_info, models_dir)
        downloader.download()
        return f"Download started for {backend}:{model_info.get('model', model_info.get('name', ''))}"
    except Exception as e:
        return f"Error: {e}"

@celery_app.task
def celery_change_config(key, value):
    """Change a config value (runs in background)."""
    try:
        config = ConfigManager.load()
        config[key] = value
        ConfigManager.save(config)
        return f"Config {key} set to {value}"
    except Exception as e:
        return f"Error: {e}"

@celery_app.task
def celery_set_backend(backend_name):
    """Change backend (runs in background)."""
    return celery_change_config.s('backend', backend_name)()

@celery_app.task
def celery_set_model(model_name):
    """Change model (runs in background)."""
    return celery_change_config.s('model', model_name)()

# Celery tasks for database/config management
@celery_app.task
def celery_load_config():
    """Load configuration from the database (runs in background)."""
    try:
        return ConfigManager.load()
    except Exception as e:
        return {"error": str(e)}

@celery_app.task
def celery_save_config(data):
    """Save configuration to the database (runs in background)."""
    try:
        ConfigManager.save(data)
        return {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}

@celery_app.task
def celery_reset_config():
    """Reset configuration to defaults (runs in background)."""
    try:
        ConfigManager.reset()
        return {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}

# Example usage:
# celery_load_config.delay().get()
# celery_save_config.delay(new_config).get()
# celery_reset_config.delay().get()

# Celery task for loading a speech model (returns model path or error)
@celery_app.task
def celery_load_speech_model(backend, model_name, models_dir):
    try:
        if backend == 'vosk':
            from vosk import Model
            model_path = os.path.join(models_dir, model_name)
            if not os.path.isdir(model_path):
                return {'error': f'Model not found: {model_path}'}
            model = Model(model_path)
            return {'status': 'ok', 'model_path': model_path}
        elif backend == 'whisper':
            import whisper
            model = whisper.load_model(model_name, download_root=models_dir)
            return {'status': 'ok', 'model_name': model_name}
        # Add other backends as needed
        return {'error': f'Backend {backend} not supported'}
    except Exception as e:
        return {'error': str(e)}
