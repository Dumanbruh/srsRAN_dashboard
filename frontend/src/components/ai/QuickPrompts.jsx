const PROMPTS = [
  ['Проанализируй текущее состояние сети и оцени качество связи', 'Анализ сети'],
  ['Какие метрики CQI и MCS сейчас? Как их улучшить?', 'CQI / MCS'],
  ['Как оптимально выбрать pathloss для UE1 в тесте?', 'Pathloss совет'],
  ['Объясни архитектуру: gNB → GNU Radio → srsUE через ZMQ', 'Архитектура ZMQ'],
  ['Как запустить iperf3 трафик и что это даст для метрик?', 'Трафик iperf3'],
  ['Что означают поля dl_brate, ul_brate, cqi, dl_mcs, dl_nof_nok в метриках gNB?', 'Метрики gNB'],
];

export default function QuickPrompts({ onSend }) {
  return (
    <div className="welcome">
      <div className="welcome-icon">◈</div>
      <div className="welcome-title">AI Ассистент 5G NR</div>
      <div className="welcome-sub">
        Анализирую состояние srsRAN testbed в реальном времени.<br />
        Задай вопрос или выбери быстрый сценарий:
      </div>
      <div className="quick-btns">
        {PROMPTS.map(([text, label]) => (
          <button key={label} className="qbtn" onClick={() => onSend(text)}>{label}</button>
        ))}
      </div>
    </div>
  );
}
