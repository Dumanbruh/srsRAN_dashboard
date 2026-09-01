import { useEffect, useState } from 'react';
import Topbar from '../components/layout/Topbar';
import ActiveRunPanel from '../components/scenarios/ActiveRunPanel';
import ScenarioCard from '../components/scenarios/ScenarioCard';
import RunHistoryTable from '../components/scenarios/RunHistoryTable';
import { useAuth } from '../context/AuthContext';
import { useScenarioRunSSE } from '../hooks/useScenarioRunSSE';
import { useActiveRunPoll } from '../hooks/useActiveRunPoll';
import { usePolling } from '../hooks/usePolling';
import { getScenarios, runScenario, stopRun, getRuns } from '../api/scenarios';
import { scnStatusLabel } from '../utils/format';
import '../styles/scenarios.css';

export default function Scenarios() {
  const { user } = useAuth();
  const isAdmin = !!user?.is_admin;

  const [catalog, setCatalog] = useState([]);
  const [runs, setRuns] = useState([]);
  const { run, logLines, attach, isAttached } = useScenarioRunSSE();

  useActiveRunPoll(isAttached, attach);
  useEffect(() => { getScenarios().then((d) => { if (d.ok) setCatalog(d.scenarios); }); }, []);
  usePolling(async () => {
    const d = await getRuns(30);
    if (d.ok) setRuns(d.runs);
  }, 8000);

  const handleRun = async (slug, params) => {
    const d = await runScenario(slug, params);
    if (!d.ok) { alert('Ошибка запуска: ' + d.error); return; }
    attach(d.run.id);
  };
  const handleStop = async (runId) => {
    const d = await stopRun(runId);
    if (!d.ok) alert('Не удалось остановить: ' + d.error);
  };

  return (
    <>
      <Topbar title="Сценарии">
        {run && <span className={`badge ${run.status}`}>{run.scenario_name} — {scnStatusLabel(run.status)}</span>}
      </Topbar>

      <div className="page-body">
        <div className="section-title">Текущий прогон</div>
        <ActiveRunPanel run={run} logLines={logLines} isAdmin={isAdmin} onStop={handleStop} />

        <div className="section-title">Каталог сценариев</div>
        {!isAdmin && <div className="viewer-only-hint">Роль viewer — запуск/остановка недоступны, только просмотр.</div>}
        <div className="scenario-grid">
          {catalog.map((s) => <ScenarioCard key={s.slug} scenario={s} isAdmin={isAdmin} onRun={handleRun} />)}
        </div>

        <div className="section-title">История прогонов</div>
        <RunHistoryTable runs={runs} onAttach={attach} />
      </div>
    </>
  );
}
