import { useEffect, useRef, useState } from 'react';
import Topbar from '../components/layout/Topbar';
import SummaryBar from '../components/ai/SummaryBar';
import ChatMessage from '../components/ai/ChatMessage';
import ChatInput from '../components/ai/ChatInput';
import QuickPrompts from '../components/ai/QuickPrompts';
import { useAiSummary } from '../hooks/useAiSummary';
import { useOllamaStatus } from '../hooks/useOllamaStatus';
import { aiChat } from '../api/ai';
import '../styles/ai.css';

function ts() { return new Date().toTimeString().slice(0, 8); }

export default function AI() {
  const { ues, ok: influxOk, dlHistory } = useAiSummary();
  const ollamaOk = useOllamaStatus();

  const [messages, setMessages] = useState([]);
  const [history, setHistory] = useState([]); // flat [{role, content}] pairs sent to the API
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const chatAreaRef = useRef(null);

  useEffect(() => {
    if (chatAreaRef.current) chatAreaRef.current.scrollTop = chatAreaRef.current.scrollHeight;
  }, [messages, sending]);

  const handleSend = async (text) => {
    const msg = (text ?? input).trim();
    if (!msg) return;
    setInput('');
    setSending(true);
    setMessages((prev) => [...prev, { role: 'user', text: msg, ts: ts() }]);

    try {
      const d = await aiChat(msg, history);
      if (d.ok) {
        setMessages((prev) => [...prev, { role: 'ai', text: d.response, ts: ts() }]);
        setHistory((prev) => {
          const next = [...prev, { role: 'user', content: msg }, { role: 'assistant', content: d.response }];
          return next.length > 40 ? next.slice(next.length - 40) : next;
        });
      } else {
        setMessages((prev) => [...prev, { role: 'ai', text: 'Ошибка: ' + (d.error || 'неизвестная ошибка'), ts: ts() }]);
      }
    } catch (e) {
      setMessages((prev) => [...prev, { role: 'ai', text: 'Ошибка соединения с сервером: ' + e.message, ts: ts() }]);
    } finally {
      setSending(false);
    }
  };

  const clearChat = () => { setMessages([]); setHistory([]); };

  return (
    <div className="ai-main">
      <Topbar title="AI Ассистент">
        <div className="topbar-right">
          <span className="model-badge">qwen2.5:7b-instruct</span>
          <button className="clear-btn" onClick={clearChat}>Очистить чат</button>
        </div>
      </Topbar>

      <SummaryBar ues={ues} ok={influxOk} dlHistory={dlHistory} />

      <div className="chat-area" ref={chatAreaRef}>
        {messages.length === 0 && <QuickPrompts onSend={handleSend} />}
        {messages.map((m, i) => <ChatMessage key={i} role={m.role} text={m.text} ts={m.ts} />)}
        {sending && (
          <div className="msg ai">
            <div className="msg-avatar">AI</div>
            <div className="msg-bubble"><div className="typing"><span /><span /><span /></div></div>
          </div>
        )}
      </div>

      <div className="input-area">
        <div className="ctx-bar">
          <div className="ctx-item">
            <div className={`ctx-dot ${influxOk ? 'ok' : 'err'}`} />
            <span className="ctx-label">InfluxDB: {influxOk ? `${ues.length} UE` : 'нет данных'}</span>
          </div>
          <div className="ctx-item">
            <div className={`ctx-dot ${ollamaOk ? 'ok' : 'err'}`} />
            <span className="ctx-label">Ollama: {ollamaOk === null ? 'проверка...' : (ollamaOk ? 'готов' : 'недоступен')}</span>
          </div>
        </div>
        <ChatInput value={input} onChange={setInput} onSend={() => handleSend()} disabled={sending}
                   msgCount={Math.floor(history.length / 2)} />
      </div>
    </div>
  );
}
