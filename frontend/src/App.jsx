import { useMemo, useState, useRef, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

/*  Message Component */
function Message({ msg }) {
  return (
    <div className={`msg ${msg.role}`}>
      <div className="bubble">
        <div className="role">
          {msg.role === "user" ? "You" : "Assistant"}
        </div>

        <p>{msg.content}</p>

        {msg.sources?.length > 0 && (
          <div className="sources">
            {msg.sources.map((s, idx) => (
              <a key={idx} href={s.url} target="_blank" rel="noreferrer">
                {new URL(s.url).hostname} ({s.score.toFixed(2)})
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/*  Toast Component */
function Toast({ toast }) {
  return <div className={`toast ${toast.type}`}>{toast.message}</div>;
}

function App() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "hi! ask me anything about gitlab handbook or direction. i will answer with sources"
    }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [topK, setTopK] = useState(5);
  const [dark, setDark] = useState(true);
  const [toasts, setToasts] = useState([]);

  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const history = useMemo(
    () => messages.map((m) => ({ role: m.role, content: m.content })),
    [messages]
  );

  /*Toast logic */
  function showToast(message, type = "error") {
    const newToast = {
      id: Date.now(),
      message,
      type,
      createdAt: Date.now()
    };

    setToasts((prev) => prev.concat(newToast));

    setTimeout(() => {
      const now = Date.now();
      setToasts((prev) =>
        prev.filter((t) => now - t.createdAt < 3000)
      );
    }, 3000);
  }

  /*  Send question */
  async function sendQuestion() {
    const question = input.trim();

    if (!question) {
      showToast("please enter a valid question");
      return;
    }

    if (loading) return;

    setLoading(true);
    setInput("");

    setMessages((prev) =>
      prev.concat({ role: "user", content: question })
    );

    const fetchResponse = async () => {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, top_k: topK, history })
      });

      if (!res.ok) {
        let errMsg = `api error ${res.status}`;
        try {
          const errData = await res.json();
          if (errData.detail) {
            errMsg = typeof errData.detail === "string" ? errData.detail : errData.detail[0].msg;
          }
        } catch (e) {}
        return { error: errMsg };
      }

      const data = await res.json();
      return { data };
    };

    const result = await fetchResponse().catch(() => ({
      error: "network error: unable to reach backend"
    }));

    if (result.error) {
      showToast(result.error);
      setLoading(false);
      return;
    }

    setMessages((prev) =>
      prev.concat({
        role: "assistant",
        content: result.data.answer,
        sources: result.data.sources || []
      })
    );

    showToast("response received", "success");
    setLoading(false);
  }

  return (
    <div className={dark ? "app dark" : "app"}>
      
      {/* HEADER */}
      <header className="header">
        <h1>GitLab AI Chatbot</h1>
        <button className="theme-btn" onClick={() => setDark(!dark)}>
          {dark ? "🌙" : "☀️"}
        </button>
      </header>

      {/* CONTROLS */}
      <div className="controls">
        <div className="slider-box">
          <label>
            Top K: <strong>{topK}</strong>
          </label>
          <input
            type="range"
            min="3"
            max="10"
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
          />
        </div>
      </div>

      {/* CHAT */}
      <main className="chat">
        {messages.map((msg, i) => (
          <Message key={i} msg={msg} />
        ))}

        {loading && <div className="typing">thinking...</div>}
        <div ref={bottomRef}></div>
      </main>

    
      <footer className="input-area">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="ask something about gitlab..."
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              sendQuestion();
            }
          }}
        />
        <button onClick={sendQuestion}>
          {loading ? "..." : "Send"}
        </button>
      </footer>

     
      <div className="toast-container">
        {toasts.map((t) => (
          <Toast key={t.id} toast={t} />
        ))}
      </div>
    </div>
  );
}

export default App;