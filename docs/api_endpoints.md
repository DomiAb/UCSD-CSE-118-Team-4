# API Endpoints

This document summarizes the available HTTP and WebSocket endpoints in this codebase, including request/response formats and notes on usage.

## FastAPI HTTP Server (backend/main.py)
Run with: `uvicorn backend.main:app --host 0.0.0.0 --port 8765`

### GET /health
- **Purpose:** Liveness check.
- **Response:** `{"status": "ok"}`

### POST /suggest
- **Purpose:** Generate a single LLM reply and store it as the current option.
- **Request JSON (one of these fields for text):**
  - `data` | `heard` | `transcript`: string (required)
  - `context`: string (optional)
  - `goal`: string (optional)
- **Responses:**
  - `200 OK`: `{"options": ["<reply>"]}`
  - `400 Bad Request` if no text is provided.
  - `500 Internal Server Error` on LLM failure.
- **Notes:** Internally stores the reply in `options` for `/select-input`.

### POST /select-input
- **Purpose:** Return a stored option by index (1-based).
- **Request JSON:** `{"data": "<index_as_string>"}` (e.g., `"1"`)
- **Responses:**
  - `200 OK`: `{"selected": "<option_text>"}`
  - `400 Bad Request` for invalid index.
- **Notes:** Does not perform TTS; intended for the client (e.g., HoloLens) to handle playback.

### POST /llm-suggest
- **Purpose:** Generate a single LLM reply without storing options.
- **Request JSON:**
  - `heard` | `transcript`: string (required)
  - `context`: string (optional, default `"friendly encounter"`)
  - `goal`: string (optional, default `"be concise and friendly"`)
- **Responses:**
  - `200 OK`: `{"reply": "<text>", "context": "<context>", "goal": "<goal>"}`  
  - `400 Bad Request` if text is missing.
  - `500 Internal Server Error` on LLM failure.

## WebSocket Server (jetson/server/main.py)
Run with: `python -m jetson.server.main` (listens on `ws://0.0.0.0:8765`)

### Incoming messages (from HoloLens/client)
- JSON with either or both of:
  - `audio_data`: string (speech-to-text from HoloLens)
  - `image_data`: base64 string (optional image context)
- If neither is provided, the server logs a warning and ignores the message.
- Requires `GEMINI_API_KEY` to be set; uses Gemini to generate three options.
- Selection messages:
  - `{"type": "select", "data": <1-based index>}` (or `selection` instead of `data`) to pick one of the three options.
- Conversation control:
  - `{"type": "start_conversation"}` (or plain string "start conversation") starts a session and resets history.
  - `{"type": "stop_conversation"}` (or plain string "stop conversation") ends the session, clears options, and returns a conversation highlight with timestamps.

### Outgoing messages (to HoloLens/client)
- On success (after audio/image input): `{"type": "options", "data": ["opt1", "opt2", "opt3"]}`  
  The server stores these per connection.
- On selection: `{"type": "selected", "data": "<chosen_text>"}`  
  The server speaks the selected text via `pyttsx3` (`speak`) on the Jetson’s default speaker.
- On selection error: `{"type": "error", "message": "Invalid selection"}`
- On conversation start: `{"type": "conversation_started"}`
- On conversation stop: `{"type": "conversation_highlight", "data": "<highlight_text>"}` followed by `{"type": "conversation_stopped"}`. Highlights are also appended to `conversation_highlights.log` with start/stop timestamps.
- Highlights/log context:
  - Recent highlights are loaded from `user_context/conversation_highlights.log` and seeded into new conversations.
  - Schedule context is loaded from `user_context/events.ics` (ICS calendar) and included in prompts (current event, recent past, and upcoming).

## Notes on Models/Backends
- FastAPI server can use Hugging Face (torch) or `llama-cpp` backends via environment variables (e.g., `LLM_BACKEND`, `LLAMA_CPP_MODEL_PATH`).
- WebSocket server uses Gemini (`GEMINI_API_KEY`) via `jetson/context/llm_interface.py`.
