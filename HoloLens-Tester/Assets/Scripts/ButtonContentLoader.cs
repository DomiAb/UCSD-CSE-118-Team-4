using UnityEngine;
using TMPro;
using System.Text;
using NativeWebSocket;

public class ButtonContentLoader : MonoBehaviour
{
    public TextMeshProUGUI button1Text;

    private WebSocket ws;
    private string pendingText = null;

    [System.Serializable]
    class OptionsMessage
    {
        public string type;
        public string[] data;
    }

    [System.Serializable]
    class SelectedMessage
    {
        public string type;
        public string data;
    }

    [System.Serializable]
    class ErrorMessage
    {
        public string type;
        public string message;
    }

    async void Start()
    {
        button1Text.text = "Waiting…";

        ws = new WebSocket("ws://192.168.0.210:8765");

        ws.OnOpen += () =>
        {
            Debug.Log("WebSocket Connected!");
            button1Text.text = "Connected!";
        };

        ws.OnMessage += (bytes) =>
        {
            string msg = Encoding.UTF8.GetString(bytes);
            Debug.Log("MESSAGE RECEIVED: " + msg);

            // First check "type" manually
            if (msg.Contains("\"type\":\"options\""))
            {
                var m = JsonUtility.FromJson<OptionsMessage>(msg);

                if (m.data != null && m.data.Length > 0)
                    pendingText = m.data[0];   // Use first option for Button1
            }
            else if (msg.Contains("\"type\":\"selected\""))
            {
                var m = JsonUtility.FromJson<SelectedMessage>(msg);
                pendingText = m.data;         // Show selected text
            }
            else if (msg.Contains("\"type\":\"error\""))
            {
                var m = JsonUtility.FromJson<ErrorMessage>(msg);
                pendingText = "Error: " + m.message;
            }
        };

        ws.OnError += (e) =>
        {
            Debug.LogError("WebSocket Error: " + e);
            button1Text.text = "Error!";
        };

        await ws.Connect();
    }

    void Update()
    {
#if !UNITY_WEBGL || UNITY_EDITOR
        ws?.DispatchMessageQueue();
#endif

        if (pendingText != null)
        {
            button1Text.text = pendingText;
            pendingText = null;
        }
    }

    async void OnApplicationQuit()
    {
        if (ws != null)
            await ws.Close();
    }
}
