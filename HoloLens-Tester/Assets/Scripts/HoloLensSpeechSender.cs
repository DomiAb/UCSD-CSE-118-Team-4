using NativeWebSocket;
using System.Text;
using TMPro;
using Unity.VisualScripting.Antlr3.Runtime.Misc;
using UnityEngine;
using UnityEngine.Windows.Speech;

public class HoloLensSpeechSender : MonoBehaviour
{
    public TextMeshProUGUI debugLabel;
    public TextMeshProUGUI button1Label;
    public TextMeshProUGUI button2Label;
    public TextMeshProUGUI button3Label;

    private DictationRecognizer dictation;
    private WebSocket ws;
    private string lastPartial = "";
    private float silenceTimer = 0f;
    private bool heardSomething = false;

    async void Start()
    {
        Log("Starting…");

        // ---- SETUP WEBSOCKET ----
        ws = new WebSocket("ws://192.168.0.197:8765");

        ws.OnOpen += async () =>
        {
            Log("WS CONNECTED!");

            // TEST MESSAGE
            string testJson = "{\"audio_data\":\"Hello from HoloLens\"}";
            await ws.SendText(testJson);
            Log("Sent TEST message");
        };

        ws.OnError += e => Log("WS ERROR: " + e);
        ws.OnClose += e => Log("WS CLOSED: " + e);

        ws.OnMessage += bytes =>
        {
            string msg = Encoding.UTF8.GetString(bytes);
            Log("SERVER ? " + msg);

            // Try parsing "options" message
            try
            {
                OptionsMessage opt = JsonUtility.FromJson<OptionsMessage>(msg);

                if (opt.type == "options" && opt.data != null && opt.data.Length >= 3)
                {
                    // Update buttons on main thread
                    UnityMainThreadDispatcher.Instance().Enqueue(() =>
                    {
                        button1Label.text = opt.data[0];
                        button2Label.text = opt.data[1];
                        button3Label.text = opt.data[2];
                    });
                }
            }
            catch
            {
                Log("JSON parse failed");
            }
        };


        try
        {
            await ws.Connect();
            Log("Connect() returned");
        }
        catch (System.Exception ex)
        {
            Log("CONNECT EXCEPTION: " + ex.Message);
        }

        // ---- DICTATION SETUP ----
        dictation = new DictationRecognizer();

        dictation.DictationResult += OnResult;
        dictation.DictationHypothesis += OnPartial;
        dictation.DictationError += (error, hresult) => Log("Dictation Error: " + error);

        dictation.Start();
        Log("Dictation Started");

    }

    void OnPartial(string text)
    {
        heardSomething = true;
        lastPartial = text;
        silenceTimer = 0f;

        Log("Heard (partial): " + text);
    }
    private void OnResult(string text, ConfidenceLevel confidence)
    {
        Log("FINAL: " + text);

        string json = "{\"audio_data\":\"" + text + "\"}";
        Send(json);

        lastPartial = "";
        silenceTimer = 0f;

        dictation.Stop();
        dictation.Start();
    }

    async void Update()
    {
#if !UNITY_WEBGL || UNITY_EDITOR
        ws?.DispatchMessageQueue();
#endif

        if (heardSomething)
        {
            silenceTimer += Time.deltaTime;

            if (silenceTimer >= 1.2f)
            {
                heardSomething = false;

                if (!string.IsNullOrEmpty(lastPartial))
                {
                    string json = "{\"audio_data\":\"" + lastPartial + "\"}";
                    Log("Sending final: " + lastPartial);
                    await Send(json);
                }

                lastPartial = "";
                dictation.Stop();
                dictation.Start();
            }
        }
    }

    private async System.Threading.Tasks.Task Send(string msg)
    {
        if (ws.State == WebSocketState.Open)
        {
            await ws.SendText(msg);
            Log("Sent: " + msg);
        }
        else
        {
            Log("Send FAILED — WebSocket not open");
        }
    }

    private void Log(string s)
    {
        Debug.Log(s);
        if (debugLabel != null)
            debugLabel.text = s;
    }

    private async void OnApplicationQuit()
    {
        dictation?.Stop();
        dictation?.Dispose();

        if (ws != null)
            await ws.Close();
    }
    public async void SendRawMessage(string json)
    {
        if (ws != null && ws.State == WebSocketState.Open)
        {
            await ws.SendText(json);
            Log("Sent JSON: " + json);
        }
        else
        {
            Log("WS not open — cannot send JSON");
        }
    }

}

[System.Serializable]
public class OptionsMessage
{
    public string type;
    public string[] data;
}
