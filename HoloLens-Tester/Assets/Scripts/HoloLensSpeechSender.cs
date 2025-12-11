<<<<<<< HEAD
ï»¿using UnityEngine;
using NativeWebSocket;
using TMPro;
using System.Text;
using System.Threading.Tasks;

public class HoloLensSpeechSender : MonoBehaviour
{
=======
using NativeWebSocket;
using System.Text;
using TMPro;
using Unity.VisualScripting.Antlr3.Runtime.Misc;
using UnityEngine;
using UnityEngine.Windows.Speech;

public class HoloLensSpeechSender : MonoBehaviour
{
    public TextMeshProUGUI debugLabel;
>>>>>>> af50c24ea916df472e2ec492e2770af438c6d03c
    public TextMeshProUGUI button1Label;
    public TextMeshProUGUI button2Label;
    public TextMeshProUGUI button3Label;

<<<<<<< HEAD
    private WebSocket ws;
    private bool keepConnecting = true;

    // -------------------------
    // STARTUP
    // -------------------------
    private void Start()
    {
        ws = new WebSocket("ws://192.168.0.166:8765");
=======
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
>>>>>>> af50c24ea916df472e2ec492e2770af438c6d03c

        ws.OnMessage += bytes =>
        {
            string msg = Encoding.UTF8.GetString(bytes);
<<<<<<< HEAD

            try
            {
                OptionsMessage opt = JsonUtility.FromJson<OptionsMessage>(msg);
                if (opt != null && opt.type == "options" && opt.data?.Length >= 3)
                {
=======
            Log("SERVER ? " + msg);

            // Try parsing "options" message
            try
            {
                OptionsMessage opt = JsonUtility.FromJson<OptionsMessage>(msg);

                if (opt.type == "options" && opt.data != null && opt.data.Length >= 3)
                {
                    // Update buttons on main thread
>>>>>>> af50c24ea916df472e2ec492e2770af438c6d03c
                    UnityMainThreadDispatcher.Instance().Enqueue(() =>
                    {
                        button1Label.text = opt.data[0];
                        button2Label.text = opt.data[1];
                        button3Label.text = opt.data[2];
                    });
                }
            }
<<<<<<< HEAD
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
                Debug.Log("WS: attempting connectâ€¦");
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
=======
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
>>>>>>> af50c24ea916df472e2ec492e2770af438c6d03c
    {
#if !UNITY_WEBGL || UNITY_EDITOR
        ws?.DispatchMessageQueue();
#endif
<<<<<<< HEAD
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
=======

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

>>>>>>> af50c24ea916df472e2ec492e2770af438c6d03c
}

[System.Serializable]
public class OptionsMessage
{
    public string type;
    public string[] data;
}
