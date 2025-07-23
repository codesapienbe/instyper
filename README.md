# 🚀 Instyper: Instant Voice Typer

Instyper is a free, open source, cross-platform desktop toolbar application that lets you type with your voice instantly.

## Key Benefits

- Open source & free forever
- Cross-platform: Windows, macOS, Linux
- Simple, no developer setup required
- Offline support with Vosk
- Online models like Whisper & SpeechBrain
- Non-blocking backend switching for seamless performance
- Real-time multilingual translation: speak in one language and instantly have text typed in another

## Installation

1. Download the installer for your OS:
   - Windows: [instyper-win.exe](https://github.com/codesapienbe/instyper/releases/download/v0.0.1/instyper-win.exe)
   - macOS: [instyper-macos](https://github.com/codesapienbe/instyper/releases/download/v0.0.1/instyper-macos)
   - Linux: [instyper-linux](https://github.com/codesapienbe/instyper/releases/download/v0.0.1/instyper-linux)
2. Run the installer.
3. Launch Instyper from your system tray or toolbar.
4. Start speaking to type text instantly!

## Getting Help

- Visit the [Releases](https://github.com/codesapienbe/instyper/releases) page for the latest version and troubleshooting.
- Open an issue if you need support or have feedback.

## Auto-Translation Mode

Instyper now includes an auto-translation mode: after you speak in your configured input language, your speech is recognized, translated into your configured output language, and typed in real time.

Configure via the system tray Settings menu:
- **Set Input Language**: the language you speak into the microphone (e.g., 'tr' for Turkish).
- **Set Output Language**: the language to translate typed text into (e.g., 'en' for English).

With both languages set, simply speak as usual and Instyper will translate and type instantly.

## License

[MIT License](LICENSE)

---

## 🛠️ API & Worker Architecture (v1+)

Instyper now uses a secure, scalable **API + Celery Worker** architecture for all business and utility functions.

### Key Features
- **All business logic is exposed via FastAPI WebSocket endpoints**
- **Heavy/background work is offloaded to Celery workers** (model download, config, speech log, token management, etc.)
- **Real-time progress updates** for all long-running tasks
- **JWT authentication required for all endpoints**
- **Structured audit logging** (user, IP, correlation ID, etc.)
- **Rate limiting, input validation, and CORS/origin restrictions**
- **Consistent, extensible pattern for all new features**

### API Usage Overview

- **All endpoints are WebSocket-based** (for real-time, bidirectional communication)
- **All requests require a valid JWT** (see below)
- **All heavy/side-effecting actions return a `task_id`**; subscribe to `/ws/task_progress` for real-time updates

#### Example: Model Download
1. **Trigger a model download:**
   - Connect to `/ws/celery_download_model` (WebSocket)
   - Send: `{ "backend": "whisper", "model_info": {...}, "models_dir": "/path/to/models" }`
   - Receive: `{ "task_id": "..." }`
2. **Subscribe to progress:**
   - Connect to `/ws/task_progress` (WebSocket)
   - Send: `{ "task_id": "..." }`
   - Receive progress updates: `{ "task_id": "...", "status": "PROGRESS", "progress": 0 }`, `{ ... progress: 50 }`, `{ ... progress: 100, "result": { ... } }`

#### Example: Utility Function (Human Size)
1. **Request human-readable size:**
   - Connect to `/ws/human_size`
   - Send: `{ "nbytes": 1048576 }`
   - Receive: `{ "task_id": "..." }`
2. **Subscribe to progress:**
   - Connect to `/ws/task_progress`
   - Send: `{ "task_id": "..." }`
   - Receive: `{ "task_id": "...", "status": "PROGRESS", "progress": 100, "result": { "human_size": "1.0 MB" } }`

### Endpoint Summary Table

| Endpoint                        | Purpose                                 | Input Example / Notes                |
|----------------------------------|-----------------------------------------|--------------------------------------|
| `/ws/celery_download_model`      | Download model (async)                  | `{ backend, model_info, models_dir }`|
| `/ws/celery_change_config`       | Change config (async)                   | `{ key, value }`                     |
| `/ws/celery_set_backend`         | Set backend (async)                     | `{ backend_name }`                   |
| `/ws/celery_set_model`           | Set model (async)                       | `{ model_name }`                     |
| `/ws/celery_load_config`         | Load config (async)                     | `{}`                                 |
| `/ws/celery_save_config`         | Save config (async)                     | `{ config_data }`                    |
| `/ws/celery_reset_config`        | Reset config (async)                    | `{}`                                 |
| `/ws/celery_load_speech_model`   | Load speech model (async)               | `{ backend, model_name, models_dir }`|
| `/ws/append_encrypted_speech_log`| Append to encrypted speech log (async)  | `{ text, pincode }`                  |
| `/ws/decrypt_speech_log`         | Decrypt speech log (async)              | `{ pincode }`                        |
| `/ws/get_hf_token_from_env`      | Get HuggingFace token (async)           | `{}`                                 |
| `/ws/save_hf_token_to_env`       | Save HuggingFace token (async)          | `{ token }`                          |
| `/ws/huggingface_login`          | HuggingFace login (async)               | `{ token }`                          |
| `/ws/human_size`                 | Human-readable size (async)             | `{ nbytes }`                         |
| `/ws/show_notification`          | Log notification (async)                | `{ title, message, level }`          |
| `/ws/is_useless_whisper_output`  | Whisper output filter (async)           | `{ text }`                           |
| `/ws/find_ckpts`                 | Find .ckpt files in object (async)      | `{ obj }`                            |
| `/ws/task_progress`              | Subscribe to task progress              | `{ task_id }`                        |

> **All endpoints require JWT authentication and return a `task_id` for progress tracking.**

### Security & Observability
- **JWT authentication**: All endpoints require a valid JWT in the `Authorization` header.
- **Rate limiting**: Per-user, per-endpoint rate limits are enforced.
- **Input validation**: All requests are validated using Pydantic models.
- **CORS/origin restrictions**: Only allowed origins can connect.
- **Audit logging**: All actions are logged with user_id, IP, correlation ID, and sanitized inputs.

### Extending the API
- To add a new business or utility function:
  1. Implement a Celery task in `instyper_worker` (with progress, logging, and secure args)
  2. Add a WebSocket endpoint in the API that enqueues the task and returns `task_id`
  3. Use `/ws/task_progress` for real-time updates

---

For more details, see the code in `src/instyper_api/` and `src/instyper_worker/`.

---
