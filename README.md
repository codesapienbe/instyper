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

### 🧪 Testing the Installer as an End-User

When you want to test the installation just like a real end-user, here's what you need to know:

### 📁 Default Install Locations
- **Windows:** `C:\Program Files\instyper` (or a custom folder you choose during install)
- **macOS:** `/Applications/instyper`
- **Linux:** `/opt/instyper`

### 🧑‍💻 How to Test
1. **Close your development environment** and any running Instyper apps.
2. **Run the installer** for your platform (see the Packaging section above).
3. **Accept the default install path** (recommended for a real-world test), or choose a custom directory (e.g., `C:\Users\YourUser\instyper-test` on Windows) if you want to test alternate locations.
4. **After installation:**
   - Check that the app runs from the Start Menu, desktop shortcut, or `/Applications`/`/opt` as appropriate.
   - Verify that the README and any other files are present in the install directory.
   - Try uninstalling to make sure the uninstaller works and cleans up files.

### 🚫 Where NOT to Test
- Don't use your project root, build, or `dist` directories for end-user testing.
- Always use a directory outside your development workspace to avoid conflicts.

### 🧰 Advanced: Sandboxed/Virtual Testing
- For extra safety, test in a virtual machine or a new user account to simulate a fresh user environment.

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
