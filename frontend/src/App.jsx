import React, { useEffect, useState } from "react";
import { parseIcs, summarizeSchedule } from "./utils/ics";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8765";
const tabs = ["Status", "Conversation", "Core Info", "Highlights", "Calendar"];

function useWebSocketClient(onContextSnapshot) {
  const [status, setStatus] = useState("disconnected");
  const [messages, setMessages] = useState([]);
  const [options, setOptions] = useState([]);
  const [lastSelected, setLastSelected] = useState(null);
  const [conversationLog, setConversationLog] = useState([]);
  const wsRef = React.useRef(null);

  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;
    ws.onopen = () => {
      setStatus("connected");
      ws.send(JSON.stringify({ type: "get_context" }));
    };
    ws.onclose = () => setStatus("disconnected");
    ws.onerror = () => setStatus("error");
    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        setMessages((prev) => [...prev, data]);
        if (data.type === "options" && Array.isArray(data.data)) {
          setOptions(data.data);
        } else if (data.type === "selected") {
          setLastSelected(data.data);
          setConversationLog((prev) => [...prev, { role: "assistant", text: data.data }]);
        } else if (data.type === "context_snapshot" && onContextSnapshot) {
          onContextSnapshot(data);
        } else if (data.type === "conversation_highlight" && typeof data.data === "string") {
          setMessages((prev) => [...prev, { type: "conversation_highlight", data: data.data }]);
        }
      } catch {
        setMessages((prev) => [...prev, { raw: evt.data }]);
      }
    };
    return () => ws.close();
  }, [onContextSnapshot]);

  const send = (payload) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(payload));
    } else {
      console.warn("WebSocket not ready");
    }
  };

  const appendUserSpeech = (text) => {
    if (!text) return;
    setConversationLog((prev) => [...prev, { role: "user", text }]);
  };

  return {
    status,
    messages,
    options,
    lastSelected,
    send,
    conversationLog,
    setConversationLog,
    appendUserSpeech,
  };
}

function App() {
  const [coreLines, setCoreLines] = useState([]);
  const [highlights, setHighlights] = useState([]);
  const [newLine, setNewLine] = useState("");
  const [newHighlight, setNewHighlight] = useState("");
  const [icsEvents, setIcsEvents] = useState([]);
  const [scheduleSummary, setScheduleSummary] = useState({
    current: "None",
    previous: [],
    upcoming: [],
  });
  const [activeTab, setActiveTab] = useState("Status");

  const onContextSnapshot = React.useCallback((data) => {
    if (Array.isArray(data.core)) setCoreLines(data.core);
    if (Array.isArray(data.highlights)) {
      const mapped = data.highlights.map((h) => ({
        start_at: h.start_at || "",
        stop_at: h.stop_at || "",
        highlight: h.highlight || h,
      }));
      setHighlights(mapped);
    }
    if (Array.isArray(data.events)) {
      const evs = data.events
        .map((e) => ({
          summary: e.summary,
          start: e.start ? new Date(e.start) : null,
          end: e.end ? new Date(e.end) : null,
          location: e.location,
        }))
        .filter((e) => e.start && e.end);
      setIcsEvents(evs);
      setScheduleSummary(summarizeSchedule(evs));
    }
    if (typeof data.schedule === "string") {
      setScheduleSummary((prev) => ({
        ...prev,
        current: data.schedule,
      }));
    }
  }, []);

  const { status, messages, options, lastSelected, send, conversationLog, appendUserSpeech } =
    useWebSocketClient(onContextSnapshot);

  const startConversation = () => send({ type: "start_conversation" });
  const stopConversation = () => send({ type: "stop_conversation" });
  const sendAudio = (text) => {
    if (!text) return;
    appendUserSpeech(text);
    send({ audio_data: text });
  };
  const selectOption = (idx) => send({ type: "select", data: idx + 1 });

  const addCore = () => {
    if (!newLine.trim()) return;
    const updated = [...coreLines, newLine.trim()];
    setCoreLines(updated);
    send({ type: "set_core_context", data: updated });
    setNewLine("");
  };
  const addHighlight = () => {
    if (!newHighlight.trim()) return;
    const newEntry = {
      start_at: new Date().toISOString(),
      stop_at: new Date().toISOString(),
      highlight: newHighlight.trim(),
    };
    const updated = [...highlights, newEntry];
    setHighlights(updated);
    send({ type: "add_highlight", data: newHighlight.trim() });
    setNewHighlight("");
  };

  const deleteCore = (i) => {
    const updated = coreLines.filter((_, idx) => idx !== i);
    setCoreLines(updated);
    send({ type: "set_core_context", data: updated });
  };
  const deleteHighlight = (i) =>
    setHighlights((prev) => {
      const updated = prev.filter((_, idx) => idx !== i);
      send({ type: "delete_highlight", data: i });
      return updated;
    });

  const onIcsUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const text = reader.result?.toString() || "";
      const parsed = parseIcs(text);
      setIcsEvents(parsed);
      setScheduleSummary(summarizeSchedule(parsed));
      send({ type: "set_calendar", data: text });
    };
    reader.readAsText(file);
  };

  return (
    <div className="app">
      <header>
        <h1>SpeechLens Dashboard</h1>
        <div className={`status ${status}`}>Server: {status}</div>
      </header>

      <nav className="tabs">
        {tabs.map((tab) => (
          <button
            key={tab}
            className={tab === activeTab ? "active" : ""}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </nav>

      <main>
        {activeTab === "Status" && (
          <section>
            <h2>Status</h2>
            <p>WS URL: {WS_URL}</p>
            <button onClick={startConversation}>Start Conversation</button>
            <button onClick={stopConversation} style={{ marginLeft: 8 }}>
              Stop Conversation
            </button>
            <h3>Recent Messages</h3>
            <div className="log">
              {conversationLog.map((entry, idx) => (
                <div key={idx} style={{ marginBottom: 4 }}>
                  <strong>{entry.role === "user" ? "Heard" : "User Selection"}:</strong>{" "}
                  {entry.text}
                </div>
              ))}
            </div>
          </section>
        )}

        {activeTab === "Conversation" && (
          <section>
            <h2>Conversation</h2>
            <button onClick={startConversation}>Start Conversation</button>
            <button onClick={stopConversation} style={{ marginLeft: 8 }}>
              Stop Conversation
            </button>
            <div className="input-row">
              <input
                type="text"
                placeholder="Enter heard speech..."
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    sendAudio(e.target.value);
                    e.target.value = "";
                  }
                }}
              />
              <button
                onClick={() => {
                  const val = prompt("Speech text?");
                  if (val) sendAudio(val);
                }}
              >
                Send Speech
              </button>
            </div>
            <h3>Options</h3>
            <ul className="options">
              {options.map((opt, idx) => (
                <li key={idx}>
                  <span>{opt}</span>
                  <button onClick={() => selectOption(idx)}>Select</button>
                </li>
              ))}
            </ul>
            {lastSelected && <div className="selected">Last selected: {lastSelected}</div>}
            <h3>Conversation Log (heard vs. spoken)</h3>
            <ul className="list">
              {conversationLog.map((entry, idx) => (
                <li key={idx}>
                  <span>
                    <strong>{entry.role === "user" ? "Heard" : "Spoken"}:</strong> {entry.text}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {activeTab === "Core Info" && (
          <section>
            <h2>Core Information</h2>
            <div className="input-row">
              <input
                value={newLine}
                onChange={(e) => setNewLine(e.target.value)}
                placeholder="Add core fact (e.g., Likes: ...)"
              />
              <button onClick={addCore}>Add</button>
            </div>
            <ul className="list">
              {coreLines.map((line, idx) => (
                <li key={idx}>
                  <span>{line}</span>
                  <button onClick={() => deleteCore(idx)}>Delete</button>
                </li>
              ))}
            </ul>
          </section>
        )}

        {activeTab === "Highlights" && (
          <section>
            <h2>Highlights</h2>
            <div className="input-row">
              <input
                value={newHighlight}
                onChange={(e) => setNewHighlight(e.target.value)}
                placeholder="Add highlight"
              />
              <button onClick={addHighlight}>Add</button>
            </div>
            <ul className="list">
              {highlights.map((line, idx) => (
                <li key={idx}>
                  <div>
                    <div>{line.highlight || line}</div>
                    {line.start_at && (
                      <div className="small">
                        {line.start_at} {line.stop_at ? `- ${line.stop_at}` : ""}
                      </div>
                    )}
                  </div>
                  <button onClick={() => deleteHighlight(idx)}>Delete</button>
                </li>
              ))}
            </ul>
          </section>
        )}

        {activeTab === "Calendar" && (
          <section>
            <h2>Calendar (ICS)</h2>
            <input type="file" accept=".ics" onChange={onIcsUpload} />
            <div className="calendar-summary">
              <p>
                <strong>Current:</strong> {scheduleSummary.current}
              </p>
              {scheduleSummary.previous?.length > 0 && (
                <p>
                  <strong>Earlier:</strong> {scheduleSummary.previous.join(" | ")}
                </p>
              )}
              {scheduleSummary.upcoming?.length > 0 && (
                <p>
                  <strong>Upcoming:</strong> {scheduleSummary.upcoming.join(" | ")}
                </p>
              )}
            </div>
            <h3>Events</h3>
            <ul className="list">
              {icsEvents.map((ev, idx) => (
                <li key={idx}>
                  <div>{ev.summary}</div>
                  <div className="small">
                    {ev.start.toLocaleString()} - {ev.end.toLocaleTimeString()}
                    {ev.location ? ` @ ${ev.location}` : ""}
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
