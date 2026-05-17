import { useState, useEffect } from 'react'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, PointElement, LineElement, ArcElement, Filler, Tooltip, Legend } from 'chart.js'
import { Bar, Line, Doughnut } from 'react-chartjs-2'
ChartJS.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, ArcElement, Filler, Tooltip, Legend)

// ── Mock data ──────────────────────────────────────────────────────────────
const DAYS7 = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
const HOURS = Array.from({length:24},(_,i)=>i)

const MOCK_VOLUME = {
  incoming: [142,189,203,176,284,98,72],
  resolved:  [121,155,180,160,241,80,61],
}
const MOCK_SENTIMENT = {
  positive: [38,42,35,40,28,50,55],
  neutral:  [35,30,38,32,34,28,30],
  negative: [27,28,27,28,38,22,15],
}
const MOCK_HOURLY = [0,0,0,0,0,0,0,0,12,48,92,74,55,38,68,85,62,40,28,18,10,5,2,0]

const CATEGORIES = [
  { name:'Payment Failure', count:312, color:'#f43f5e' },
  { name:'Login/Access',    count:198, color:'#f59e0b' },
  { name:'Performance',     count:145, color:'#7c5cfc' },
  { name:'Feature Request', count:98,  color:'#4f8ef7' },
  { name:'Billing Query',   count:87,  color:'#06b6d4' },
  { name:'Other',           count:62,  color:'#6b7280' },
]
const TOTAL_TICKETS = CATEGORIES.reduce((s,c)=>s+c.count, 0)

const AGENTS = [
  { name:'Sarah Chen',    resolved:47, handle:'2.8h', csat:4.6, breaches:0, status:'Active' },
  { name:'James Okafor',  resolved:38, handle:'3.1h', csat:4.2, breaches:1, status:'Active' },
  { name:'Maria Lopez',   resolved:35, handle:'3.5h', csat:4.4, breaches:2, status:'Active' },
  { name:'Tom Bradley',   resolved:29, handle:'4.2h', csat:3.8, breaches:4, status:'Away'   },
  { name:'Priya Nair',    resolved:26, handle:'3.9h', csat:4.0, breaches:1, status:'Active' },
  { name:'Alex Kim',      resolved:18, handle:'5.1h', csat:3.5, breaches:5, status:'Away'   },
]

const SLA_BY_CAT = [
  { name:'Payment',  safe:58, risk:28, breach:14 },
  { name:'Login',    safe:72, risk:18, breach:10 },
  { name:'Performance', safe:65, risk:22, breach:13 },
  { name:'Feature',  safe:88, risk:10, breach:2  },
  { name:'Billing',  safe:75, risk:18, breach:7  },
]

const AT_RISK_TICKETS = [
  { id:'TKT-4821', customer:'Jennifer Walsh',   type:'Payment Failure', mins:12, agent:'Sarah Chen' },
  { id:'TKT-4798', customer:'Robert Chen',      type:'Login/Access',    mins:28, agent:'James Okafor' },
  { id:'TKT-4765', customer:'Sandra O\'Connor', type:'Performance',     mins:45, agent:'Maria Lopez' },
  { id:'TKT-4739', customer:'David Park',       type:'Billing Query',   mins:67, agent:'Priya Nair' },
  { id:'TKT-4712', customer:'Emma Williams',    type:'Payment Failure', mins:89, agent:'Tom Bradley' },
]

// Heatmap data — generate realistic peaks
const HEATMAP = DAYS7.map((day, di) => {
  const isWeekend = di >= 5
  return HOURS.map(h => {
    if (isWeekend) return Math.max(0, Math.floor(Math.random()*8 - 2))
    if (h < 8 || h > 19) return 0
    const peak1 = Math.exp(-0.5*Math.pow((h-10)/1.5, 2)) * 40
    const peak2 = Math.exp(-0.5*Math.pow((h-15)/1.5, 2)) * 35
    return Math.max(0, Math.floor(peak1 + peak2 + Math.random()*8))
  })
})

// ── Helpers ────────────────────────────────────────────────────────────────
const BRAND = '#534AB7'
const BRAND_LIGHT = 'rgba(83,74,183,0.15)'
const baseOpts = { responsive:true, maintainAspectRatio:false, plugins:{legend:{labels:{color:'#6b7280',font:{size:11}},position:'bottom'}}, scales:{x:{ticks:{color:'#9ca3af',font:{size:10}},grid:{color:'rgba(0,0,0,0.05)'}},y:{ticks:{color:'#9ca3af',font:{size:10}},grid:{color:'rgba(0,0,0,0.07)'},beginAtZero:true}} }
const noLegend = { ...baseOpts, plugins:{legend:{display:false}} }

const card = { background:'#fff', border:'1px solid #e5e7eb', borderRadius:12, padding:'18px 20px', boxShadow:'0 1px 6px rgba(0,0,0,0.06)' }
const metricCard = (accent) => ({ ...card, borderLeft:`4px solid ${accent}` })

function Pill({ label, color }) {
  return <span style={{ display:'inline-block', padding:'2px 10px', borderRadius:100, background:color+'22', color, fontWeight:700, fontSize:'0.7rem', border:`1px solid ${color}44` }}>{label}</span>
}

function CountdownBadge({ mins }) {
  const color = mins < 30 ? '#ef4444' : '#f59e0b'
  const h = Math.floor(mins/60), m = mins%60
  return <span style={{ background:color+'22', color, fontWeight:700, fontSize:'0.72rem', padding:'3px 10px', borderRadius:100, border:`1px solid ${color}55` }}>{h>0?`${h}h `:''}⏱ {m}m</span>
}

// ── Tabs ───────────────────────────────────────────────────────────────────
const TABS = ['Overview','Issue Categories','Heatmap','Agent Performance','SLA Tracker']

function TabBar({ active, onChange }) {
  return (
    <div style={{ display:'flex', gap:2, background:'#f9fafb', borderBottom:'1px solid #e5e7eb', padding:'0 24px' }}>
      {TABS.map(t => (
        <button key={t} onClick={()=>onChange(t)} style={{ padding:'14px 20px', fontWeight:active===t?700:500, fontSize:'0.88rem', color:active===t?BRAND:'#6b7280', background:'transparent', border:'none', borderBottom:active===t?`2px solid ${BRAND}`:'2px solid transparent', cursor:'pointer', transition:'all 0.15s', marginBottom:-1 }}>{t}</button>
      ))}
    </div>
  )
}

// ── Tab 1: Overview ────────────────────────────────────────────────────────
function Overview() {
  const metrics = [
    { label:'Tickets Today', value:'284', change:'↑ 23%', acc:'#534AB7', dir:'up' },
    { label:'Avg Resolution', value:'3.4h', change:'↓ 12%', acc:'#10b981', dir:'down' },
    { label:'CSAT Score', value:'74%', change:'↓ 6pts', acc:'#f59e0b', dir:'bad' },
    { label:'SLA Breach Risk', value:'18', change:'↑ 4 last hour', acc:'#ef4444', dir:'bad' },
  ]
  return (
    <div>
      <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:16, marginBottom:24 }}>
        {metrics.map(m => (
          <div key={m.label} style={metricCard(m.acc)}>
            <div style={{ fontSize:'0.75rem', color:'#9ca3af', fontWeight:600, marginBottom:6, textTransform:'uppercase', letterSpacing:'0.05em' }}>{m.label}</div>
            <div style={{ fontSize:'2rem', fontWeight:900, color:'#111827', lineHeight:1 }}>{m.value}</div>
            <div style={{ fontSize:'0.75rem', marginTop:6, color: m.dir==='down'?'#10b981':m.dir==='up'?BRAND:'#ef4444', fontWeight:600 }}>{m.change}</div>
          </div>
        ))}
      </div>
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:16, marginBottom:16 }}>
        <div style={card}>
          <div style={{ fontWeight:700, fontSize:'0.82rem', color:'#374151', marginBottom:12 }}>📊 Ticket Volume — 7 Days</div>
          <div style={{ height:200 }}>
            <Bar data={{ labels:DAYS7, datasets:[{ label:'Incoming', data:MOCK_VOLUME.incoming, backgroundColor:'rgba(83,74,183,0.7)', borderRadius:4 },{ label:'Resolved', data:MOCK_VOLUME.resolved, backgroundColor:'rgba(16,185,129,0.7)', borderRadius:4 }] }} options={baseOpts} />
          </div>
        </div>
        <div style={card}>
          <div style={{ fontWeight:700, fontSize:'0.82rem', color:'#374151', marginBottom:12 }}>😊 Sentiment Trend — 7 Days</div>
          <div style={{ height:200 }}>
            <Line data={{ labels:DAYS7, datasets:[{ label:'Positive', data:MOCK_SENTIMENT.positive, fill:true, backgroundColor:'rgba(16,185,129,0.15)', borderColor:'#10b981', tension:0.4 },{ label:'Neutral', data:MOCK_SENTIMENT.neutral, fill:true, backgroundColor:'rgba(156,163,175,0.12)', borderColor:'#9ca3af', tension:0.4 },{ label:'Negative', data:MOCK_SENTIMENT.negative, fill:true, backgroundColor:'rgba(239,68,68,0.12)', borderColor:'#ef4444', tension:0.4 }] }} options={baseOpts} />
          </div>
        </div>
      </div>
      <div style={card}>
        <div style={{ fontWeight:700, fontSize:'0.82rem', color:'#374151', marginBottom:12 }}>⏰ Hourly Inflow Today</div>
        <div style={{ height:170 }}>
          <Line data={{ labels:HOURS.map(h=>`${h}:00`), datasets:[{ label:'Tickets', data:MOCK_HOURLY, fill:true, backgroundColor:BRAND_LIGHT, borderColor:BRAND, borderWidth:2, tension:0.4, pointRadius:2 }] }} options={noLegend} />
        </div>
      </div>
    </div>
  )
}

// ── Tab 2: Issue Categories ─────────────────────────────────────────────────
function IssueCategories() {
  return (
    <div>
      <div style={{ background:'#fef2f2', border:'1px solid #fecaca', borderRadius:10, padding:'12px 16px', marginBottom:20, display:'flex', gap:12, alignItems:'center' }}>
        <span style={{ fontSize:'1.2rem' }}>🚨</span>
        <div>
          <div style={{ fontWeight:700, color:'#b91c1c', fontSize:'0.88rem' }}>Focus Area: Payment Failure</div>
          <div style={{ fontSize:'0.8rem', color:'#dc2626', marginTop:2 }}>Payment Failure accounts for 35% of all tickets this week — this is above threshold and requires immediate team attention.</div>
        </div>
      </div>
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:16 }}>
        <div style={card}>
          <div style={{ fontWeight:700, fontSize:'0.82rem', color:'#374151', marginBottom:14 }}>Ticket Volume by Category</div>
          <div style={{ height:260 }}>
            <Bar data={{ labels:CATEGORIES.map(c=>c.name), datasets:[{ data:CATEGORIES.map(c=>c.count), backgroundColor:CATEGORIES.map(c=>c.color+'cc'), borderColor:CATEGORIES.map(c=>c.color), borderWidth:1, borderRadius:5 }] }} options={{ ...noLegend, indexAxis:'y', scales:{ x:{ticks:{color:'#9ca3af',font:{size:10}},grid:{color:'rgba(0,0,0,0.05)'}}, y:{ticks:{color:'#374151',font:{size:11,weight:'500'}},grid:{display:false}} } }} />
          </div>
        </div>
        <div style={card}>
          <div style={{ fontWeight:700, fontSize:'0.82rem', color:'#374151', marginBottom:14 }}>Share of Total Tickets</div>
          <div style={{ height:260 }}>
            <Doughnut data={{ labels:CATEGORIES.map(c=>`${c.name} (${Math.round(c.count/TOTAL_TICKETS*100)}%)`), datasets:[{ data:CATEGORIES.map(c=>c.count), backgroundColor:CATEGORIES.map(c=>c.color+'cc'), borderColor:CATEGORIES.map(c=>c.color), borderWidth:1 }] }} options={{ responsive:true, maintainAspectRatio:false, plugins:{ legend:{ position:'bottom', labels:{color:'#6b7280',font:{size:10},padding:10,boxWidth:10} } }, cutout:'60%' }} />
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Tab 3: Heatmap ─────────────────────────────────────────────────────────
function Heatmap() {
  const maxVal = Math.max(...HEATMAP.flat())
  const colLabels = ['12am','','','3am','','','6am','','','9am','','','12pm','','','3pm','','','6pm','','','9pm','','']

  const cellColor = (v) => {
    if (v === 0) return '#f9fafb'
    const t = v / maxVal
    const r = Math.round(83 + (83-83)*t)
    const g = Math.round(74 - 74*t)
    const b = Math.round(183 + (183-183)*t)
    // purple scale: light to dark
    const alpha = 0.1 + t * 0.9
    return `rgba(83,74,183,${alpha.toFixed(2)})`
  }

  return (
    <div style={card}>
      <div style={{ fontWeight:700, fontSize:'0.88rem', color:'#374151', marginBottom:16 }}>🗓️ Issue Volume Heatmap — 7 Days × 24 Hours</div>
      <div style={{ overflowX:'auto' }}>
        <div style={{ display:'grid', gridTemplateColumns:'48px repeat(24,1fr)', gap:2, minWidth:700 }}>
          <div />
          {colLabels.map((l,i) => <div key={i} style={{ fontSize:'0.58rem', color:'#9ca3af', textAlign:'center', paddingBottom:3 }}>{l}</div>)}
          {HEATMAP.map((row, di) => (
            <>
              <div key={`lbl-${di}`} style={{ fontSize:'0.72rem', color:'#374151', fontWeight:600, display:'flex', alignItems:'center', justifyContent:'flex-end', paddingRight:6 }}>{DAYS7[di]}</div>
              {row.map((val, hi) => (
                <div key={hi} title={`${DAYS7[di]} ${hi}:00 — ${val} tickets`} style={{ height:24, borderRadius:3, background:cellColor(val), transition:'transform 0.1s', cursor:'pointer' }}
                  onMouseEnter={e=>e.target.style.transform='scale(1.4)'}
                  onMouseLeave={e=>e.target.style.transform='scale(1)'}
                />
              ))}
            </>
          ))}
        </div>
      </div>
      {/* Legend */}
      <div style={{ display:'flex', alignItems:'center', gap:8, marginTop:14, fontSize:'0.72rem', color:'#9ca3af' }}>
        <span>Low</span>
        <div style={{ display:'flex', gap:2 }}>
          {[0.1,0.25,0.4,0.55,0.7,0.85,1.0].map((a,i) => <div key={i} style={{ width:20, height:12, borderRadius:2, background:`rgba(83,74,183,${a})` }} />)}
        </div>
        <span>High</span>
      </div>
    </div>
  )
}

// ── Tab 4: Agent Performance ───────────────────────────────────────────────
function AgentPerformance() {
  const sorted = [...AGENTS].sort((a,b)=>b.resolved-a.resolved)
  const topAgent = sorted[0].name

  return (
    <div>
      <div style={{ ...card, marginBottom:16 }}>
        <div style={{ fontWeight:700, fontSize:'0.88rem', color:'#374151', marginBottom:14 }}>🏆 Agent Leaderboard</div>
        <table style={{ width:'100%', borderCollapse:'collapse', fontSize:'0.85rem' }}>
          <thead>
            <tr style={{ borderBottom:'2px solid #e5e7eb' }}>
              {['Agent','Resolved','Avg Handle Time','CSAT','SLA Breaches','Status'].map(h => (
                <th key={h} style={{ padding:'8px 12px', textAlign:'left', fontSize:'0.72rem', fontWeight:700, color:'#6b7280', textTransform:'uppercase', letterSpacing:'0.05em' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {AGENTS.map((a,i) => {
              const isTop = a.name === topAgent
              const isBad = a.breaches > 3
              const bg = isTop ? '#f0fdf4' : isBad ? '#fef2f2' : i%2===0 ? '#fff' : '#f9fafb'
              return (
                <tr key={a.name} style={{ background:bg, borderBottom:'1px solid #e5e7eb' }}>
                  <td style={{ padding:'10px 12px', fontWeight:600, color:isTop?'#15803d':isBad?'#b91c1c':'#111827' }}>
                    {isTop && '🥇 '}{a.name}
                  </td>
                  <td style={{ padding:'10px 12px', fontFamily:'monospace', color:isTop?'#15803d':'#111827', fontWeight:isTop?700:400 }}>{a.resolved}</td>
                  <td style={{ padding:'10px 12px', color:'#374151' }}>{a.handle}</td>
                  <td style={{ padding:'10px 12px' }}>
                    <span style={{ color: a.csat>=4.3?'#15803d':a.csat>=3.8?'#b45309':'#b91c1c', fontWeight:700 }}>⭐ {a.csat}</span>
                  </td>
                  <td style={{ padding:'10px 12px' }}>
                    <span style={{ color: a.breaches>3?'#b91c1c':a.breaches>0?'#b45309':'#15803d', fontWeight:700 }}>{a.breaches}</span>
                  </td>
                  <td style={{ padding:'10px 12px' }}>
                    <Pill label={a.status} color={a.status==='Active'?'#10b981':'#9ca3af'} />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <div style={card}>
        <div style={{ fontWeight:700, fontSize:'0.82rem', color:'#374151', marginBottom:12 }}>Tickets Resolved per Agent</div>
        <div style={{ height:200 }}>
          <Bar data={{ labels:sorted.map(a=>a.name.split(' ')[0]), datasets:[{ data:sorted.map(a=>a.resolved), backgroundColor:sorted.map(a=>a.name===topAgent?'#10b981cc':a.breaches>3?'#ef4444cc':'#534AB7cc'), borderRadius:5 }] }} options={noLegend} />
        </div>
      </div>
    </div>
  )
}

// ── Tab 5: SLA Tracker ─────────────────────────────────────────────────────
function SLATracker() {
  return (
    <div>
      <div style={{ ...card, marginBottom:16 }}>
        <div style={{ fontWeight:700, fontSize:'0.88rem', color:'#374151', marginBottom:14 }}>SLA Status by Category</div>
        <div style={{ display:'flex', flexDirection:'column', gap:10 }}>
          {SLA_BY_CAT.map(c => (
            <div key={c.name} style={{ display:'flex', alignItems:'center', gap:12 }}>
              <div style={{ width:110, fontSize:'0.82rem', fontWeight:600, color:'#374151' }}>{c.name}</div>
              <div style={{ flex:1, height:28, display:'flex', borderRadius:5, overflow:'hidden' }}>
                <div title={`Safe: ${c.safe}%`} style={{ width:`${c.safe}%`, background:'#10b981', display:'flex', alignItems:'center', justifyContent:'center', fontSize:'0.7rem', color:'#fff', fontWeight:700 }}>{c.safe}%</div>
                <div title={`At Risk: ${c.risk}%`} style={{ width:`${c.risk}%`, background:'#f59e0b', display:'flex', alignItems:'center', justifyContent:'center', fontSize:'0.7rem', color:'#fff', fontWeight:700 }}>{c.risk}%</div>
                <div title={`Breached: ${c.breach}%`} style={{ width:`${c.breach}%`, background:'#ef4444', display:'flex', alignItems:'center', justifyContent:'center', fontSize:'0.7rem', color:'#fff', fontWeight:700 }}>{c.breach}%</div>
              </div>
              <div style={{ display:'flex', gap:6, fontSize:'0.68rem', color:'#9ca3af', width:130 }}>
                <span style={{color:'#10b981'}}>●</span>Safe
                <span style={{color:'#f59e0b'}}>●</span>Risk
                <span style={{color:'#ef4444'}}>●</span>Breach
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={card}>
        <div style={{ fontWeight:700, fontSize:'0.88rem', color:'#374151', marginBottom:14 }}>⚠️ Most Urgent At-Risk Tickets</div>
        <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
          {AT_RISK_TICKETS.map(t => (
            <div key={t.id} style={{ display:'flex', alignItems:'center', gap:12, padding:'10px 14px', background:'#fafafa', border:'1px solid #e5e7eb', borderRadius:9 }}>
              <div style={{ fontFamily:'monospace', fontSize:'0.8rem', color:'#534AB7', fontWeight:700, width:80 }}>{t.id}</div>
              <div style={{ flex:1 }}>
                <div style={{ fontWeight:600, fontSize:'0.86rem', color:'#111827' }}>{t.customer}</div>
                <div style={{ fontSize:'0.75rem', color:'#6b7280' }}>{t.type}</div>
              </div>
              <CountdownBadge mins={t.mins} />
              <div style={{ fontSize:'0.78rem', color:'#6b7280', width:100, textAlign:'right' }}>{t.agent}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Main export ─────────────────────────────────────────────────────────────
export default function ManagerAnalytics() {
  const [tab, setTab] = useState('Overview')
  const [tick, setTick] = useState(0)
  useEffect(() => { const t = setInterval(()=>setTick(p=>p+1), 60000); return ()=>clearInterval(t) }, [])

  return (
    <div style={{ minHeight:'100vh', background:'#f3f4f6' }}>
      {/* Header */}
      <div style={{ background:'#fff', borderBottom:'1px solid #e5e7eb', padding:'14px 28px', display:'flex', alignItems:'center', justifyContent:'space-between' }}>
        <div>
          <div style={{ fontSize:'1.2rem', fontWeight:900, color:BRAND, letterSpacing:'-0.02em' }}>📊 Manager Analytics</div>
          <div style={{ fontSize:'0.76rem', color:'#9ca3af', marginTop:2 }}>Real-time · SupportLens Intelligence · Relanto 2026</div>
        </div>
        <div style={{ display:'flex', gap:10, alignItems:'center' }}>
          <Pill label="Live" color="#10b981" />
          <span style={{ fontSize:'0.75rem', color:'#9ca3af' }}>Last refresh: just now</span>
        </div>
      </div>

      <TabBar active={tab} onChange={setTab} />

      <div style={{ padding:'24px 28px' }}>
        {tab === 'Overview' && <Overview />}
        {tab === 'Issue Categories' && <IssueCategories />}
        {tab === 'Heatmap' && <Heatmap />}
        {tab === 'Agent Performance' && <AgentPerformance />}
        {tab === 'SLA Tracker' && <SLATracker />}
      </div>
    </div>
  )
}
