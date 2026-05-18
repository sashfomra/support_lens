import { useState, useEffect } from 'react'
import { getDashboard, askManager, getClusters, getAgentStats, getHeatmap, getSLABreakdown, getCSATForecast, getManagerAlerts, dismissAlert } from '../api/client'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, ArcElement, Tooltip, Legend, Filler } from 'chart.js'
import { Line, Bar, Doughnut } from 'react-chartjs-2'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, ArcElement, Tooltip, Legend, Filler)

const COLORS = ['#4f8ef7','#7c5cfc','#10d98c','#f59e0b','#f43f5e','#06b6d4','#ec4899','#a78bfa']
const DAYS = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
const baseOpts = {
  responsive: true, maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    x: { ticks: { color: '#4a5070', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.03)' } },
    y: { ticks: { color: '#4a5070', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.03)' }, min: 0 }
  }
}

/* ── Issue Heatmap ──────────────────────────────────────── */
function IssueHeatmap({ data }) {
  const [tooltip, setTooltip] = useState(null)
  if (!data || data.length === 0) return <div className="empty" style={{padding:30}}><div>No heatmap data yet</div></div>

  const maxCount = Math.max(...data.map(d => d.count), 1)

  const getColor = (count, cat) => {
    if (count === 0) return 'rgba(255,255,255,0.03)'
    const intensity = count / maxCount
    const palettes = {
      'Billing': `rgba(244,63,94,${0.15 + intensity * 0.7})`,
      'Technical': `rgba(79,142,247,${0.15 + intensity * 0.7})`,
      'Account': `rgba(124,92,252,${0.15 + intensity * 0.7})`,
      'Performance': `rgba(245,158,11,${0.15 + intensity * 0.7})`,
      'UX': `rgba(6,182,212,${0.15 + intensity * 0.7})`,
    }
    return palettes[cat] || `rgba(16,217,140,${0.15 + intensity * 0.7})`
  }

  const grid = {}
  data.forEach(d => { grid[`${d.day}-${d.hour}`] = d })

  return (
    <div style={{ position: 'relative' }}>
      <div className="heatmap-grid">
        {/* Hour labels */}
        <div />
        {Array.from({length:24},(_,h) => (
          <div key={h} className="heatmap-hour-label">{h%6===0?`${h}h`:''}</div>
        ))}
        {/* Rows */}
        {DAYS.map((day, di) => (
          <>
            <div key={`lbl-${di}`} className="heatmap-day-label">{day}</div>
            {Array.from({length:24},(_,h) => {
              const cell = grid[`${di}-${h}`]
              const count = cell?.count || 0
              const cat = cell?.dominant_category
              return (
                <div
                  key={`${di}-${h}`}
                  className="heatmap-cell"
                  style={{ background: getColor(count, cat) }}
                  onMouseEnter={() => setTooltip({ day, h, count, cat })}
                  onMouseLeave={() => setTooltip(null)}
                />
              )
            })}
          </>
        ))}
      </div>
      {tooltip && (
        <div style={{ position:'fixed', pointerEvents:'none', background:'var(--bg5)', border:'1px solid var(--border2)', borderRadius:7, padding:'7px 11px', fontSize:'0.75rem', zIndex:1000, transform:'translate(12px,-50%)', boxShadow:'var(--shadow-card)' }}>
          <div style={{ fontWeight:600 }}>{tooltip.day} {tooltip.h}:00</div>
          <div style={{ color:'var(--text2)' }}>{tooltip.count} tickets</div>
          {tooltip.cat && <div style={{ color:'var(--blue)' }}>{tooltip.cat}</div>}
        </div>
      )}
      {/* Legend */}
      <div style={{ display:'flex', gap:14, marginTop:10, fontSize:'0.68rem', color:'var(--text3)' }}>
        <span>░ Low</span><span style={{color:'var(--text2)'}}>▒ Medium</span><span style={{color:'var(--text)'}}>█ High</span>
      </div>
    </div>
  )
}

/* ── SLA Tracker ──────────────────────────────────────── */
function SLATracker({ data }) {
  if (!data) return null
  const { totals, by_agent } = data
  const total = (totals.safe + totals.at_risk + totals.breached) || 1

  return (
    <div>
      {/* Summary pills */}
      <div style={{ display:'flex', gap:10, marginBottom:14 }}>
        <div style={{ flex:1, background:'var(--green-dim)', border:'1px solid rgba(16,217,140,0.2)', borderRadius:9, padding:'10px 14px', textAlign:'center' }}>
          <div style={{ fontSize:'1.5rem', fontWeight:800, color:'var(--green)' }}>{totals.safe}</div>
          <div style={{ fontSize:'0.72rem', color:'var(--text2)' }}>Safe</div>
        </div>
        <div style={{ flex:1, background:'var(--amber-dim)', border:'1px solid rgba(245,158,11,0.2)', borderRadius:9, padding:'10px 14px', textAlign:'center' }}>
          <div style={{ fontSize:'1.5rem', fontWeight:800, color:'var(--amber)' }}>{totals.at_risk}</div>
          <div style={{ fontSize:'0.72rem', color:'var(--text2)' }}>At Risk</div>
        </div>
        <div style={{ flex:1, background:'var(--red-dim)', border:'1px solid rgba(244,63,94,0.2)', borderRadius:9, padding:'10px 14px', textAlign:'center' }}>
          <div style={{ fontSize:'1.5rem', fontWeight:800, color:'var(--red)' }}>{totals.breached}</div>
          <div style={{ fontSize:'0.72rem', color:'var(--text2)' }}>Breached</div>
        </div>
      </div>

      {/* Per-agent stacked bar */}
      <div className="sla-bar-wrap">
        {by_agent.map((a, i) => {
          const t = a.safe + a.at_risk + a.breached || 1
          return (
            <div key={i} className="sla-agent-row">
              <div className="sla-agent-name" style={{fontSize:'0.77rem',fontWeight:500}}>{a.agent}</div>
              <div className="sla-bar-track">
                <div className="sla-seg sla-seg-safe" style={{width:`${(a.safe/t)*100}%`}} />
                <div className="sla-seg sla-seg-risk" style={{width:`${(a.at_risk/t)*100}%`}} />
                <div className="sla-seg sla-seg-breach" style={{width:`${(a.breached/t)*100}%`}} />
              </div>
              <div className="sla-total">{t}</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/* ── CSAT Forecast ──────────────────────────────────────── */
function CSATForecast({ data }) {
  if (!data) return null
  const pct = (data.forecast / 5) * 100
  const color = data.forecast >= 4 ? 'var(--green)' : data.forecast >= 3 ? 'var(--amber)' : 'var(--red)'

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
      <div style={{ textAlign:'center' }}>
        <div style={{ fontSize:'3rem', fontWeight:900, color, lineHeight:1 }}>{data.forecast}</div>
        <div style={{ fontSize:'0.8rem', color:'var(--text2)', marginTop:4 }}>/ 5.0 predicted</div>
      </div>
      <div className="progress"><div className="progress-fill" style={{ width:`${pct}%`, background: color }} /></div>
      <div style={{ display:'flex', justifyContent:'space-between', fontSize:'0.75rem', color:'var(--text3)' }}>
        {data.prev_week && <span>Last week: <strong style={{color:'var(--text2)'}}>{data.prev_week}</strong></span>}
        {data.current_actual && <span>Actual: <strong style={{color:'var(--text2)'}}>{data.current_actual}</strong></span>}
      </div>
      {data.drivers?.map((d,i) => (
        <div key={i} style={{ display:'flex', justifyContent:'space-between', fontSize:'0.75rem', padding:'5px 0', borderBottom:'1px solid var(--border)' }}>
          <span style={{color:'var(--text2)'}}>{d.label}</span>
          <span style={{color:d.impact<0?'var(--red)':'var(--green)',fontFamily:'var(--mono)',fontWeight:600}}>{d.impact>0?'+':''}{d.impact}</span>
        </div>
      ))}
    </div>
  )
}

/* ── Manager Q&A ──────────────────────────────────────── */
function QABot() {
  const QUICK = ['Why did CSAT drop?','Show SLA at-risk','Most churn risks?','Top issue today?','Busiest agent?']
  const [msgs, setMsgs] = useState([{ role:'ai', text:"Ask anything about your support data. I'll query the database and show you evidence.", time: new Date().toLocaleTimeString() }])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const send = async (q) => {
    const question = q || input.trim()
    if (!question) return
    setInput('')
    setMsgs(p => [...p, { role:'user', text:question, time:new Date().toLocaleTimeString() }])
    setLoading(true)
    try {
      const r = await askManager(question)
      const d = r.data
      let text = d.answer
      if (d.evidence_tickets?.length > 0) {
        text += '\n\n📋 Evidence:\n' + d.evidence_tickets.slice(0,3).map(t =>
          t.subject ? `• ${t.subject}` : `• ${t.agent}: ${t.open_tickets} open`
        ).join('\n')
      }
      setMsgs(p => [...p, { role:'ai', text, time:new Date().toLocaleTimeString(), chartData:d.chart_data }])
    } catch {
      setMsgs(p => [...p, { role:'ai', text:'Connection error — is the backend running?', time:new Date().toLocaleTimeString() }])
    }
    setLoading(false)
  }

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100%' }}>
      <div className="card-hd"><span className="card-hd-dot"/>Manager Q&A — Plain English Analytics</div>
      {/* Quick buttons */}
      <div style={{ display:'flex', gap:5, flexWrap:'wrap', marginBottom:12 }}>
        {QUICK.map((q,i) => (
          <button key={i} className="btn btn-ghost btn-sm" onClick={()=>send(q)} style={{fontSize:'0.72rem',padding:'4px 9px',border:'1px solid var(--border2)'}}>
            {q}
          </button>
        ))}
      </div>
      {/* Messages */}
      <div style={{ flex:1, overflowY:'auto', maxHeight:300, display:'flex', flexDirection:'column', gap:10, marginBottom:12, paddingRight:2 }}>
        {msgs.map((m,i) => (
          <div key={i} style={{ display:'flex', flexDirection:'column', alignItems:m.role==='user'?'flex-end':'flex-start' }}>
            <div className={`bubble ${m.role==='user'?'bubble-user':'bubble-ai'}`}>
              <div style={{ whiteSpace:'pre-wrap' }}>{m.text}</div>
              {m.chartData && (
                <div style={{ marginTop:10, height:110 }}>
                  <Bar data={{ labels:m.chartData.labels, datasets:[{ data:m.chartData.values, backgroundColor:COLORS.map(c=>c+'99'), borderColor:COLORS, borderWidth:1, borderRadius:4 }] }}
                    options={{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}}, scales:{x:{ticks:{color:'#8b92b8',font:{size:9}},grid:{display:false}},y:{ticks:{color:'#8b92b8',font:{size:9}},grid:{color:'rgba(255,255,255,0.04)'}}} }} />
                </div>
              )}
              <div className="bubble-time">{m.time}</div>
            </div>
          </div>
        ))}
        {loading && (
          <div style={{alignSelf:'flex-start'}}>
            <div className="bubble bubble-ai">
              <div style={{display:'flex',gap:8,alignItems:'center'}}>
                <span className="spinner" style={{width:13,height:13}}/><span style={{fontSize:'0.82rem',color:'var(--text2)'}}>Querying data…</span>
              </div>
            </div>
          </div>
        )}
      </div>
      <div style={{ display:'flex', gap:8 }}>
        <input className="input" value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>e.key==='Enter'&&!loading&&send()} placeholder="Ask a question…" disabled={loading} />
        <button className="btn btn-primary" onClick={()=>send()} disabled={loading||!input.trim()}>Send</button>
      </div>
    </div>
  )
}

/* ── Main Dashboard ──────────────────────────────────────── */
export default function ManagerDashboard() {
  const [stats, setStats] = useState(null)
  const [agents, setAgents] = useState([])
  const [clusters, setClusters] = useState([])
  const [heatmap, setHeatmap] = useState(null)
  const [sla, setSla] = useState(null)
  const [csat, setCsat] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getDashboard(), getAgentStats(), getClusters(), getHeatmap(), getSLABreakdown(), getCSATForecast()])
      .then(([s,a,c,h,sl,cs]) => { setStats(s.data); setAgents(a.data); setClusters(c.data); setHeatmap(h.data); setSla(sl.data); setCsat(cs.data) })
      .catch(console.error)
      .finally(() => setLoading(false))

    // Poll for spike alerts every 30s
    const pollAlerts = () => getManagerAlerts().then(r => setAlerts(r.data)).catch(() => {})
    pollAlerts()
    const alertTimer = setInterval(pollAlerts, 30000)
    return () => clearInterval(alertTimer)
  }, [])

  if (loading) return <div className="empty" style={{paddingTop:140}}><div className="spinner" style={{width:44,height:44,margin:'0 auto 16px'}}/><div style={{color:'var(--text2)'}}>Loading dashboard…</div></div>

  const doughnutOpts = { responsive:true, maintainAspectRatio:false, plugins:{ legend:{ position:'bottom', labels:{ color:'#8b92b8', font:{size:11}, padding:12, boxWidth:10 } } }, cutout:'62%' }

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">📊 Manager Dashboard</div>
          <div className="page-sub">Real-time team performance · Conversational data intelligence</div>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={()=>window.location.reload()}>⟳ Refresh</button>
      </div>

      <div className="page-body">
        {/* Spike Alerts */}
        {alerts.length > 0 && (
          <div style={{ marginBottom:18 }}>
            {alerts.map(a => (
              <div key={a.id} style={{ background: a.severity==='critical'?'rgba(244,63,94,0.1)':'rgba(245,158,11,0.1)', border:`1px solid ${a.severity==='critical'?'rgba(244,63,94,0.4)':'rgba(245,158,11,0.4)'}`, borderRadius:11, padding:'13px 18px', display:'flex', alignItems:'center', justifyContent:'space-between', gap:14, marginBottom:8 }}>
                <div style={{ display:'flex', alignItems:'center', gap:12 }}>
                  <span style={{ fontSize:'1.4rem' }}>{a.severity==='critical'?'🚨':'⚠️'}</span>
                  <div>
                    <div style={{ fontWeight:700, color: a.severity==='critical'?'var(--red)':'var(--amber)', fontSize:'0.9rem' }}>
                      {a.category} tickets spiked {a.spike_pct}%
                    </div>
                    <div style={{ fontSize:'0.8rem', color:'var(--text2)', marginTop:2 }}>
                      {a.count_30m} tickets in last 30 min vs {a.avg_hourly}/hr average · {new Date(a.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
                <button className="btn btn-ghost btn-sm" onClick={() => { dismissAlert(a.id); setAlerts(p => p.filter(x => x.id !== a.id)) }} style={{ flexShrink:0, fontSize:'1rem', padding:'4px 8px' }}>✕</button>
              </div>
            ))}
          </div>
        )}
        {stats && (
          <div className="stats-row">
            {[
              { icon:'🎫', val:stats.total_open, lbl:'Open Tickets', sub:`${stats.total_resolved_today} resolved today`, col:'var(--blue)', bg:'var(--bg4)' },
              { icon:'🚨', val:stats.sla_breached, lbl:'SLA Breaches', col:'var(--red)', bg:'var(--red-dim)' },
              { icon:'⚠️', val:stats.churn_risks, lbl:'Churn Risks', col:'var(--amber)', bg:'var(--amber-dim)' },
              { icon:'📈', val:stats.avg_urgency, lbl:'Avg Urgency', col:'var(--purple)', bg:'var(--purple-dim)' },
              { icon:'⭐', val:stats.avg_csat?.toFixed(1)||'N/A', lbl:'CSAT Score', sub:'Out of 5.0', col:'var(--green)', bg:'var(--green-dim)' },
            ].map((s,i) => (
              <div className="stat-card" key={i}>
                <div className="stat-card-bg" style={{ background: s.col }} />
                <div className="stat-icon" style={{ background: s.bg }}>{s.icon}</div>
                <div className="stat-val" style={{ color: s.col }}>{s.val}</div>
                <div className="stat-lbl">{s.lbl}</div>
                {s.sub && <div className="stat-chg">{s.sub}</div>}
              </div>
            ))}
          </div>
        )}

        {/* Heatmap + SLA Tracker */}
        <div className="grid-2" style={{ marginBottom:18 }}>
          <div className="card">
            <div className="card-hd"><span className="card-hd-dot" style={{background:'var(--red)'}}/>Issue Heatmap — 7 Days × 24 Hours</div>
            <IssueHeatmap data={heatmap} />
          </div>
          <div className="card">
            <div className="card-hd"><span className="card-hd-dot" style={{background:'var(--amber)'}}/>SLA Tracker — By Agent</div>
            <SLATracker data={sla} />
          </div>
        </div>

        {/* CSAT + Trend charts */}
        {stats && (
          <div className="grid-2" style={{ marginBottom:18 }}>
            <div className="card">
              <div className="card-hd"><span className="card-hd-dot" style={{background:'var(--green)'}}/>CSAT Forecast</div>
              <CSATForecast data={csat} />
            </div>
            <div className="card">
              <div className="card-hd"><span className="card-hd-dot"/>Volume Trend — 7 Days</div>
              <div style={{ height:180 }}>
                <Bar data={{ labels:stats.volume_trend.map(d=>d.date), datasets:[{ data:stats.volume_trend.map(d=>d.value), backgroundColor:'rgba(124,92,252,0.4)', borderColor:'#7c5cfc', borderWidth:1, borderRadius:5 }] }} options={baseOpts} />
              </div>
            </div>
          </div>
        )}

        {/* Doughnut charts */}
        {stats && (
          <div className="grid-2" style={{ marginBottom:18 }}>
            <div className="card">
              <div className="card-hd"><span className="card-hd-dot"/>Issues by Category</div>
              <div style={{ height:200 }}>
                <Doughnut data={{ labels:Object.keys(stats.ticket_by_category), datasets:[{ data:Object.values(stats.ticket_by_category), backgroundColor:COLORS.map(c=>c+'cc'), borderColor:COLORS, borderWidth:1 }] }} options={doughnutOpts} />
              </div>
            </div>
            <div className="card">
              <div className="card-hd"><span className="card-hd-dot" style={{background:'var(--red)'}}/>Emotion Breakdown</div>
              <div style={{ height:200 }}>
                <Doughnut data={{ labels:Object.keys(stats.ticket_by_emotion), datasets:[{ data:Object.values(stats.ticket_by_emotion), backgroundColor:['#f43f5e80','#f59e0b80','#7c5cfc80','#6b728080','#10d98c80','#f9731680'], borderColor:['#f43f5e','#f59e0b','#7c5cfc','#6b7280','#10d98c','#f97316'], borderWidth:1 }] }} options={doughnutOpts} />
              </div>
            </div>
          </div>
        )}

        {/* Issue Clusters */}
        {clusters.length > 0 && (
          <div className="card" style={{ marginBottom:18 }}>
            <div className="card-hd"><span className="card-hd-dot" style={{background:'var(--cyan)'}}/>Detected Issue Clusters</div>
            <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(260px,1fr))', gap:10 }}>
              {clusters.map(c => (
                <div key={c.id} style={{ background:'var(--bg4)', border:'1px solid var(--border2)', borderRadius:9, padding:13 }}>
                  <div style={{ display:'flex', justifyContent:'space-between', marginBottom:5 }}>
                    <span style={{ fontWeight:600, fontSize:'0.86rem' }}>{c.label}</span>
                    <span className="badge badge-blue">{c.ticket_count}</span>
                  </div>
                  {c.description && <div style={{ fontSize:'0.78rem', color:'var(--text2)', lineHeight:1.5 }}>{c.description}</div>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Agent Leaderboard */}
        {agents.length > 0 && (
          <div className="card" style={{ marginBottom:18 }}>
            <div className="card-hd"><span className="card-hd-dot" style={{background:'var(--purple)'}}/>Agent Leaderboard</div>
            <div style={{ display:'flex', flexDirection:'column', gap:5 }}>
              <div style={{ display:'grid', gridTemplateColumns:'1fr 70px 80px 75px 75px 70px', gap:10, padding:'5px 10px', fontSize:'0.63rem', fontWeight:700, color:'var(--text3)', textTransform:'uppercase', letterSpacing:'0.07em' }}>
                <span>Agent</span><span>Open</span><span>Resolved</span><span>SLA Risk</span><span>Avg Hrs</span><span>CSAT</span>
              </div>
              {agents.map((a,i) => (
                <div key={a.agent_id} style={{ display:'grid', gridTemplateColumns:'1fr 70px 80px 75px 75px 70px', gap:10, padding:'10px', background:'var(--bg4)', borderRadius:9, alignItems:'center', border:'1px solid var(--border)' }}>
                  <div style={{ display:'flex', alignItems:'center', gap:10 }}>
                    <div style={{ width:30, height:30, borderRadius:'50%', background:`linear-gradient(135deg,${COLORS[i%COLORS.length]},${COLORS[(i+3)%COLORS.length]})`, display:'flex', alignItems:'center', justifyContent:'center', color:'#fff', fontSize:'0.78rem', fontWeight:700, flexShrink:0 }}>
                      {a.agent_name.charAt(0)}
                    </div>
                    <span style={{ fontWeight:600, fontSize:'0.86rem' }}>{a.agent_name}</span>
                  </div>
                  <span style={{ fontFamily:'var(--mono)', fontSize:'0.83rem', color:a.open_tickets>8?'var(--red)':a.open_tickets>4?'var(--amber)':'var(--text)' }}>{a.open_tickets}</span>
                  <span style={{ fontFamily:'var(--mono)', fontSize:'0.83rem', color:'var(--green)' }}>{a.resolved_this_week}</span>
                  <span style={{ fontFamily:'var(--mono)', fontSize:'0.83rem', color:a.sla_at_risk>0?'var(--red)':'var(--text3)' }}>{a.sla_at_risk}</span>
                  <span style={{ fontFamily:'var(--mono)', fontSize:'0.83rem' }}>{a.avg_resolution_hours}h</span>
                  <span style={{ fontFamily:'var(--mono)', fontSize:'0.83rem', color:a.csat_avg>=4?'var(--green)':a.csat_avg>=3?'var(--amber)':'var(--red)' }}>{a.csat_avg?`⭐${a.csat_avg}`:'—'}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Q&A Bot */}
        <div className="card"><QABot /></div>
      </div>
    </>
  )
}
