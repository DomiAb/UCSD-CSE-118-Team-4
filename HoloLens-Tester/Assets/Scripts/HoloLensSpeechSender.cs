using UnityEngine;
using NativeWebSocket;
using TMPro;
using System.Text;
using System.Threading.Tasks;

public class HoloLensSpeechSender : MonoBehaviour
{
    public TextMeshProUGUI button1Label;
    public TextMeshProUGUI button2Label;
    public TextMeshProUGUI button3Label;

    private WebSocket ws;
    private bool keepConnecting = true;

    // -------------------------
    // STARTUP
    // -------------------------
    private void Start()
    {
        ws = new WebSocket("ws://192.168.0.166:8765");

        ws.OnMessage += bytes =>
        {
            string msg = Encoding.UTF8.GetString(bytes);

            try
            {
                OptionsMessage opt = JsonUtility.FromJson<OptionsMessage>(msg);
                if (opt != null && opt.type == "options" && opt.data?.Length >= 3)
                {
                    UnityMainThreadDispatcher.Instance().Enqueue(() =>
                    {
                        button1Label.text = opt.data[0];
                        button2Label.text = opt.data[1];
                        button3Label.text = opt.data[2];
                    });
                }
            }
            catch { /* ignore parse errors */ }
        };

        _ = ConnectWebSocket();
    }

    private async Task ConnectWebSocket()
    {
        // avoid overlapping loops
        if (ws == null) return;

        while (keepConnecting && ws.State != WebSocketState.Open)
        {
            try
            {
                Debug.Log("WS: attempting connect…");
                await ws.Connect();

                // if we get here and state is Open, break out
                if (ws.State == WebSocketState.Open)
                {
                    Debug.Log("WS: connected.");
                    break;
                }
            }
            catch (System.Exception ex)
            {
                Debug.Log("WS connect exception: " + ex.Message);
            }

            // small delay before trying again
            await Task.Delay(1000); // 1 second
        }
    }

    private void Update()
    {
#if !UNITY_WEBGL || UNITY_EDITOR
        ws?.DispatchMessageQueue();
#endif
    }

    // -------------------------
    // SENDERS
    // -------------------------
    public async void SendStartConversation()
    {
        if (ws.State == WebSocketState.Open)
            await ws.SendText("{\"type\":\"start_conversation\"}");
    }

    public async void SendStopConversation()
    {
        if (ws.State == WebSocketState.Open)
            await ws.SendText("{\"type\":\"stop_conversation\"}");
    }

    public async void SendRawMessage(string json)
    {
        if (ws != null && ws.State == WebSocketState.Open)
            await ws.SendText(json);
    }


    private async void OnApplicationQuit()
    {
        if (ws != null)
            await ws.Close();
    }
}

[System.Serializable]
public class OptionsMessage
{
    public string type;
    public string[] data;
}
