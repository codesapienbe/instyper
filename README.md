# 🚀 Instyper — Instant Voice Typing (end‑user guide)

Instyper is a lightweight, privacy-first desktop application that turns your voice into text instantly. It works offline (Vosk) and supports modern online models (Whisper) and live translation — all with a simple installer and a friendly GUI.

- Fast to install, easy to run
- Offline-first: use Vosk for on-device recognition
- Switch to Whisper for higher-quality models (optional)
- Built-in real-time translation and encrypted speech logs for privacy

----

## Quick start

1) Install from PyPI (recommended):

   - `python -m pip install instyper`
   - After installation run the platform installer to create a launcher: `instyper install` (or `python -m instyper install`)

2) Run without installing (try immediately):

   - `python -m instyper`

3) From source (developer/local):

   - Clone the repo and inside the project folder:
     - `python -m venv .venv && source .venv/bin/activate` (macOS / Linux)
     - `python -m venv .venv; .\.venv\Scripts\Activate.ps1` (Windows PowerShell)
     - `python -m pip install --user .`
     - `python -m instyper install` (to create desktop shortcuts)

----

## Highlights


1) **Instant typing (offline) with Vosk**

   - Use case: low-latency, private speech→text without internet.
   - How: In the app Settings choose **Vosk** as the recognition backend, select a small local model (installer downloads recommended small models), then press the microphone button — your speech is typed immediately.
   - Why: Works completely offline and keeps audio & transcripts on your machine.

2) **Switch to Whisper (higher accuracy)**

   - Use case: improved accuracy, multi-language support and better handling of complex audio.
   - How: Open Settings → Backend → select **Whisper** and choose a model. Whisper models may be larger; the installer can download them for you. For faster performance, install with GPU support (when available).
   - Why: Whisper provides higher recognition quality for many languages and noisy environments.

3) **Instant typing + real-time translation**

   - Use case: speak in one language and instantly have the translated text typed in another language.
   - How: Enable **Auto‑Translation** in Settings, choose your Input and Output languages. Speak normally; the app recognizes, translates, and types in real time.
   - Why: Great for multilingual workflows, live captions, and cross-language communication.

4) **Encrypted speech logs for privacy and auditability**

   - Use case: keep a secure, auditable record of transcripts while protecting user privacy.
   - How: Enable **Encrypted logs** in Settings (logs are stored locally and encrypted). You control where logs are saved and when to share them.
   - Why: Useful for research, debugging, or compliance while minimizing risk to sensitive data.

----

## Why choose Instyper?

- Privacy-first: offline recognition and local encrypted logs.
- Flexible: switch backends and models from the GUI.
- Easy: one-line install and a friendly installer to set up shortcuts and models.
- Modern: real-time translation, solid desktop integration and structured logs for troubleshooting.

----

## Help

- Releases, issues and documentation: `https://github.com/codesapienbe/instyper`
- If you need support or want to report installation problems, attach `application.log` from your Instyper folder when opening an issue.

## License

MIT License
