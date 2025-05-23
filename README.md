# 🚀 Instyper: Instant Voice Typer

Instyper lets you type with your voice in many languages, even when you're offline! It's powered by Vosk, a super-smart speech recognition engine. Just install, talk, and watch your words appear like magic! ✨

---

## 📦 How Instyper Stores Stuff

- 🏠 **All your models and settings live in one place:** `~/.instyper` (in your home folder)
- 🗂️ **Models are always loaded from:** `~/.instyper/models`
- 📄 **A copy of this README is saved in:** `~/.instyper/README.md`
- 🛠️ **First time you run Instyper:** If `~/.instyper/models` is empty and there's a `models/` folder in the app, all models are copied over for you
- 🌍 **Add or remove languages anytime:** Just put new models in `~/.instyper/models`

---

## 👩‍💻 For End-Users

### 🖥️ How to Install

Just follow these steps for your computer:

#### 🪟 Windows
1. Download `instyper-windows.exe` from the `dist` folder
2. Put it anywhere you want and double-click to start!

#### 🍏 macOS
1. Download `instyper-darwin` from the `dist` folder
2. Open Terminal and run:
   ```bash
   chmod +x instyper-darwin
   ./instyper-darwin
   ```

#### 🐧 Linux
1. Download `instyper-linux` from the `dist` folder
2. Open Terminal and run:
   ```bash
   chmod +x instyper-linux
   ./instyper-linux
   ```

### 🌐 How to Add or Update Languages
- Download new Vosk models from [Vosk Models](https://alphacephei.com/vosk/models)
- Unzip the model folder into `~/.instyper/models`
- Restart Instyper — your new language will show up in the menu!

### 🗃️ Where is Everything?
- All your stuff is in `~/.instyper` (including this README)
- You can delete or update models in `~/.instyper/models` whenever you want

---

## 🧑‍💻 For Developers

### 🏃‍♂️ Running from Source
1. Clone the repo
2. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Run Instyper:
   ```bash
   python src/instyper/__init__.py
   ```

### 🛠️ Managing Models
- Put new models in `~/.instyper/models`
- On first run, if `~/.instyper/models` is empty, models from the repo's `models/` folder are copied there
- The app **always** loads models from `~/.instyper/models`

### 📦 Packaging
- Models are **not** bundled in the binary (keeps things small and fast!)
- End-users manage their own models in `~/.instyper/models`

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
