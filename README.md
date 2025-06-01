# 🚀 Instyper: Instant Voice Typer

Instyper is a cross-platform voice typing taskbar application.

---

## ⚠️ Prerequisites & Setup

**Automated installation via Makefile is no longer supported.**

To ensure transparency and user control, you must manually install all prerequisites and dependencies. This avoids any background installation of system tools or libraries without your explicit approval.

### 1. Python 3.10 (Required)

- Instyper requires **Python 3.10** (not 3.11+ or 3.9-).
- [Download Python 3.10](https://www.python.org/downloads/release/python-3100/)
- Ensure `python` or `python3` in your terminal points to Python 3.10.

### 2. Install `uv` (Python package/dependency manager)

- `uv` is a fast, modern Python package manager (like pip, but faster).
- Install it globally:

  ```sh
  # On all platforms (if you have pip):
  pip install uv
  # Or, if you have Python 3.10 as python3:
  python3 -m pip install uv
  ```

- [uv documentation](https://github.com/astral-sh/uv)

### 3. System Dependencies

#### Windows

- **Visual C++ Build Tools**: Required for building some Python packages.
  - Download and install from [Microsoft Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- **FFmpeg**: Required for audio processing.
  - Download from [FFmpeg.org](https://ffmpeg.org/download.html) and add to your PATH.

#### macOS

- **Homebrew** (recommended): [Install Homebrew](https://brew.sh/)
- **FFmpeg**:

  ```sh
  brew install ffmpeg
  ```

#### Linux (Debian/Ubuntu)

- **Build tools & FFmpeg**:

  ```sh
  sudo apt-get update
  sudo apt-get install -y build-essential ffmpeg
  ```

### 4. Python Dependencies

- All Python dependencies are listed in `pyproject.toml`.
- Install them using `uv`:

  ```sh
  uv pip install --prerelease=allow -r pyproject.toml
  ```

- For OpenAI Whisper (if needed):

  ```sh
  uv pip install --prerelease=allow --upgrade git+https://github.com/openai/whisper.git
  ```

---

## License

[MIT](LICENSE)

---

## 📦 How Instyper Stores Stuff

- 🏠 **All your models and settings live in one place:** `~/.instyper` (in your home folder)
- 🗂️ **Models are always loaded from:** `~/.instyper/models`
- 📄 **A copy of this README is saved in:** `~/.instyper/README.md`
- 🛠️ **First time you run Instyper:** If `~/.instyper/models` is empty and there's a `models/` folder in the app, all models are copied over for you
- 🌍 **Add or remove languages anytime:** Just put new models in `~/.instyper/models`

---

## 👩‍💻 For Everyone Using Instyper

### 🖥️ Get Started in 3 Steps

1. **Download** the right version for your computer:
   - Windows: [instyper-win.exe](https://github.com/codesapienbe/instyper/releases/download/v0.0.1/instyper-win.exe) (Just double-click!)
   - macOS: [instyper-macos](https://github.com/codesapienbe/instyper/releases/download/v0.0.1/instyper-macos) (Not available yet)
   - Linux: [instyper-linux](https://github.com/codesapienbe/instyper/releases/download/v0.0.1/instyper-linux) (Not available yet)

2. **First Run Magic** ✨  
   Instyper automatically:
   - Creates a personal configuration folder in your home directory (`~/.instyper`)
   - Sets up basic English voice typing
   - Remembers your preferences between sessions

3. **Add Languages** (Optional)  
   Want to type in French, Dutch, or other languages?
   1. Get models from [Vosk Models](https://alphacephei.com/vosk/models)
   2. Unzip into `~/instyper/models` (we'll create this automatically)
   3. Restart Instyper - new languages appear like magic!

### ⚡ New: Non-Blocking Model & Backend Switching

Instyper now supports **asynchronous, non-blocking switching** of speech models and backends!

- When you change the speech recognition model or backend (for example, switching from Vosk to Whisper, or changing the language/model), Instyper loads the new model in the background.
- **The app and its menus stay fully responsive**—no more freezing or waiting!
- You'll see a loading indicator while the new model is being prepared, and a notification when it's ready.
- If you were already using voice typing, it will automatically resume with the new model as soon as loading is complete.

This makes it much faster and smoother to experiment with different models or languages, even with large models that take a while to load.

### 🔔 Notifications & Feedback

- Instyper uses a subtle status indicator near your mouse cursor for most feedback (like loading, listening, or typing).
- OS native notifications are only shown for important events, such as errors or when a long-running operation completes.
- This keeps your workflow smooth and distraction-free!

### ⚙️ Where Everything Lives  

All your personal settings and languages are kept in:  
`~/instyper/`  

- 🔒 Safe from app updates
- 🗑️ Delete anytime to start fresh
- 🔄 Add/remove models while Instyper is closed

### 🚀 Need Help?  

Visit our [Releases Page](https://github.com/codesapienbe/instyper/releases) for the latest version and troubleshooting tips!

---

## 🧠 How Instyper Listens to You (The Science-y Part!)

When you talk, Instyper (using Vosk and Kaldi) does some smart stuff to understand you:

- 🎵 **Turns your voice into numbers:** It uses something called MFCCs (Mel-Frequency Cepstral Coefficients) or Filter Banks. These are like special fingerprints for sounds!
- 🎚️ **Makes all audio the same:** Everything is changed to 16kHz mono (one channel) so it's super clear and easy for the computer to understand.
- 🦾 **Why do this?**
  - ✅ **Consistency:** Makes sure all voices are treated the same
  - 🔄 **Compatibility:** Works with lots of different microphones and files
  - 🚀 **Optimization:** 16kHz mono is perfect for speech
  - 🎧 **Quality:** Keeps your words clear and avoids weird sound problems

So, no matter what mic or file you use, Instyper always hears you in the best way for accurate typing! 🏆

---

## 🛠️ Troubleshooting

- ❓ **Missing a language?** Make sure its model folder is in `~/.instyper/models`
- ⚠️ **Error about missing models?** Download and unzip the model into `~/.instyper/models`
- 🆘 **Other problems?** See below or ask for help!

---

## 💻 System Requirements

- Windows 10 or later
- macOS 10.13 or later
- Linux (most modern distros)
- At least 100MB free space
- 4GB RAM recommended

---

## 🆘 Support

If you need help:

1. Check the troubleshooting section above
2. Open an issue in the project repo
3. Contact the dev team

---

✨ Happy voice typing! ✨
