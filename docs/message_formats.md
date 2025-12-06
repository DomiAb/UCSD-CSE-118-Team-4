# Message formats
This document describes how the messages sent between the Jetson and the HoloLens should look. It defines the message format.  
All messages are sent via a websocket connection in json format.

### Errors
```
{
  "type": "error", 
  "message": "<details>"
}
```
## Messages FROM HoloLens TO Jetson
### Start Conversation
```
{
  "type": "start_conversation"
}
```

### Stop Conversation
```
{
  "type": "stop_conversation"
}
```

### Send an image
```
{
  "image_data": "<base64_image_data>"
}
```

### Select an option
The selected option (as an index) is sent to the Jetson, so that it can read out the corresponding response afterwards.
```
{
  "type": "select", 
  "data": <1-based index>
}
```


## Messages FROM Jetson TO HoloLens
### Receive Options
```
{
  "type": "options", 
  "data": [
    "<opt1>", 
    "<opt2>", 
    "<opt3>"
  ]
}
```
