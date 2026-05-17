// MeliSim — Admin Overview + Services + Outbox + DLQ + Kafka

const langColors = { Python: '#3776AB', Java: '#E76F00', Kotlin: '#7F52FF', Go: '#00ADD8' };
const statusDot = (s) => ({ UP: C.success, DEGRADED: C.warning, DOWN: C.danger })[s] || C.gray400;

function ServiceTile({ svc }) {
  const spark = Array.from({ length: 12 }, () => Math.round(svc.rps * (0.6 + Math.random() * 0.8)));
  return (
    <Card style={{ padding: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: statusDot(svc.status), animation: svc.status === 'DEGRADED' ? 'pulse 2s infinite' : 'none' }}></div>
          <span style={{ fontSize: 13, fontWeight: 700, color: C.gray800 }}>{svc.name}</span>
        </div>
        <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 3, background: langColors[svc.lang] || C.gray400, color: '#fff' }}>{svc.lang}</span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <div style={{ fontSize: 11, color: C.gray500 }}>:{svc.port}</div>
          <div style={{ fontSize: 18, fontWeight: 800, color: C.gray900, marginTop: 2 }}>{svc.rps} <span style={{ fontSize: 11, fontWeight: 400, color: C.gray400 }}>RPS</span></div>
          <div style={{ fontSize: 12, color: svc.p95 > 200 ? C.danger : C.gray600 }}>p95 {svc.p95}ms</div>
        </div>
        <Sparkline data={spark} color={svc.p95 > 200 ? C.danger : C.action} width={70} height={28} />
      </div>
    </Card>
  );
}

function DependencyMap() {
  const nodes = [
    { id: 'api-gateway', x: 300, y: 50 },
    { id: 'users', x: 80, y: 160 }, { id: 'products', x: 220, y: 160 },
    { id: 'orders', x: 380, y: 160 }, { id: 'payments', x: 520, y: 160 },
    { id: 'notifications', x: 120, y: 270 }, { id: 'search', x: 300, y: 270 },
    { id: 'stock-monitor', x: 480, y: 270 },
  ];
  const edges = [
    { from: 'api-gateway', to: 'users' }, { from: 'api-gateway', to: 'products' },
    { from: 'api-gateway', to: 'orders' }, { from: 'api-gateway', to: 'payments', degraded: true },
    { from: 'orders', to: 'notifications' }, { from: 'orders', to: 'payments', degraded: true },
    { from: 'products', to: 'search' }, { from: 'stock-monitor', to: 'products' },
  ];
  const nodeMap = Object.fromEntries(nodes.map(n => [n.id, n]));

  return (
    <Card hover={false} style={{ padding: 20 }}>
      <div style={{ fontSize: 15, fontWeight: 700, color: C.gray800, marginBottom: 10 }}>Mapa de Dependências</div>
      <svg viewBox="0 0 600 330" style={{ width: '100%', display: 'block' }}>
        <defs>
          <marker id="arrowG" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10z" fill={C.gray300} /></marker>
          <marker id="arrowR" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10z" fill={C.danger} /></marker>
        </defs>
        {edges.map((e, i) => {
          const f = nodeMap[e.from], t = nodeMap[e.to];
          return <line key={i} x1={f.x} y1={f.y + 16} x2={t.x} y2={t.y - 16} stroke={e.degraded ? C.danger : C.gray300} strokeWidth={e.degraded ? 2 : 1.5} markerEnd={e.degraded ? 'url(#arrowR)' : 'url(#arrowG)'} strokeDasharray={e.degraded ? '4 3' : 'none'} />;
        })}
        {nodes.map(n => {
          const svc = SERVICES.find(s => s.name === n.id || s.name.startsWith(n.id));
          const col = svc ? statusDot(svc.status) : C.gray400;
          return (
            <g key={n.id}>
              <rect x={n.x - 52} y={n.y - 14} width={104} height={28} rx={6} fill={C.white} stroke={col} strokeWidth={1.5} />
              <circle cx={n.x - 38} cy={n.y} r={4} fill={col} />
              <text x={n.x - 28} y={n.y + 4} fontSize="10" fontWeight="600" fill={C.gray800} fontFamily={T.sans}>{n.id}</text>
            </g>
          );
        })}
      </svg>
    </Card>
  );
}

function AdminOverview() {
  return (
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: C.gray900, marginBottom: 20 }}>System Overview — MeliSim</h1>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 20 }}>
        <MetricCard label="Requests/min" value="456" sub="Total across services" trend={5} color={C.action} />
        <MetricCard label="Error Rate" value="0.42%" sub="Last 5 min" trend={-12} color={C.success} />
        <MetricCard label="Kafka Events/sec" value="2.85" sub="6 topics" trend={3} color={C.blue} />
        <MetricCard label="Outbox PENDING" value="1" sub="ob-1003" trend={0} color={C.warning} />
      </div>

      <div style={{ fontSize: 12, fontWeight: 700, color: C.gray500, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>Services</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 24 }}>
        {SERVICES.map(s => <ServiceTile key={s.name} svc={s} />)}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
        <DependencyMap />
        <Card hover={false} style={{ padding: 20 }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: C.gray800, marginBottom: 14 }}>Incidentes / Deploys — 24h</div>
          {[
            { time: '14:22', type: 'deploy', text: 'payments-service v1.1.3 deployed', color: C.action },
            { time: '12:05', type: 'incident', text: 'payments-service p95 > 2s (external gateway timeout)', color: C.warning },
            { time: '09:30', type: 'deploy', text: 'products-service v1.5.1 deployed', color: C.action },
            { time: '08:12', type: 'incident', text: 'outbox ob-1004 FAILED after 10 attempts', color: C.danger },
            { time: '03:00', type: 'deploy', text: 'api-gateway v1.4.2 deployed', color: C.action },
          ].map((ev, i) => (
            <div key={i} style={{ display: 'flex', gap: 10, padding: '8px 0', borderBottom: i < 4 ? `1px solid ${C.gray100}` : 'none' }}>
              <span style={{ fontSize: 11, color: C.gray400, width: 40, flexShrink: 0, fontFamily: T.mono }}>{ev.time}</span>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: ev.color, marginTop: 4, flexShrink: 0 }}></div>
              <span style={{ fontSize: 13, color: C.gray700 }}>{ev.text}</span>
            </div>
          ))}
        </Card>
      </div>
    </div>
  );
}

function AdminServices() {
  const [selected, setSelected] = React.useState(null);
  const [tab, setTab] = React.useState('metrics');
  const svc = selected ? SERVICES.find(s => s.name === selected) : null;

  if (svc) {
    const sparkData = Array.from({ length: 30 }, () => Math.round(svc.rps * (0.5 + Math.random())));
    const latData = Array.from({ length: 30 }, () => Math.round(svc.p95 * (0.4 + Math.random() * 1.2)));
    return (
      <div>
        <div onClick={() => setSelected(null)} style={{ fontSize: 13, color: C.action, cursor: 'pointer', marginBottom: 14 }}>← Back to services</div>
        <Card hover={false} style={{ padding: 20, marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: statusDot(svc.status) }}></div>
            <h2 style={{ fontSize: 20, fontWeight: 700 }}>{svc.name}</h2>
            <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 3, background: langColors[svc.lang], color: '#fff', fontWeight: 700 }}>{svc.lang}</span>
            <span style={{ fontSize: 12, color: C.gray400, marginLeft: 'auto' }}>v{svc.version} • :{svc.port}</span>
          </div>
          <div style={{ display: 'flex', gap: 0, borderBottom: `1px solid ${C.gray100}` }}>
            {['metrics', 'traces', 'logs', 'config'].map(t => (
              <div key={t} onClick={() => setTab(t)} style={{ padding: '8px 16px', fontSize: 13, fontWeight: tab === t ? 700 : 400, color: tab === t ? C.blue : C.gray500, borderBottom: tab === t ? `2px solid ${C.yellow}` : '2px solid transparent', cursor: 'pointer', textTransform: 'capitalize', marginBottom: -1 }}>{t}</div>
            ))}
          </div>
        </Card>

        {tab === 'metrics' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            {[
              { label: 'Requests/sec', data: sparkData, color: C.action, unit: 'RPS' },
              { label: 'Latency p95', data: latData, color: svc.p95 > 200 ? C.danger : C.warning, unit: 'ms' },
              { label: 'Error Rate', data: Array.from({ length: 30 }, () => +(Math.random() * 2).toFixed(2)), color: C.danger, unit: '%' },
              { label: 'CPU / Memory', data: Array.from({ length: 30 }, () => 20 + Math.random() * 40), color: C.blue, unit: '%' },
            ].map(m => (
              <Card key={m.label} hover={false} style={{ padding: 16 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: C.gray600, marginBottom: 8 }}>{m.label}</div>
                <Sparkline data={m.data} color={m.color} width={280} height={60} />
                <div style={{ fontSize: 22, fontWeight: 800, color: C.gray900, marginTop: 6 }}>{m.data[m.data.length - 1].toFixed(m.unit === '%' ? 1 : 0)} <span style={{ fontSize: 12, color: C.gray400 }}>{m.unit}</span></div>
              </Card>
            ))}
          </div>
        )}

        {tab === 'traces' && (
          <Card hover={false} style={{ padding: 0, overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead><tr style={{ background: C.gray50 }}>
                {['Trace ID', 'Duration', 'Spans', 'Status', 'Timestamp'].map(h => <th key={h} style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 700, color: C.gray500, fontSize: 11, textTransform: 'uppercase' }}>{h}</th>)}
              </tr></thead>
              <tbody>
                {Array.from({ length: 10 }, (_, i) => {
                  const dur = Math.round(svc.p95 * (0.3 + Math.random() * 1.5));
                  const ok = dur < svc.p95 * 1.5;
                  return (
                    <tr key={i} style={{ borderBottom: `1px solid ${C.gray100}` }}>
                      <td style={{ padding: '8px 14px', fontFamily: T.mono, fontSize: 11, color: C.action }}>{`${svc.name.slice(0, 3)}${(1000 + i).toString(16)}`}</td>
                      <td style={{ padding: '8px 14px', fontWeight: 600, color: ok ? C.gray800 : C.danger }}>{dur}ms</td>
                      <td style={{ padding: '8px 14px' }}>{2 + Math.floor(Math.random() * 5)}</td>
                      <td style={{ padding: '8px 14px' }}><Badge color={ok ? C.success : C.danger} bg={ok ? C.successBg : C.dangerBg}>{ok ? 'OK' : 'SLOW'}</Badge></td>
                      <td style={{ padding: '8px 14px', color: C.gray500, fontSize: 12 }}>30/04 {9 + Math.floor(Math.random() * 8)}:{String(Math.floor(Math.random() * 60)).padStart(2, '0')}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>
        )}

        {tab === 'logs' && (
          <div style={{ background: '#1A1A1A', borderRadius: 6, padding: 16, fontFamily: T.mono, fontSize: 12, lineHeight: 1.8, maxHeight: 400, overflow: 'auto' }}>
            {Array.from({ length: 20 }, (_, i) => {
              const levels = ['INFO', 'INFO', 'INFO', 'WARN', 'ERROR'];
              const lv = levels[Math.floor(Math.random() * levels.length)];
              const colors = { INFO: '#4EC9B0', WARN: '#FFD700', ERROR: '#F23D4F' };
              const msgs = [
                `GET /api/${svc.name.replace('-service', '')} 200 ${Math.round(svc.p95 * Math.random())}ms`,
                `POST /api/${svc.name.replace('-service', '')} 201 ${Math.round(svc.p95 * 0.8)}ms`,
                `Health check passed`,
                `Connection pool: 8/20 active`,
                `Kafka consumer lag: 0`,
              ];
              return (
                <div key={i}>
                  <span style={{ color: '#666' }}>14:{String(22 + Math.floor(i / 3)).padStart(2, '0')}:{String(i * 3).padStart(2, '0')}</span>
                  {' '}<span style={{ color: colors[lv], fontWeight: 600 }}>[{lv}]</span>
                  {' '}<span style={{ color: '#E5E5E5' }}>{msgs[i % msgs.length]}</span>
                </div>
              );
            })}
          </div>
        )}

        {tab === 'config' && (
          <Card hover={false} style={{ padding: 20 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: C.gray600, marginBottom: 14 }}>Environment Variables</div>
            <table style={{ width: '100%', fontSize: 13 }}><tbody>
              {[
                ['PORT', String(svc.port)], ['DATABASE_URL', '••••••••••••••••'],
                ['KAFKA_BROKERS', 'kafka:9092'], ['LOG_LEVEL', 'info'],
                ['REDIS_URL', '••••••••••••••••'], ['FEATURE_NEW_CHECKOUT', 'true'],
              ].map(([k, v]) => (
                <tr key={k} style={{ borderBottom: `1px solid ${C.gray100}` }}>
                  <td style={{ padding: '8px 0', fontFamily: T.mono, color: C.gray600, width: '40%' }}>{k}</td>
                  <td style={{ padding: '8px 0', fontFamily: T.mono, color: v.includes('•') ? C.gray400 : C.gray800 }}>{v}</td>
                </tr>
              ))}
            </tbody></table>
          </Card>
        )}
      </div>
    );
  }

  return (
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: C.gray900, marginBottom: 20 }}>Services</h1>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        {SERVICES.map(s => (
          <div key={s.name} onClick={() => setSelected(s.name)} style={{ cursor: 'pointer' }}>
            <ServiceTile svc={s} />
          </div>
        ))}
      </div>
    </div>
  );
}

function AdminOutbox() {
  const pending = OUTBOX.filter(o => o.status === 'PENDING').length;
  const sent = OUTBOX.filter(o => o.status === 'SENT').length;
  const failed = OUTBOX.filter(o => o.status === 'FAILED').length;

  return (
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: C.gray900, marginBottom: 20 }}>Outbox Monitor</h1>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, marginBottom: 20 }}>
        <MetricCard label="PENDING" value={String(pending)} color={C.warning} />
        <MetricCard label="SENT" value={String(sent)} color={C.success} />
        <MetricCard label="FAILED" value={String(failed)} color={C.danger} />
      </div>
      <Card hover={false} style={{ overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead><tr style={{ background: C.gray50 }}>
            {['ID', 'Event', 'Order', 'Status', 'Attempts', 'Created', 'Sent', ''].map(h => (
              <th key={h} style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 700, color: C.gray500, fontSize: 10, textTransform: 'uppercase' }}>{h}</th>
            ))}
          </tr></thead>
          <tbody>
            {OUTBOX.map((o, i) => {
              const sc = { SENT: C.success, PENDING: C.warning, FAILED: C.danger }[o.status];
              return (
                <tr key={o.id} style={{ borderBottom: `1px solid ${C.gray100}`, background: i % 2 === 1 ? C.gray50 : C.white }}>
                  <td style={{ padding: '8px 12px', fontFamily: T.mono, fontSize: 11 }}>{o.id}</td>
                  <td style={{ padding: '8px 12px' }}>{o.event}</td>
                  <td style={{ padding: '8px 12px', fontFamily: T.mono }}>{o.orderId}</td>
                  <td style={{ padding: '8px 12px' }}><Badge color={sc} bg={sc + '18'}>{o.status}</Badge></td>
                  <td style={{ padding: '8px 12px', fontWeight: o.attempts > 3 ? 700 : 400, color: o.attempts > 3 ? C.danger : C.gray700 }}>{o.attempts}</td>
                  <td style={{ padding: '8px 12px', color: C.gray500, fontSize: 11 }}>{o.created}</td>
                  <td style={{ padding: '8px 12px', color: C.gray500, fontSize: 11 }}>{o.sent || '—'}</td>
                  <td style={{ padding: '8px 12px' }}>
                    {o.status === 'FAILED' && <button style={{ padding: '3px 8px', fontSize: 10, fontWeight: 700, background: C.dangerBg, color: C.danger, border: 'none', borderRadius: 3, cursor: 'pointer' }}>Replay</button>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

function AdminDLQ() {
  const [selected, setSelected] = React.useState(null);
  const dlqTopics = [...new Set(DLQ.map(d => d.topic))].map(t => ({ name: t, count: DLQ.filter(d => d.topic === t).length }));

  return (
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: C.gray900, marginBottom: 20 }}>Dead Letter Queue</h1>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 20 }}>
        {dlqTopics.map(t => (
          <Card key={t.name} style={{ padding: 16, cursor: 'pointer', border: selected === t.name ? `2px solid ${C.danger}` : '2px solid transparent' }}>
            <div onClick={() => setSelected(t.name)}>
              <div style={{ fontSize: 13, fontWeight: 700, color: C.gray800, fontFamily: T.mono }}>{t.name}</div>
              <div style={{ fontSize: 24, fontWeight: 800, color: C.danger, marginTop: 4 }}>{t.count} <span style={{ fontSize: 12, fontWeight: 400, color: C.gray400 }}>msg</span></div>
            </div>
          </Card>
        ))}
      </div>
      {selected && (
        <Card hover={false} style={{ overflow: 'hidden' }}>
          <div style={{ padding: '14px 20px', fontWeight: 700, borderBottom: `1px solid ${C.gray100}`, fontSize: 14 }}>{selected}</div>
          {DLQ.filter(d => d.topic === selected).map(d => (
            <div key={d.id} style={{ padding: '14px 20px', borderBottom: `1px solid ${C.gray100}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <span style={{ fontFamily: T.mono, fontSize: 11, color: C.gray500 }}>offset:{d.offset}</span>
                <span style={{ fontSize: 11, color: C.gray400 }}>{d.ts}</span>
              </div>
              <div style={{ fontSize: 13, color: C.danger, fontWeight: 600, marginBottom: 6 }}>{d.error}</div>
              <pre style={{ fontSize: 11, background: '#1A1A1A', color: '#E5E5E5', padding: 10, borderRadius: 4, overflow: 'auto' }}>{d.payload}</pre>
              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                <button style={{ padding: '4px 10px', fontSize: 11, fontWeight: 700, background: C.warningBg, color: '#b37800', border: 'none', borderRadius: 3, cursor: 'pointer' }}>Replay original</button>
                <button style={{ padding: '4px 10px', fontSize: 11, fontWeight: 700, background: C.gray100, color: C.gray600, border: 'none', borderRadius: 3, cursor: 'pointer' }}>Discard</button>
              </div>
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}

function AdminKafka() {
  const [expanded, setExpanded] = React.useState(null);
  return (
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: C.gray900, marginBottom: 20 }}>Kafka Topics</h1>
      <Card hover={false} style={{ overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead><tr style={{ background: C.gray50 }}>
            {['Topic', 'Partitions', 'Produced/sec', 'Consumed/sec', 'Consumer Lag', 'DLQ'].map(h => (
              <th key={h} style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 700, color: C.gray500, fontSize: 11, textTransform: 'uppercase' }}>{h}</th>
            ))}
          </tr></thead>
          <tbody>
            {KAFKA_TOPICS.map((t, i) => {
              const lagColor = t.lag > 10000 ? C.danger : t.lag > 1000 ? C.warning : C.success;
              const dlqCount = DLQ.filter(d => d.topic === t.dlq).length;
              return (
                <tr key={t.name} style={{ borderBottom: `1px solid ${C.gray100}`, background: i % 2 === 1 ? C.gray50 : C.white, cursor: 'pointer' }} onClick={() => setExpanded(expanded === t.name ? null : t.name)}>
                  <td style={{ padding: '10px 14px', fontFamily: T.mono, fontWeight: 600, color: C.gray800 }}>{t.name}</td>
                  <td style={{ padding: '10px 14px' }}>{t.partitions}</td>
                  <td style={{ padding: '10px 14px' }}>{t.msgs_per_sec}</td>
                  <td style={{ padding: '10px 14px' }}>{(t.msgs_per_sec * 0.95).toFixed(2)}</td>
                  <td style={{ padding: '10px 14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{ width: 60, height: 6, background: C.gray100, borderRadius: 3, overflow: 'hidden' }}>
                        <div style={{ width: `${Math.min(100, (t.lag / 100) * 100)}%`, height: '100%', background: lagColor, borderRadius: 3 }}></div>
                      </div>
                      <span style={{ fontSize: 12, color: lagColor, fontWeight: 600 }}>{t.lag}</span>
                    </div>
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    {dlqCount > 0 ? <Badge color={C.danger} bg={C.dangerBg}>{dlqCount}</Badge> : <span style={{ color: C.gray400 }}>—</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

Object.assign(window, { AdminOverview, AdminServices, AdminOutbox, AdminDLQ, AdminKafka });
