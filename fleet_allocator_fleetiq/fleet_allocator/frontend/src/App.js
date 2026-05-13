import React, { useState, useEffect, useCallback } from 'react';
import { MapContainer, TileLayer, CircleMarker, Polyline, Popup, Tooltip } from 'react-leaflet';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RTooltip,
  Legend, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer
} from 'recharts';
import axios from 'axios';
import 'leaflet/dist/leaflet.css';
import './App.css';

const API = 'http://localhost:8000';

// ── Colour palette ─────────────────────────────────────────────────────────
const ALGO_COLORS = { greedy: '#f59e0b', hungarian: '#3b82f6', composite: '#10b981' };
const PRIORITY_COLOR = { P1: '#ef4444', P2: '#f97316', P3: '#6b7280' };
const NODE_TYPE_COLOR = {
  mine: '#92400e', plant: '#1d4ed8', warehouse: '#7c3aed',
  port: '#0e7490', railyard: '#065f46', customer: '#be185d',
};
const RESOURCE_COLOR = {
  FIE: '#3b82f6', LC: '#10b981', WS: '#f59e0b', QA: '#ef4444', TP: '#8b5cf6',
};

function Badge({ label, color }) {
  return (
    <span style={{
      background: color + '22', color, border: `1px solid ${color}44`,
      padding: '2px 8px', borderRadius: 12, fontSize: 11, fontWeight: 600,
    }}>
      {label}
    </span>
  );
}

function MetricCard({ label, value, sub, color = '#3b82f6' }) {
  return (
    <div className="metric-card" style={{ borderTop: `3px solid ${color}` }}>
      <div className="metric-value" style={{ color }}>{value}</div>
      <div className="metric-label">{label}</div>
      {sub && <div className="metric-sub">{sub}</div>}
    </div>
  );
}

function SectionHeader({ title, icon }) {
  return <h2 className="section-header">{icon} {title}</h2>;
}

// ── Map Panel ──────────────────────────────────────────────────────────────
function MapPanel({ nodes, resources, requests, assignments, showLines }) {
  const center = [21.5, 85.5];

  const assignedPairs = assignments.map(a => {
    const res = resources.find(r => r.id === a.resource_id);
    const req = requests.find(r => r.id === a.request_id);
    return res && req ? { res, req, a } : null;
  }).filter(Boolean);

  return (
    <MapContainer center={center} zoom={6} style={{ height: 520, borderRadius: 12, zIndex: 0 }}>
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
      />

      {/* Supply chain nodes */}
      {nodes.map(n => (
        <CircleMarker
          key={n.id}
          center={[n.lat, n.lon]}
          radius={10}
          pathOptions={{ color: NODE_TYPE_COLOR[n.type] || '#666', fillColor: NODE_TYPE_COLOR[n.type] || '#666', fillOpacity: 0.8 }}
        >
          <Tooltip permanent={false}>{n.name}</Tooltip>
          <Popup><b>{n.name}</b><br />Type: {n.type}<br />ID: {n.id}</Popup>
        </CircleMarker>
      ))}

      {/* Resources */}
      {resources.map(r => (
        <CircleMarker
          key={r.id}
          center={[r.lat, r.lon]}
          radius={5}
          pathOptions={{ color: RESOURCE_COLOR[r.type] || '#888', fillColor: RESOURCE_COLOR[r.type], fillOpacity: 0.9 }}
        >
          <Popup>
            <b>{r.name}</b><br />
            Type: {r.type_label}<br />
            Certs: {r.certifications.join(', ') || 'None'}<br />
            Cost: ₹{r.cost_per_km}/km
          </Popup>
        </CircleMarker>
      ))}

      {/* Assignment lines */}
      {showLines && assignedPairs.map(({ res, req, a }) => (
        <Polyline
          key={a.id}
          positions={[[res.lat, res.lon], [req.lat, req.lon]]}
          pathOptions={{
            color: PRIORITY_COLOR[a.request_priority] || '#999',
            weight: a.request_priority === 'P1' ? 2.5 : 1.5,
            opacity: 0.65,
            dashArray: a.request_priority === 'P3' ? '6 4' : undefined,
          }}
        >
          <Popup>
            <b>{a.resource_name}</b> → {a.node_name}<br />
            Priority: {a.request_priority} | Dist: {a.travel_distance_km} km<br />
            Cost: ₹{a.travel_cost_inr}
          </Popup>
        </Polyline>
      ))}
    </MapContainer>
  );
}

// ── Algorithm Comparison Chart ─────────────────────────────────────────────
function ComparisonPanel({ compareData }) {
  if (!compareData) return <div className="empty-state">Run "Compare All" to see algorithm comparison.</div>;

  const algos = ['greedy', 'hungarian', 'composite'];
  const metrics = ['assignment_rate', 'total_distance_km', 'p1_coverage_pct', 'workload_gini', 'cost_per_assignment'];
  const labels = {
    assignment_rate: 'Assignment %',
    total_distance_km: 'Total Dist (km)',
    p1_coverage_pct: 'P1 Coverage %',
    workload_gini: 'Gini (lower=better)',
    cost_per_assignment: 'Cost/Assignment ₹',
  };

  const barData = metrics.map(m => {
    const row = { metric: labels[m] };
    algos.forEach(a => { row[a] = compareData[a]?.metrics[m] ?? 0; });
    return row;
  });

  // Radar: normalise 5 key metrics per algorithm
  const radarData = [
    { axis: 'Assignment %', greedy: 0, hungarian: 0, composite: 0 },
    { axis: 'P1 Coverage', greedy: 0, hungarian: 0, composite: 0 },
    { axis: 'Efficiency',  greedy: 0, hungarian: 0, composite: 0 },
    { axis: 'Balance',     greedy: 0, hungarian: 0, composite: 0 },
    { axis: 'Speed',       greedy: 0, hungarian: 0, composite: 0 },
  ];
  algos.forEach(a => {
    const m = compareData[a]?.metrics || {};
    const rt = compareData[a]?.run_time_ms || 1;
    radarData[0][a] = m.assignment_rate || 0;
    radarData[1][a] = m.p1_coverage_pct || 0;
    radarData[2][a] = Math.max(0, 100 - (m.avg_distance_km || 0) / 20);
    radarData[3][a] = Math.max(0, 100 * (1 - (m.workload_gini || 0)));
    radarData[4][a] = Math.max(0, 100 - Math.min(rt, 100));
  });

  return (
    <div>
      <div className="compare-summary-row">
        {algos.map(a => (
          <div key={a} className="algo-summary-card" style={{ borderTop: `4px solid ${ALGO_COLORS[a]}` }}>
            <div className="algo-title" style={{ color: ALGO_COLORS[a] }}>{a.toUpperCase()}</div>
            <div className="algo-stat">Assigned: <b>{compareData[a]?.metrics.assigned}/{compareData[a]?.metrics.total_requests}</b></div>
            <div className="algo-stat">Rate: <b>{compareData[a]?.metrics.assignment_rate}%</b></div>
            <div className="algo-stat">Dist: <b>{compareData[a]?.metrics.total_distance_km} km</b></div>
            <div className="algo-stat">P1 Coverage: <b>{compareData[a]?.metrics.p1_coverage_pct}%</b></div>
            <div className="algo-stat">Gini: <b>{compareData[a]?.metrics.workload_gini}</b></div>
            <div className="algo-stat">Time: <b>{compareData[a]?.run_time_ms} ms</b></div>
          </div>
        ))}
      </div>

      <div className="charts-row">
        <div className="chart-box">
          <h4>Metric Comparison</h4>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={barData} margin={{ top: 5, right: 10, left: 10, bottom: 60 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="metric" angle={-30} textAnchor="end" interval={0} tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <RTooltip />
              <Legend />
              {algos.map(a => <Bar key={a} dataKey={a} fill={ALGO_COLORS[a]} radius={[3,3,0,0]} />)}
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-box">
          <h4>Multi-Dimensional Radar</h4>
          <ResponsiveContainer width="100%" height={280}>
            <RadarChart data={radarData}>
              <PolarGrid />
              <PolarAngleAxis dataKey="axis" tick={{ fontSize: 11 }} />
              <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 9 }} />
              {algos.map(a => (
                <Radar key={a} name={a} dataKey={a} stroke={ALGO_COLORS[a]}
                  fill={ALGO_COLORS[a]} fillOpacity={0.15} />
              ))}
              <Legend />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

// ── Assignments Table ──────────────────────────────────────────────────────
function AssignmentsTable({ assignments }) {
  const [expanded, setExpanded] = useState(null);
  if (!assignments.length) return <div className="empty-state">No assignments yet. Run an algorithm above.</div>;

  return (
    <div className="assignments-table-wrap">
      <table className="assignments-table">
        <thead>
          <tr>
            <th>Request</th>
            <th>Category</th>
            <th>Priority</th>
            <th>Resource</th>
            <th>Type</th>
            <th>Location</th>
            <th>Dist (km)</th>
            <th>Cost ₹</th>
            <th>Score</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          {assignments.map(a => (
            <React.Fragment key={a.id}>
              <tr className={`prio-${a.request_priority.toLowerCase()}`}>
                <td><code>{a.request_id}</code></td>
                <td style={{ fontSize: 12 }}>{a.request_category}</td>
                <td><Badge label={a.request_priority} color={PRIORITY_COLOR[a.request_priority]} /></td>
                <td style={{ fontSize: 12 }}>{a.resource_name}</td>
                <td><Badge label={a.resource_type} color={RESOURCE_COLOR[a.resource_type] || '#666'} /></td>
                <td style={{ fontSize: 12 }}>{a.node_name}</td>
                <td>{a.travel_distance_km}</td>
                <td>{a.travel_cost_inr}</td>
                <td>{a.score_breakdown?.total_score ?? '—'}</td>
                <td>
                  <button className="btn-link" onClick={() => setExpanded(expanded === a.id ? null : a.id)}>
                    {expanded === a.id ? '▲' : '▼'}
                  </button>
                </td>
              </tr>
              {expanded === a.id && (
                <tr className="explanation-row">
                  <td colSpan={10}>
                    <div className="explanation-box">
                      <p><b>Explanation:</b> {a.explanation}</p>
                      {a.score_breakdown && (
                        <div className="score-pills">
                          <span>Travel: <b>{a.score_breakdown.travel_score}</b></span>
                          <span>Priority: <b>{a.score_breakdown.priority_score}</b></span>
                          <span>Balance: <b>{a.score_breakdown.balance_score}</b></span>
                          <span>Cert: <b>{a.score_breakdown.cert_bonus}</b></span>
                        </div>
                      )}
                      {a.constraints_applied?.length > 0 && (
                        <p><b>Constraints applied:</b> {a.constraints_applied.join(', ')}</p>
                      )}
                      {a.alternatives_considered?.length > 0 && (
                        <div>
                          <b>Alternatives considered:</b>
                          <ul style={{ margin: '4px 0', paddingLeft: 20, fontSize: 12 }}>
                            {a.alternatives_considered.map((alt, i) => (
                              <li key={i}>
                                {alt.resource_name} — score {alt.score}
                                {alt.rejection_reason && <span style={{ color: '#ef4444' }}> (rejected: {alt.rejection_reason})</span>}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              )}
            </React.Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Main App ───────────────────────────────────────────────────────────────
export default function App() {
  const [tab, setTab] = useState('map');
  const [nodes, setNodes] = useState([]);
  const [resources, setResources] = useState([]);
  const [requests, setRequests] = useState([]);
  const [result, setResult] = useState(null);
  const [compareData, setCompareData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [algo, setAlgo] = useState('greedy');
  const [showLines, setShowLines] = useState(true);
  const [error, setError] = useState(null);
  const [backendOk, setBackendOk] = useState(null);

  // Check backend
  useEffect(() => {
    axios.get(`${API}/health`)
      .then(() => setBackendOk(true))
      .catch(() => setBackendOk(false));
  }, []);

  // Load reference data
  useEffect(() => {
    if (!backendOk) return;
    Promise.all([
      axios.get(`${API}/api/nodes`),
      axios.get(`${API}/api/resources`),
      axios.get(`${API}/api/requests`),
    ]).then(([n, r, q]) => {
      setNodes(n.data);
      setResources(r.data);
      setRequests(q.data);
    }).catch(e => setError('Failed to load data: ' + e.message));
  }, [backendOk]);

  const runAllocation = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API}/api/allocate/default/${algo}`);
      setResult(res.data);
      setTab('assignments');
    } catch (e) {
      setError('Allocation failed: ' + (e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  }, [algo]);

  const runCompare = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API}/api/allocate/default/all`);
      setCompareData(res.data);
      setTab('compare');
    } catch (e) {
      setError('Comparison failed: ' + (e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  }, []);

  const assignments = result?.assignments || [];
  const metrics = result?.metrics || {};

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="header-brand">
          <span className="logo">⚙</span>
          <div>
            <div className="app-title">FleetIQ</div>
            <div className="app-subtitle">Supply Chain Resource Allocation Engine</div>
          </div>
        </div>
        <div className="header-status">
          {backendOk === null && <span className="status-dot gray" />}
          {backendOk === true && <span className="status-dot green" />}
          {backendOk === false && <span className="status-dot red" />}
          <span style={{ fontSize: 12, color: '#94a3b8' }}>
            {backendOk === null ? 'Connecting…' : backendOk ? 'Backend OK' : 'Backend offline'}
          </span>
        </div>
      </header>

      {/* Controls */}
      <div className="controls-bar">
        <div className="controls-left">
          <label className="ctrl-label">Algorithm:</label>
          {['greedy', 'hungarian', 'composite'].map(a => (
            <button
              key={a}
              className={`btn-algo ${algo === a ? 'active' : ''}`}
              style={algo === a ? { background: ALGO_COLORS[a], color: '#fff', borderColor: ALGO_COLORS[a] } : {}}
              onClick={() => setAlgo(a)}
            >
              {a.charAt(0).toUpperCase() + a.slice(1)}
            </button>
          ))}
          <button className="btn-run" onClick={runAllocation} disabled={loading || !backendOk}>
            {loading ? '…' : '▶ Run'}
          </button>
          <button className="btn-compare" onClick={runCompare} disabled={loading || !backendOk}>
            ⚖ Compare All
          </button>
          <label className="ctrl-label" style={{ marginLeft: 16 }}>
            <input type="checkbox" checked={showLines} onChange={e => setShowLines(e.target.checked)} />
            {' '}Show lines
          </label>
        </div>
        <div className="controls-right">
          <span className="data-pill">{resources.length} Resources</span>
          <span className="data-pill">{requests.length} Requests</span>
          <span className="data-pill">{nodes.length} Nodes</span>
        </div>
      </div>

      {error && <div className="error-banner">⚠ {error}</div>}

      {/* Metrics strip */}
      {result && (
        <div className="metrics-strip">
          <MetricCard label="Assigned" value={`${metrics.assigned}/${metrics.total_requests}`} color={ALGO_COLORS[result.algorithm]} />
          <MetricCard label="Rate" value={`${metrics.assignment_rate}%`} color={ALGO_COLORS[result.algorithm]} />
          <MetricCard label="Total Distance" value={`${metrics.total_distance_km} km`} color="#6366f1" />
          <MetricCard label="Total Cost" value={`₹${metrics.total_cost_inr?.toLocaleString()}`} color="#8b5cf6" />
          <MetricCard label="P1 Coverage" value={`${metrics.p1_coverage_pct}%`} color={metrics.p1_coverage_pct === 100 ? '#10b981' : '#ef4444'} />
          <MetricCard label="Workload Gini" value={metrics.workload_gini} sub="0=equal, 1=concentrated" color="#f59e0b" />
          <MetricCard label="Run Time" value={`${result.run_time_ms} ms`} color="#6b7280" />
          <MetricCard label="Unassigned" value={metrics.unassigned} color={metrics.unassigned > 0 ? '#ef4444' : '#10b981'} />
        </div>
      )}

      {/* Tabs */}
      <div className="tabs">
        {['map', 'assignments', 'compare'].map(t => (
          <button key={t} className={`tab ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
            {t === 'map' ? '🗺 Map View' : t === 'assignments' ? '📋 Assignments' : '⚖ Algorithm Compare'}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="tab-content">
        {tab === 'map' && (
          <div>
            <SectionHeader title="Spatial View – Supply Chain Network" icon="🗺" />
            <div className="legend-row">
              <span className="legend-title">Nodes:</span>
              {Object.entries(NODE_TYPE_COLOR).map(([t, c]) => (
                <span key={t} className="legend-item"><span className="legend-dot" style={{ background: c }} />{t}</span>
              ))}
              <span className="legend-title" style={{ marginLeft: 16 }}>Resources:</span>
              {Object.entries(RESOURCE_COLOR).map(([t, c]) => (
                <span key={t} className="legend-item"><span className="legend-dot" style={{ background: c }} />{t}</span>
              ))}
              {result && <>
                <span className="legend-title" style={{ marginLeft: 16 }}>Assignments:</span>
                {Object.entries(PRIORITY_COLOR).map(([p, c]) => (
                  <span key={p} className="legend-item"><span className="legend-dot" style={{ background: c }} />{p}</span>
                ))}
              </>}
            </div>
            <MapPanel nodes={nodes} resources={resources} requests={requests}
              assignments={assignments} showLines={showLines} />
            {!result && <div className="map-hint">Run an algorithm to see assignment lines on the map.</div>}
          </div>
        )}

        {tab === 'assignments' && (
          <div>
            <SectionHeader title={`Assignments – ${result?.algorithm?.toUpperCase() || '—'}`} icon="📋" />
            <AssignmentsTable assignments={assignments} />
            {result?.unassigned_requests?.length > 0 && (
              <div className="unassigned-banner">
                ⚠ Unassigned requests ({result.unassigned_requests.length}):&nbsp;
                {result.unassigned_requests.join(', ')}
              </div>
            )}
          </div>
        )}

        {tab === 'compare' && (
          <div>
            <SectionHeader title="Algorithm Comparison" icon="⚖" />
            <ComparisonPanel compareData={compareData} />
          </div>
        )}
      </div>
    </div>
  );
}
