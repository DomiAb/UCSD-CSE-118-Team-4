# Message formats
This document describes how the messages sent between the Jetson and the HoloLens should look. It defines the message format.  
All messages are sent as data via a HTTP connection in json format.

## Messages FROM HoloLens TO Jetson
### /suggest (POST) Endpoint 
As the HoloLens has the built-in feature of converting an audio recording to spoken text, this task is left to the HoloLens. Therefore, not the audio recording, but the spoken text is sent to the Jetson.
```
{
  "audio_data": "The spoken text. So, the data is here.",   (Optional)
  "image_data": "The taken photo. So, the data is here."    (Optional, either of one must be provided)
}
```

### /select-input (POST) Endpoint
The selected option (as an index) is sent to the Jetson, so, that it can read out the corresponding response afterwards.
```
{
  "selection": 1/2/3
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

### /select-input (POST) Endpoint
No information needs to be send to the HoloLens. Therefore no data will be transmitted.
```
{
}
```
