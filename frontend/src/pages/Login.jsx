import { useState } from 'react';
import { loginJson } from '../api/auth';
import '../styles/login.css';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      const d = await loginJson(username, password);
      if (d.ok) {
        window.location.href = '/';
      } else {
        setError(d.error || 'Неверный логин или пароль');
        setSubmitting(false);
      }
    } catch {
      setError('Ошибка соединения с сервером');
      setSubmitting(false);
    }
  };

  return (
    <div className="login-root">
      <div className="login-grid-bg" />
      <div className="login-panel">
        <div className="login-corner tl" /><div className="login-corner tr" />
        <div className="login-corner bl" /><div className="login-corner br" />
        <div className="login-logo">
          <div className="login-logo-main">Kaz<span>NU</span></div>
          <div className="login-logo-sub">Al-Farabi 5G Project</div>
        </div>
        {error && <div className="login-error">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="login-field">
            <label>Логин</label>
            <input type="text" autoFocus autoComplete="username" value={username}
                   onChange={(e) => setUsername(e.target.value)} />
          </div>
          <div className="login-field">
            <label>Пароль</label>
            <input type="password" autoComplete="current-password" value={password}
                   onChange={(e) => setPassword(e.target.value)} />
          </div>
          <button className="login-btn" type="submit" disabled={submitting}>Войти</button>
        </form>
      </div>
    </div>
  );
}
