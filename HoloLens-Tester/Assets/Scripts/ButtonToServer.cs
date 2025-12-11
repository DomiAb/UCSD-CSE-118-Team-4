using UnityEngine;

public class ButtonToServer : MonoBehaviour
{
    public HoloLensSpeechSender sender;
    public int selectionIndex = 1;   // 1, 2, or 3

    public void SendSelection()
    {
<<<<<<< HEAD
        string json = "{\"type\": \"select\", \"data\": " + selectionIndex + "}";
=======
        string json = "{\"selection\":" + selectionIndex + "}";
>>>>>>> af50c24ea916df472e2ec492e2770af438c6d03c
        sender.SendRawMessage(json);
    }
}
