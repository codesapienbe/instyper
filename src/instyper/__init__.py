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
        self.selected_mic_index = 0 if self.mic_names else None
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
        self.MODELS_DIR = USER_MODELS_DIR  # Always use the user home dir
        self.selected_lang = 'EN'  # Default to English
        self.model_path = self.get_model_path(self.selected_lang)
        self.model = Model(self.model_path)

    def set_language(self, lang_code):
        if lang_code not in self.LANG_MODELS:
            print(f"Language {lang_code} not supported.")
            return
        was_listening = self.is_listening
        if was_listening:
            self.toggle_listening()  # Stop
        self.selected_lang = lang_code
        self.model_path = self.get_model_path(self.selected_lang)
        self.model = Model(self.model_path)
        print(f"Switched to language: {lang_code}")
        self.tts_engine.say(f"Language changed to {lang_code}")
        self.tts_engine.runAndWait()
        if was_listening:
            self.toggle_listening()  # Restart

    def get_model_path(self, lang_code):
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
            self.stop_event.clear()
            if self.indicator:
                self.indicator.show()
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
                self.indicator.hide()

    def set_mic_index(self, idx):
        was_listening = self.is_listening
        if was_listening:
            self.toggle_listening()  # Stop
        self.selected_mic_index = idx if idx >= 0 else None
        if was_listening:
            self.toggle_listening()  # Restart

    def recognize_speech(self):
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
                        pyperclip.copy(text + " ")
                        pyautogui.hotkey('ctrl', 'v')
        except Exception as e:
            print(f"Error with Vosk recognition: {e}")
        finally:
            try:
                stream.stop_stream()
                stream.close()
            except Exception:
                pass
            p.terminate()

    def cleanup(self):
        print("Cleaning up...")
        self.stop_event.set()
        if self.recognition_thread and self.recognition_thread.is_alive():
            self.recognition_thread.join(timeout=2)
        print("Instant Typer stopped.")

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
    icon.title = "Instant Typer"
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
