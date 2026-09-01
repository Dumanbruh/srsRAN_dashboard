export default function QuickCommandsPanel({ isAdmin, onSetAllUes, onResetPathloss, onClearNoise, onRefresh, onExport }) {
  return (
    <div className="cmd-panel">
      <div className="cmd-title">Быстрые команды</div>
      <div className="cmd-grid">
        {isAdmin && <button className="cmd-btn" onClick={() => onSetAllUes(true)}>Включить все UE</button>}
        {isAdmin && <button className="cmd-btn danger" onClick={() => onSetAllUes(false)}>Отключить все UE</button>}
        {isAdmin && <button className="cmd-btn" onClick={onResetPathloss}>Сброс pathloss</button>}
        {isAdmin && <button className="cmd-btn" onClick={onClearNoise}>Очистить помехи</button>}
        <button className="cmd-btn" onClick={onRefresh}>Обновить данные</button>
        <button className="cmd-btn" onClick={onExport}>Экспорт CSV</button>
      </div>
    </div>
  );
}
