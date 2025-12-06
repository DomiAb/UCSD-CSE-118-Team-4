using UnityEngine;

public class ButtonToServer : MonoBehaviour
{
    public HoloLensSpeechSender sender;
    public int selectionIndex = 1;   // 1, 2, or 3

    public void SendSelection()
    {
        string json = "{\"selection\":" + selectionIndex + "}";
        sender.SendRawMessage(json);
    }
}
