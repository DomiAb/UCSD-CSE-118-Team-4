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
Notes:
- audio_data and image_data are both optional.  
- At least one of audio_data or image_data must be provided.
```

### /select-input (POST) Endpoint
The selected option (as an index) is sent to the Jetson, so that it can read out the corresponding response afterwards.
```
{
  "selection": 1 | 2 | 3
}
```


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
**Response:** No response body. The server should return HTTP status code `204 No Content`.
