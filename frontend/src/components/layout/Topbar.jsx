export default function Topbar({ title, children }) {
  return (
    <div className="topbar">
      <div className="page-title">{title}</div>
      <div className="status-row">{children}</div>
    </div>
  );
}
