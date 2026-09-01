import { useRef } from 'react';

export default function ChatInput({ value, onChange, onSend, disabled, msgCount }) {
  const taRef = useRef(null);

  const autoResize = () => {
    const el = taRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 150) + 'px';
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSend(); }
  };

  return (
    <>
      <div className="input-row">
        <div className="input-wrap">
          <textarea
            ref={taRef} rows={1} value={value}
            placeholder="Спроси про состояние сети, параметры, диагностику..."
            onChange={(e) => { onChange(e.target.value); autoResize(); }}
            onKeyDown={handleKeyDown}
          />
        </div>
        <button className="send-btn" disabled={disabled} onClick={onSend}>Отправить</button>
      </div>
      <div className="input-hint">
        <span>Enter — отправить · Shift+Enter — новая строка</span>
        <span>{msgCount} сообщений</span>
      </div>
    </>
  );
}
