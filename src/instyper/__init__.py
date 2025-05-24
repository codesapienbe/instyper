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
import tensorflow as tf
import numpy as np
import soundfile as sf

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
    except Exception as e:
        print(f"Error saving config: {e}")

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

VOSK_MODEL_LIST_URL = 'https://alphacephei.com/vosk/models/model-list.json'
WHISPER_MODELS = [
    'tiny', 'tiny.en', 'base', 'base.en', 'small', 'small.en', 'medium', 'medium.en', 'large', 'large-v2', 'large-v3', 'turbo'
]
SPEECHBRAIN_MODELS = [
    {
        'name': 'speechbrain/asr-transformer-transformerlm-librispeech',
        'lang': 'en',
        'desc': 'English ASR Transformer (LibriSpeech)'
    }
]
COQUI_MODELS = [
    {
        'name': 'coqui/stt-en',
        'lang': 'en',
        'desc': 'English STT (Coqui)'
    }
]
PADDLESPEECH_MODELS = [
    {
        'name': 'paddlespeech/asr-conformer-en',
        'lang': 'en',
        'desc': 'English ASR Conformer (PaddleSpeech)'
    }
]

def human_size(nbytes):
    if nbytes is None:
        return ''
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    while nbytes >= 1024 and i < len(suffixes)-1:
        nbytes /= 1024.
        i += 1
    f = ('%.2f' % nbytes).rstrip('0').rstrip('.')
    return f'{f} {suffixes[i]}'

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
        self.download_btn = tk.Button(self.top, text="Download selected model", command=self.download_model)
        self.download_btn.pack(pady=8)
        tk.Button(self.top, text="Close", command=self.top.destroy).pack(pady=2)
        self.listbox.bind('<<ListboxSelect>>', self.on_select)
        self.selected_model = None
        self.downloading = False

    def refresh_models(self):
        self.listbox.delete(0, tk.END)
        self.available_models = []
        if self.backend == 'vosk':
            try:
                resp = requests.get(VOSK_MODEL_LIST_URL, timeout=10)
                models = resp.json()
                for m in models:
                    name = m.get('name')
                    lang = m.get('lang', '')
                    size = m.get('filesize', None)
                    size_str = human_size(size)
                    notes = m.get('notes', '')
                    display = f"{name} | {lang} | {size_str} | {notes}"
                    self.listbox.insert(tk.END, display)
                    self.available_models.append(m)
            except Exception as e:
                self.listbox.insert(tk.END, f"Error fetching model list: {e}")
        elif self.backend == 'whisper':
            for m in WHISPER_MODELS:
                self.listbox.insert(tk.END, m)
                self.available_models.append({'name': m})
        elif self.backend == 'speechbrain':
            for m in SPEECHBRAIN_MODELS:
                display = f"{m['name']} | {m['lang']} | {m['desc']}"
                self.listbox.insert(tk.END, display)
                self.available_models.append(m)
        elif self.backend == 'coqui-stt':
            for m in COQUI_MODELS:
                display = f"{m['name']} | {m['lang']} | {m['desc']}"
                self.listbox.insert(tk.END, display)
                self.available_models.append(m)
        elif self.backend == 'paddlepaddle':
            for m in PADDLESPEECH_MODELS:
                display = f"{m['name']} | {m['lang']} | {m['desc']}"
                self.listbox.insert(tk.END, display)
                self.available_models.append(m)
        else:
            self.listbox.insert(tk.END, "Model download not implemented for this backend.")
        self.progress_var.set('')
        self.selected_model = None

    def on_select(self, event):
        idx = self.listbox.curselection()
        if idx:
            self.selected_model = self.available_models[idx[0]]
        else:
            self.selected_model = None

    def download_model(self):
        if self.downloading or not self.selected_model:
            return
        self.downloading = True
        self.progress_var.set('Starting download...')
        self.download_btn.config(state=tk.DISABLED)
        threading.Thread(target=self._download_model_thread, daemon=True).start()

    def _download_model_thread(self):
        try:
            if self.backend == 'vosk':
                url = self.selected_model.get('url')
                name = self.selected_model.get('name')
                if not url or not name:
                    self.progress_var.set('Invalid model info.')
                    return
                dest_zip = os.path.join(self.models_dir, name + '.zip')
                dest_dir = os.path.join(self.models_dir, name)
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
                model_name = self.selected_model['name']
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
                    whisper.load_model(model_name)
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
                model_name = self.selected_model['name']
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
                model_name = self.selected_model['name']
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
                model_name = self.selected_model['name']
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
        # Vosk language selection
        self.LANG_MODELS = {
            'EN': 'vosk-model-small-en-us-0.15',
            'DE': 'vosk-model-small-de-zamia-0.3',
            'NL': 'vosk-model-small-nl-0.22',
            'FR': 'vosk-model-small-fr-0.22',
            'TR': 'vosk-model-small-tr-0.3',
            'ES': 'vosk-model-small-es-0.42',
            'CN': 'vosk-model-small-cn-0.22',
            'CS': 'vosk-model-small-cs-0.4-rhasspy',
            'HI': 'vosk-model-small-hi-0.22',
            'IT': 'vosk-model-small-it-0.22',
            'JA': 'vosk-model-small-ja-0.22',
            'KO': 'vosk-model-small-ko-0.22',
            'KZ': 'vosk-model-small-kz-0.15',
            'PL': 'vosk-model-small-pl-0.22',
            'RU': 'vosk-model-small-ru-0.22',
            'SV': 'vosk-model-small-sv-rhasspy-0.15',
            'TE': 'vosk-model-small-te-0.42',
            'UK': 'vosk-model-small-uk-v3-small',
            'UZ': 'vosk-model-small-uz-0.22',
            'FA': 'vosk-model-small-fa-0.42',
        }
        # Backend-specific models directory
        self.MODELS_ROOT = USER_MODELS_DIR
        self.MODELS_DIR = os.path.join(self.MODELS_ROOT, 'vosk')
        os.makedirs(self.MODELS_DIR, exist_ok=True)
        config = load_config()
        self.selected_lang = config.get('lang', 'EN')  # Default to English
        self.model_path = self.get_model_path(self.selected_lang)
        try:
            self.model = Model(self.model_path)
            show_notification('Instant Typer', f'Model loaded: {self.model_path}')
        except Exception as e:
            show_notification('Instant Typer', f'Error loading model: {e}')
        # Backend selection
        self.BACKENDS = ['vosk', 'whisper', 'speechbrain', 'coqui-stt', 'paddlepaddle', 'espnet']
        self.selected_backend = config.get('backend', 'vosk')  # Default to vosk

    def set_language(self, lang_code):
        if lang_code not in self.LANG_MODELS:
            print(f"Language {lang_code} not supported.")
            return
        save_config({'backend': self.selected_backend, 'lang': lang_code, 'mic_index': self.selected_mic_index})
        was_listening = self.is_listening
        if was_listening:
            self.toggle_listening()  # Stop
        self.selected_lang = lang_code
        # Always use backend-specific model dir
        self.MODELS_DIR = os.path.join(self.MODELS_ROOT, self.selected_backend)
        os.makedirs(self.MODELS_DIR, exist_ok=True)
        self.model_path = self.get_model_path(self.selected_lang)
        try:
            self.model = Model(self.model_path)
            show_notification('Instant Typer', f'Model loaded: {self.model_path}')
        except Exception as e:
            show_notification('Instant Typer', f'Error loading model: {e}')
        print(f"Switched to language: {lang_code}")
        show_notification('Instant Typer', f'Switched to language: {lang_code}')
        self.tts_engine.say(f"Language changed to {lang_code}")
        self.tts_engine.runAndWait()
        if was_listening:
            self.toggle_listening()  # Restart

    def get_model_path(self, lang_code):
        # Use backend-specific logic for model path
        if self.selected_backend == 'vosk':
            model_dir = self.LANG_MODELS[lang_code]
            path = os.path.join(self.MODELS_DIR, model_dir)
            if not os.path.isdir(path):
                print(f"Model directory not found: {path}")
                print("Attempting to download and extract small Vosk models...")
                download_and_extract_small_vosk_models()
                if not os.path.isdir(path):
                    print("Model still not found after download. Please check your internet connection or model availability.")
                    sys.exit(1)
            return path
        elif self.selected_backend == 'whisper':
            # For whisper, just return the backend dir (model will be loaded by whisper)
            return self.MODELS_DIR
        elif self.selected_backend == 'speechbrain':
            # For speechbrain, return the backend dir (model will be loaded by speechbrain)
            return self.MODELS_DIR
        else:
            # For other backends, return the backend dir (placeholder)
            return self.MODELS_DIR

    def set_backend(self, backend_name):
        if backend_name not in self.BACKENDS:
            print(f"Backend {backend_name} not supported.")
            return
        save_config({'backend': backend_name, 'lang': self.selected_lang, 'mic_index': self.selected_mic_index})
        # Show model manager dialog on backend change
        if self.indicator and hasattr(self.indicator, 'root'):
            self.show_model_manager()
        was_listening = self.is_listening
        if was_listening:
            self.toggle_listening()  # Stop
        self.selected_backend = backend_name
        # Update backend-specific model dir
        self.MODELS_DIR = os.path.join(self.MODELS_ROOT, backend_name)
        os.makedirs(self.MODELS_DIR, exist_ok=True)
        print(f"Switched to backend: {backend_name}")
        show_notification('Instant Typer', f'Switched to backend: {backend_name}')
        self.tts_engine.say(f"Backend changed to {backend_name}")
        self.tts_engine.runAndWait()
        if was_listening:
            self.toggle_listening()  # Restart

    def start(self):
        print("Instant Typer is running. Use the tray icon to start/stop voice typing.")
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.cleanup()

    def toggle_listening(self):
        self.is_listening = not self.is_listening
        if self.is_listening:
            show_notification('Instant Typer', 'Voice typing started')
            print("Voice typing started...")
            if self.indicator:
                self.indicator.label.config(text='Listening...')
                self.indicator.show()
            self.stop_event.clear()
            self.recognition_thread = threading.Thread(target=self.recognize_speech)
            self.recognition_thread.daemon = True
            self.recognition_thread.start()
        else:
            show_notification('Instant Typer', 'Voice typing stopped')
            print("Voice typing stopped.")
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
            if self.selected_mic_index is None:
                print("No microphone selected.")
                return
            p = pyaudio.PyAudio()
            try:
                stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, input_device_index=self.selected_mic_index, frames_per_buffer=8000)
                stream.start_stream()
                rec = KaldiRecognizer(self.model, 16000)
                print("Speak into your microphone. Press Ctrl+C to stop.")
                while not self.stop_event.is_set():
                    data = stream.read(4000, exception_on_overflow=False)
                    if rec.AcceptWaveform(data):
                        result = rec.Result()
                        text = json.loads(result).get('text', '')
                        if text and not self.stop_event.is_set():
                            print(f"Typing: {text}")
                            if self.indicator:
                                self.indicator.label.config(text='Typing...')
                            pyperclip.copy(text + " ")
                            pyautogui.hotkey('ctrl', 'v')
                            if self.indicator:
                                self.indicator.label.config(text='Listening...')
            except Exception as e:
                print(f"Error with Vosk recognition: {e}")
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
                print("Whisper is not installed. Please install it with 'pip install openai-whisper'.")
                show_notification('Instant Typer', 'Whisper is not installed. Please install openai-whisper.')
                return
            if self.selected_mic_index is None:
                print("No microphone selected.")
                return
            p = pyaudio.PyAudio()
            try:
                stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, input_device_index=self.selected_mic_index, frames_per_buffer=8000)
                stream.start_stream()
                print("Speak into your microphone. Press Ctrl+C to stop.")
                model = whisper.load_model('base')
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
                        print("Transcribing with Whisper...")
                        result = model.transcribe(wav_path, language=self.selected_lang.lower())
                        text = result.get('text', '').strip()
                        if text and not self.stop_event.is_set():
                            print(f"Typing: {text}")
                            if self.indicator:
                                self.indicator.label.config(text='Typing...')
                            pyperclip.copy(text + " ")
                            pyautogui.hotkey('ctrl', 'v')
                            if self.indicator:
                                self.indicator.label.config(text='Listening...')
                        buffer = b''
            except Exception as e:
                print(f"Error with Whisper recognition: {e}")
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
                print("SpeechBrain is not installed. Please install it with 'pip install speechbrain'.")
                show_notification('Instant Typer', 'SpeechBrain is not installed. Please install speechbrain.')
                return
            if self.selected_mic_index is None:
                print("No microphone selected.")
                return
            p = pyaudio.PyAudio()
            try:
                stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, input_device_index=self.selected_mic_index, frames_per_buffer=8000)
                stream.start_stream()
                print("Speak into your microphone. Press Ctrl+C to stop.")
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
                        print("Transcribing with SpeechBrain...")
                        text = asr.transcribe_file(wav_path)
                        if text and not self.stop_event.is_set():
                            print(f"Typing: {text}")
                            if self.indicator:
                                self.indicator.label.config(text='Typing...')
                            pyperclip.copy(text + " ")
                            pyautogui.hotkey('ctrl', 'v')
                            if self.indicator:
                                self.indicator.label.config(text='Listening...')
                        buffer = b''
            except Exception as e:
                print(f"Error with SpeechBrain recognition: {e}")
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
                print("Coqui STT is not installed. Please install it with 'pip install stt huggingface_hub'.")
                show_notification('Instant Typer', 'Coqui STT is not installed. Please install stt and huggingface_hub.')
                return
            if self.selected_mic_index is None:
                print("No microphone selected.")
                return
            p = pyaudio.PyAudio()
            try:
                stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, input_device_index=self.selected_mic_index, frames_per_buffer=8000)
                stream.start_stream()
                print("Speak into your microphone. Press Ctrl+C to stop.")
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
                        print("Transcribing with Coqui STT...")
                        import numpy as np
                        import wave as pywave
                        with pywave.open(wav_path, 'rb') as wf:
                            frames = wf.readframes(wf.getnframes())
                            audio = np.frombuffer(frames, np.int16)
                        text = model.stt(audio)
                        if text and not self.stop_event.is_set():
                            print(f"Typing: {text}")
                            if self.indicator:
                                self.indicator.label.config(text='Typing...')
                            pyperclip.copy(text + " ")
                            pyautogui.hotkey('ctrl', 'v')
                            if self.indicator:
                                self.indicator.label.config(text='Listening...')
                        buffer = b''
            except Exception as e:
                print(f"Error with Coqui STT recognition: {e}")
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
        elif self.selected_backend == 'paddlepaddle':
            try:
                from paddlespeech.cli.asr.infer import ASRExecutor
            except ImportError:
                print("PaddleSpeech is not installed. Please install it with 'pip install paddlespeech huggingface_hub'.")
                show_notification('Instant Typer', 'PaddleSpeech is not installed. Please install paddlespeech and huggingface_hub.')
                return
            if self.selected_mic_index is None:
                print("No microphone selected.")
                return
            p = pyaudio.PyAudio()
            try:
                stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, input_device_index=self.selected_mic_index, frames_per_buffer=8000)
                stream.start_stream()
                print("Speak into your microphone. Press Ctrl+C to stop.")
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
                        print("Transcribing with PaddleSpeech...")
                        text = asr(audio_file=wav_path, model='conformer', lang='en', sample_rate=16000, config=None, ckpt_path=None, device='cpu')
                        if text and not self.stop_event.is_set():
                            print(f"Typing: {text}")
                            if self.indicator:
                                self.indicator.label.config(text='Typing...')
                            pyperclip.copy(text + " ")
                            pyautogui.hotkey('ctrl', 'v')
                            if self.indicator:
                                self.indicator.label.config(text='Listening...')
                        buffer = b''
            except Exception as e:
                print(f"Error with PaddleSpeech recognition: {e}")
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
            print(f"Unknown backend: {self.selected_backend}")
            show_notification('Instant Typer', f'Unknown backend: {self.selected_backend}')

    def cleanup(self):
        print("Cleaning up...")
        self.stop_event.set()
        if self.recognition_thread and self.recognition_thread.is_alive():
            self.recognition_thread.join(timeout=2)
        print("Instant Typer stopped.")

    def show_model_manager(self):
        def on_download(backend, models_dir):
            show_notification('Model Manager', f'Download for {backend} not implemented yet.')
        ModelManagerDialog(self.indicator.root, self.selected_backend, self.MODELS_DIR, on_download)

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
    print("Starting Instant Typer...")
    indicator = ListeningIndicator()
    voice_typer = VoiceTyper(indicator=indicator)
    atexit.register(voice_typer.cleanup)
    icon = pystray.Icon("instyper")
    icon.icon = create_icon()
    icon.title = f"Instant Typer ({voice_typer.selected_backend})"
    threads = {}

    # Microphone selection logic for tray menu
    def on_select_mic(idx):
        voice_typer.set_mic_index(idx - 1)  # -1 means default
        icon.update_menu()
    def mic_checked(idx):
        # Default is checked if selected_mic_index is None
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

    # Language selection logic for tray menu
    def on_select_lang(lang_code):
        voice_typer.set_language(lang_code)
        icon.update_menu()
    def lang_checked(lang_code):
        return voice_typer.selected_lang == lang_code
    def make_lang_menu_item(lang_code):
        def on_select(icon, item):
            on_select_lang(lang_code)
        def is_checked(item):
            return lang_checked(lang_code)
        return pystray.MenuItem(lang_code, on_select, checked=is_checked)
    lang_menu_items = [make_lang_menu_item(lang) for lang in voice_typer.LANG_MODELS.keys()]

    # Backend selection logic for tray menu
    def on_select_backend(backend_name):
        voice_typer.set_backend(backend_name)
        icon.title = f"Instant Typer ({voice_typer.selected_backend})"
        icon.update_menu()
    def backend_checked(backend_name):
        return voice_typer.selected_backend == backend_name
    def make_backend_menu_item(backend_name):
        if backend_name in ['vosk', 'whisper']:
            def on_select(icon, item):
                on_select_backend(backend_name)
            def is_checked(item):
                return backend_checked(backend_name)
            return pystray.MenuItem(backend_name, on_select, checked=is_checked)
        else:
            # Show as disabled (not selectable)
            return pystray.MenuItem(f"{backend_name} (not implemented)", None, enabled=False)
    backend_menu_items = [make_backend_menu_item(backend) for backend in voice_typer.BACKENDS]

    def on_exit(icon, item):
        icon.stop()
        indicator.destroy()
        voice_typer.cleanup()
        for t in threads.values():
            if t.is_alive():
                t.join(timeout=2)
        os._exit(0)
    def on_toggle(icon, item):
        voice_typer.toggle_listening()
        icon.icon = create_icon(voice_typer.is_listening)
        icon.title = f"Instant Typer ({voice_typer.selected_backend})"
        icon.update_menu()
        if voice_typer.is_listening:
            indicator.root.after(0, indicator.show)
        else:
            indicator.root.after(0, indicator.hide)
    icon.menu = pystray.Menu(
        pystray.MenuItem(
            'Toggle Voice Typing',
            on_toggle,
            checked=lambda item: voice_typer.is_listening
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
            'Exit',
            on_exit
        )
    )
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
        print("Select a language:")
        for idx, lang in enumerate(LANG_MODELS.keys(), 1):
            print(f"  {idx}. {lang}")
        choice = input("Enter number: ").strip()
        try:
            idx = int(choice) - 1
            lang = list(LANG_MODELS.keys())[idx]
            return lang
        except (ValueError, IndexError):
            print("Invalid selection.")
            sys.exit(1)

    def get_model_path(lang_code):
        model_dir = LANG_MODELS[lang_code]
        path = os.path.join(MODELS_DIR, model_dir)
        if not os.path.isdir(path):
            print(f"Model directory not found: {path}")
            print("Please ensure the model is extracted correctly.")
            sys.exit(1)
        return path

    print("Vosk Multi-language Speech Recognition")
    lang = select_language()
    model_path = get_model_path(lang)
    print(f"Loading model for {lang} from {model_path} ...")
    model = Model(model_path)

    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)
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

def download_and_extract_small_vosk_models():
    """
    Downloads all Vosk models with 'small' in their URL from https://alphacephei.com/vosk/models,
    extracts them to ~/.instyper/models, and skips extraction if the model directory already exists.
    """
    MODELS_URL = "https://alphacephei.com/vosk/models"
    print(f"Fetching model list from {MODELS_URL} ...")
    resp = requests.get(MODELS_URL)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    links = soup.find_all("a")
    model_links = [a["href"] for a in links if a.has_attr("href") and "small" in a["href"] and a["href"].endswith(".zip")]
    print(f"Found {len(model_links)} small models to process.")
    os.makedirs(USER_MODELS_DIR, exist_ok=True)
    for link in model_links:
        model_url = link if link.startswith("http") else f"https://alphacephei.com/vosk/models/{link}"
        model_zip_name = os.path.basename(model_url)
        model_dir_name = model_zip_name[:-4] if model_zip_name.endswith('.zip') else model_zip_name
        model_dir_path = os.path.join(USER_MODELS_DIR, model_dir_name)
        if os.path.isdir(model_dir_path):
            print(f"Model directory already exists, skipping: {model_dir_name}")
            continue
        print(f"Downloading {model_url} ...")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmpf:
            r = requests.get(model_url, stream=True)
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    tmpf.write(chunk)
            tmpf.flush()
            print(f"Extracting {model_zip_name} to {model_dir_path} ...")
            with zipfile.ZipFile(tmpf.name, 'r') as zip_ref:
                zip_ref.extractall(USER_MODELS_DIR)
        print(f"Model {model_dir_name} extracted.")
    print("All small models processed.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Instant Typer")
    parser.add_argument('--download-models', action='store_true', help='Download and extract all small Vosk models')
    args = parser.parse_args()
    if args.download_models:
        download_and_extract_small_vosk_models()
    else:
        main()
