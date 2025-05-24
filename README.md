# 🚀 Instyper: Instant Voice Typer

Instyper is a cross-platform voice typing and automation tool.

## Installation (Recommended)

1. Make sure you have Python 3.13+ and [uv](https://github.com/astral-sh/uv) installed:
   ```sh
   pip install uv
   ```
2. Install Instyper directly from the latest GitHub release zip:
   ```sh
   uv pip install https://github.com/<youruser>/<yourrepo>/archive/refs/tags/vX.Y.Z.zip
   ```
   *(Replace `<youruser>`, `<yourrepo>`, and `vX.Y.Z` with the correct values for your repo and release)*

3. After install, you can run Instyper from any console:
   ```sh
   instyper
   ```

- User-specific configuration and models are always stored in `~/.instyper`.
- To update Instyper, just re-run the install command with the new release zip.
- To uninstall, run `uv pip uninstall instyper`.

## Development
- All dependencies are managed in `pyproject.toml`.
- No binary builds or PyInstaller are used.

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
   - macOS: [instyper-macos](https://github.com/codesapienbe/instyper/releases/download/v0.0.1/instyper-macos)
   - Linux: [instyper-linux](https://github.com/codesapienbe/instyper/releases/download/v0.0.1/instyper-linux)

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
