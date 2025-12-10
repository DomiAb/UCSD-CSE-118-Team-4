# Message formats
This document describes how the messages sent between the Jetson and the HoloLens should look. It defines the message format.  
All messages are sent as data via a HTTP connection in json format.

## Messages FROM HoloLens TO Jetson
### /suggest (POST) Endpoint
As the HoloLens has the built-in feature of converting an audio recording to spoken text, this task is left to the HoloLens. Therefore, not the audio recording, but the spoken text is sent to the Jetson.
```
{
  "audio_data": "<spoken_text>",
  "image_data": "<base64_image_data>"
}
```
```
Notes:
- audio_data and image_data are both optional.  
- At least one of audio_data or image_data must be provided.
- image_data should be a base64-encoded string representing the image.
```

### /select-input (POST) Endpoint
The selected option (as an index) is sent to the Jetson, so that it can read out the corresponding response afterwards.
```
{
  "selection": 1
}
```

### WebSocket Messages (Conversation control + turn handling)
- Start a conversation/session  
  `{"type": "start_conversation"}` (or plain string "start conversation")

- Trigger Pi to send audio (e.g., stop listening & send request)  
  `{"type": "send_audio"}` (broadcasts `send_audio` event to connected clients)

- Send speech/image for options (must be inside a started conversation)  
  `{"audio_data": "<spoken_text>", "image_data": "<optional_base64_image>"}`

- Receive options (3 options)  
  `{"type": "options", "data": ["opt1", "opt2", "opt3"]}`

- Select an option (1-based)  
  `{"type": "select", "data": 1}` (or `selection`)

- Stop a conversation/session (returns highlight/history)  
  `{"type": "stop_conversation"}` (or plain string "stop conversation")


## Messages FROM Jetson TO HoloLens
### Answer from /suggest (POST) Endpoint
```
{
  "responses": [
    "Response 1",
    "Response 2",
    "Response 3"
  ]
}
```

### Answer from /select-input (POST) Endpoint
No information needs to be sent to the HoloLens. Therefore there will be no response body.  
The server should return HTTP status code `204 No Content`.

### WebSocket Responses
- On conversation start: `{"type": "conversation_started"}`
- On options ready: `{"type": "options", "data": ["opt1", "opt2", "opt3"]}`
- On selection: `{"type": "selected", "data": "<chosen_text>"}`
- On errors: `{"type": "error", "message": "<details>"}`
- On stop: `{"type": "conversation_highlight", "data": [...]}` then `{"type": "conversation_stopped"}`
