import { formatMessage, formatPlainText } from '../../utils/chatFormat';

export default function ChatMessage({ role, text, ts }) {
  if (role === 'user') {
    return (
      <div className="msg user">
        <div>
          <div className="msg-bubble">{formatPlainText(text)}</div>
          <div className="msg-time">{ts}</div>
        </div>
        <div className="msg-avatar">U</div>
      </div>
    );
  }
  return (
    <div className="msg ai">
      <div className="msg-avatar">AI</div>
      <div>
        <div className="msg-bubble">{formatMessage(text)}</div>
        <div className="msg-time">{ts}</div>
      </div>
    </div>
  );
}
