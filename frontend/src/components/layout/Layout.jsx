import Sidebar from './Sidebar';
import './layout.css';

export default function Layout({ children }) {
  return (
    <div className="layout">
      <Sidebar />
      <div className="main">{children}</div>
    </div>
  );
}
