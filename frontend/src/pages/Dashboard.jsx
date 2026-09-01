import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import Topbar from '../components/layout/Topbar';
import StatusBadge from '../components/layout/StatusBadge';
import MetricCard from '../components/dashboard/MetricCard';
import ThroughputChart from '../components/dashboard/ThroughputChart';
import UeCard from '../components/dashboard/UeCard';
import NoisePanel from '../components/dashboard/NoisePanel';
import TestbedControlPanel from '../components/dashboard/TestbedControlPanel';
import TimeRangeToolbar from '../components/dashboard/TimeRangeToolbar';
import ScenarioQuickPanel from '../components/dashboard/ScenarioQuickPanel';
import EventLogPanel from '../components/dashboard/EventLogPanel';
import QuickCommandsPanel from '../components/dashboard/QuickCommandsPanel';
import { useAuth } from '../context/AuthContext';
import { useStats } from '../hooks/useStats';
import { useGnrStatus } from '../hooks/useGnrStatus';
import { useTestbedStatus } from '../hooks/useTestbedStatus';
import { useHistory } from '../hooks/useHistory';
import { useDemoTraffic } from '../hooks/useDemoTraffic';
import { useEventLog } from '../hooks/useEventLog';
import { useScenarioRunSSE } from '../hooks/useScenarioRunSSE';
import { useActiveRunPoll } from '../hooks/useActiveRunPoll';
import { setPathloss as apiSetPathloss, toggleUe as apiToggleUe, setNoise as apiSetNoise } from '../api/ue';
import { exportCsvUrl } from '../api/stats';
import { getScenarios, runScenario, stopRun as apiStopRun } from '../api/scenarios';
import '../styles/dashboard.css';

const UE_COLORS = ['#347cbe', '#178a63', '#dfa359', '#b8305c', '#8B5CF6', '#14B8A6', '#F97316'];
const UE_DEFAULTS_PL = [0, 0, 0, 0, 0, 0, 0];

function buildUes(n) {
  return Array.from({ length: n }, (_, i) => ({
    id: i + 1, active: true, pathloss: UE_DEFAULTS_PL[i] || 0,
    dl: 0, ul: 0, snr: 0, nok: 0, trafficRunning: false,
  }));
}

export default function Dashboard() {
  const { user } = useAuth();
  const isAdmin = !!user?.is_admin;

  const [ues, setUes] = useState(() => buildUes(1));
  const uesLenRef = useRef(1);
  uesLenRef.current = ues.length;

  const [searchParams] = useSearchParams();
  const deepLink = searchParams.get('start') && searchParams.get('end');

  const [range, setRange] = useState('30m');
  const [customStart, setCustomStart] = useState(() => deepLink ? searchParams.get('start') : null);
  const [customEnd, setCustomEnd] = useState(() => deepLink ? searchParams.get('end') : null);
  const [metric1, setMetric1] = useState('dl');
  const [metric2, setMetric2] = useState('ul');
  const [interval, setInterval_] = useState('30s');
  const [noise, setNoiseState] = useState('none');
  const [noiseLevel, setNoiseLevel] = useState(0);
  const [catalog, setCatalog] = useState([]);

  const { log, lines: logLines, count: logCount } = useEventLog();
  const { influxOk, gnbOk } = useStats(ues, setUes);
  const gnrOk = useGnrStatus();
  const { demoActiveUes, demoPoints, runTraffic } = useDemoTraffic(setUes);
  const { run, logLines: scnLogLines, attach, isAttached } = useScenarioRunSSE();
  useActiveRunPoll(isAttached, attach);

  const onNUesChanged = useCallback((n) => {
    if (n !== uesLenRef.current) setUes(buildUes(n));
  }, []);
  const { status: testbedStatus, start: startTestbed, stop: stopTestbed } = useTestbedStatus(onNUesChanged);

  useEffect(() => { getScenarios().then((d) => { if (d.ok) setCatalog(d.scenarios); }); }, []);
  useEffect(() => {
    log('Дашборд запущен', 'ok');
    log('Подключение к InfluxDB...');
    log('Подключение к GNU Radio XML-RPC...');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isFixedRange = !!(customStart && customEnd);
  const rangeParams = isFixedRange
    ? `start=${encodeURIComponent(customStart)}&end=${encodeURIComponent(customEnd)}`
    : `start=-${range}`;

  const h1 = useHistory(metric1, interval, rangeParams, { suppressed: demoActiveUes.size > 0, isFixedRange });
  const h2 = useHistory(metric2, interval, rangeParams, { suppressed: demoActiveUes.size > 0, isFixedRange });

  function buildChartData(metric, historyRows, historyRntis) {
    const lines = historyRntis.map((rnti, i) => ({ key: rnti, label: rnti, color: UE_COLORS[i % UE_COLORS.length] }));
    if ((metric !== 'dl' && metric !== 'ul') || demoActiveUes.size === 0) {
      return { rows: historyRows, lines };
    }
    const demoLines = [];
    const demoRows = [];
    demoActiveUes.forEach((ueId) => {
      const key = `demo_${ueId}`;
      demoLines.push({ key, label: `UE${ueId} (демо)`, color: '#b8305c', dashed: true });
      (demoPoints[ueId] || []).forEach((p) => demoRows.push({ t: p.t, [key]: p[metric] }));
    });
    return { rows: [...historyRows, ...demoRows], lines: [...lines, ...demoLines] };
  }

  const chart1 = buildChartData(metric1, h1.rows, h1.rntis);
  const chart2 = buildChartData(metric2, h2.rows, h2.rntis);

  const activeUes = ues.filter((u) => u.active);
  const totalDl = activeUes.reduce((s, u) => s + u.dl * 1000, 0);
  const totalUl = activeUes.reduce((s, u) => s + u.ul * 1000, 0);
  const avgSnr = activeUes.length ? activeUes.reduce((s, u) => s + u.snr, 0) / activeUes.length : 0;
  const avgNok = activeUes.length ? activeUes.reduce((s, u) => s + u.nok, 0) / activeUes.length : 0;

  const handleToggle = async (id) => {
    if (!isAdmin) return;
    const ue = ues.find((u) => u.id === id);
    const nextActive = !ue.active;
    setUes((prev) => prev.map((u) => (u.id === id ? { ...u, active: nextActive } : u)));
    const d = await apiToggleUe(id, nextActive, ue.pathloss);
    log(`UE${id} ${nextActive ? 'включён' : 'отключён'}`, nextActive ? 'ok' : 'warn');
    if (!d.ok) log(`UE${id}: ошибка переключения`, 'err');
  };

  const handlePathloss = async (id, val) => {
    if (!isAdmin) return;
    const v = parseInt(val, 10);
    setUes((prev) => prev.map((u) => (u.id === id ? { ...u, pathloss: v } : u)));
    const d = await apiSetPathloss(id, v);
    if (d.ok) log(`UE${id} pathloss → ${v}dB`);
  };

  const handleSetAllUes = async (active) => {
    if (!isAdmin) return;
    setUes((prev) => prev.map((u) => ({ ...u, active })));
    await Promise.all(ues.map((u) => apiToggleUe(u.id, active, u.pathloss)));
    log(`Все UE ${active ? 'включены' : 'отключены'}`, active ? 'ok' : 'warn');
  };

  const handleResetPathloss = async () => {
    if (!isAdmin) return;
    setUes((prev) => prev.map((u, i) => ({ ...u, pathloss: UE_DEFAULTS_PL[i] || 0 })));
    await Promise.all(ues.map((u, i) => apiSetPathloss(u.id, UE_DEFAULTS_PL[i] || 0)));
    log('Pathloss сброшен', 'ok');
  };

  const handleSetNoise = async (type) => {
    setNoiseState(type);
    const labels = { none: 'Чистый канал', awgn: 'AWGN', fading: 'Rayleigh Fading', shadow: 'Shadowing', doppler: 'Doppler', interf: 'Интерференция' };
    if (isAdmin) {
      const d = await apiSetNoise(type, noiseLevel);
      log('Помеха: ' + labels[type], type === 'none' ? 'ok' : 'warn');
      if (!d.ok) log('Ошибка установки помехи', 'err');
    }
  };

  const handleNoiseLevel = (val) => {
    const v = parseInt(val, 10);
    setNoiseLevel(v);
    if (noise !== 'none' && isAdmin) apiSetNoise(noise, v);
  };

  const handleExport = () => { window.location.href = exportCsvUrl(metric1, interval, rangeParams); log('CSV экспорт запущен', 'ok'); };

  const handleApplyCustomRange = (startLocal, endLocal) => {
    setCustomStart(new Date(startLocal).toISOString());
    setCustomEnd(new Date(endLocal).toISOString());
  };
  const handleRangeChange = (preset) => { setRange(preset); setCustomStart(null); setCustomEnd(null); };

  const handleQuickRun = async (slug) => {
    const d = await runScenario(slug, {});
    if (!d.ok) { alert('Ошибка запуска: ' + d.error); return; }
    attach(d.run.id);
  };
  const handleStopRun = async (runId) => {
    const d = await apiStopRun(runId);
    if (!d.ok) alert('Не удалось остановить: ' + d.error);
  };

  return (
    <>
      <Topbar title="Обзор сети">
        <StatusBadge status={influxOk ? 'ok' : 'err'} label="InfluxDB" />
        <StatusBadge status={gnrOk ? 'ok' : 'err'} label="GNU Radio" />
        <StatusBadge status={gnbOk ? 'ok' : 'err'} label="gNB" />
        <StatusBadge status={testbedStatus.running ? 'ok' : 'err'} label="Testbed" />
      </Topbar>

      <div className="page-body">
        <TimeRangeToolbar
          range={range} onRangeChange={handleRangeChange}
          metric1={metric1} onMetric1Change={setMetric1}
          metric2={metric2} onMetric2Change={setMetric2}
          interval={interval} onIntervalChange={setInterval_}
          isFixedRange={isFixedRange} onApplyCustomRange={handleApplyCustomRange}
          onExport={handleExport}
        />

        <div className="metrics-grid">
          <MetricCard color="blue" label="Total DL" value={totalDl.toFixed(0)} unit="kb/s" />
          <MetricCard color="blue" label="Total UL" value={totalUl.toFixed(0)} unit="kb/s" />
          <MetricCard color="green" label="Активных UE" value={activeUes.length} unit={`/${ues.length}`} />
          <MetricCard color="amber" label="Avg PUSCH SNR" value={avgSnr.toFixed(1)} unit="dB" />
          <MetricCard color="pink" label="Avg NOK%" value={avgNok.toFixed(0)} unit="%" />
        </div>

        <ScenarioQuickPanel catalog={catalog} isAdmin={isAdmin} run={run} logLines={scnLogLines}
                             onQuickRun={handleQuickRun} onStop={handleStopRun} />

        <div className="charts-grid">
          <ThroughputChart title="DL Throughput" rows={chart1.rows} lines={chart1.lines} legend={chart1.lines} loading={h1.loading} />
          <ThroughputChart title="UL Throughput" rows={chart2.rows} lines={chart2.lines} legend={chart2.lines} loading={h2.loading} />
        </div>

        <div className="ue-grid">
          {ues.map((ue, i) => (
            <UeCard key={ue.id} ue={ue} color={UE_COLORS[i % UE_COLORS.length]} isAdmin={isAdmin}
                    onToggle={handleToggle} onPathloss={handlePathloss} onRunTraffic={runTraffic} />
          ))}
        </div>

        {isAdmin && <TestbedControlPanel status={testbedStatus} onStart={startTestbed} onStop={stopTestbed} />}
        {isAdmin && <NoisePanel noise={noise} noiseLevel={noiseLevel} onSetNoise={handleSetNoise} onSetLevel={handleNoiseLevel} />}

        <div className="bottom-grid">
          <EventLogPanel lines={logLines} count={logCount} />
          <QuickCommandsPanel isAdmin={isAdmin} onSetAllUes={handleSetAllUes} onResetPathloss={handleResetPathloss}
                               onClearNoise={() => handleSetNoise('none')}
                               onRefresh={() => { h1.refresh(); h2.refresh(); log('Данные обновлены'); }}
                               onExport={handleExport} />
        </div>
      </div>
    </>
  );
}
