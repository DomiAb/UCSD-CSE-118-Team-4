# Message formats
This document describes, how the messages sent between the Jetson and the HoloLens should look like. It defines the message format.  
All messages are sent as data via an tcp connection in json format.

# Messages FROM Jetson TO HoloLens
### Start Microphone Recording
```
{
  "type": "start_microphone"
}
```

### End Microphone Recording
```
{
  "type": "stop_microphone"
}
```


# Messages FROM HoloLens TO Jetson
### Microphone recording
As the HoloLens has the built in feature of converting an audio recording to the spoken text, this task is left at the HoloLens. Therfore, not the audio recording, but the spoken text is sent to the Jetson.
```
{
  "type": "audio_data",
  "data": "The spoken text. So, the data is here."
}
```
