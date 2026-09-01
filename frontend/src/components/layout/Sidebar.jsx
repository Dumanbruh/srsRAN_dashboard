import { NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

const NAV = [
  { to: '/', label: 'Дашборд', end: true },
  { to: '/scenarios/', label: 'Сценарии' },
  { to: '/ai/', label: 'AI Ассистент' },
];

export default function Sidebar() {
  const { user } = useAuth();

  return (
    <aside className="sidebar">
      <div className="sb-logo">
        <div className="sb-logo-text">Kaz<span>NU</span></div>
        <div className="sb-logo-sub">5G Project</div>
      </div>

      <div className="sb-section">Навигация</div>
      {NAV.map((n) => (
        <NavLink
          key={n.to}
          to={n.to}
          end={n.end}
          className={({ isActive }) => 'sb-link' + (isActive ? ' active' : '')}
        >
          {n.label}
        </NavLink>
      ))}

      <div className="sb-bottom">
        {user && (
          <div className="sb-user">
            <div className="sb-avatar">{user.username?.[0]?.toUpperCase()}</div>
            <div>
              <div className="sb-uname">{user.username}</div>
              <div className="sb-role">{user.is_admin ? 'admin' : 'viewer'}</div>
            </div>
          </div>
        )}
        <a className="sb-logout" href="/logout/">Выйти</a>
      </div>
    </aside>
  );
}
