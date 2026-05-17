import { useState, useEffect, useCallback } from 'react'
import { getTickets, getDraftReply, updateTicket, getTicketSuggestions } from '../api/client'
import SolutionPanel from '../components/SolutionPanel'

const EMO = { angry:'😡', frustrated:'😤', confused:'🤔', neutral:'😐', happy:'😊', worried:'😟' }
const DAYS = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']

function urgencyClass(s){ return s>=65?'badge-red':s>=35?'badge-amber':'badge-green' }
function urgencyLabel(s){ return s>=65?'🔴 HIGH':s>=35?'🟡 MED':'🟢 LOW' }

function SLATimer({ deadline, breached }) {
  const [txt, setTxt] = useState('—')
  const [cls, setCls] = useState('sla-ok')
  useEffect(() => {
    if (!deadline) return
    const update = () => {
      const diff = new Date(deadline) - new Date()
      if (diff <= 0 || breached) { setTxt('BREACH'); setCls('sla-breach'); return }
      const h = Math.floor(diff / 3600000), m = Math.floor((diff % 3600000) / 60000)
      setTxt(`${h}h ${m}m`)
      setCls(diff < 7200000 ? 'sla-warn' : 'sla-ok')
    }
    update()
    const t = setInterval(update, 10000)
    return () => clearInterval(t)
  }, [deadline, breached])
  return <span className={`sla ${cls}`}>{txt}</span>
}

function TicketModal({ ticket: t, onClose, onUpdate }) {
  const [draft, setDraft] = useState(t.ai_draft_reply || '')
  const [loading, setLoading] = useState(false)
  const [meta, setMeta] = useState(null)
  const [sugs, setSugs] = useState([])
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    getTicketSuggestions(t.id).then(r => setSugs(r.data || [])).catch(() => {})
  }, [t.id])

  const genDraft = async () => {
    setLoading(true)
    try {
      const r = await getDraftReply(t.id)
      setDraft(r.data.draft); setMeta(r.data)
    } catch { setDraft('Failed — is Ollama running?') }
    finally { setLoading(false) }
  }

  const save = async () => {
    await updateTicket(t.id, { status: 'in_progress', ai_draft_reply: draft })
    setSaved(true)
    setTimeout(() => { onUpdate(); onClose() }, 1200)
  }

  return (
    <div className="overlay" onClick={e => e.target===e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-hd">
          <div style={{ flex: 1, paddingRight: 12 }}>
            <div style={{ fontWeight: 700, fontSize: '1rem', marginBottom: 8 }}>{t.subject}</div>
            <div style={{ display:'flex', gap:6, flexWrap:'wrap', alignItems:'center' }}>
              <span className={`badge ${urgencyClass(t.urgency_score)}`}>{urgencyLabel(t.urgency_score)} · {t.urgency_score?.toFixed(0)}</span>
              <span className={`emo-badge emo-${t.emotion_type}`}>{EMO[t.emotion_type]||'😐'} {t.emotion_type} {t.emotion_score?.toFixed(1)}/10</span>
              {t.is_churn_risk && <span className="badge badge-red">⚠ Churn Risk</span>}
              {t.requires_human && <span className="badge badge-amber">👤 Human Required</span>}
              {t.is_escalated && <span className="badge badge-amber">🔺 Escalated</span>}
              <span className={`tier-${t.customer_tier}`}>{t.customer_tier?.toUpperCase()}</span>
            </div>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        {/* AI Summary */}
        {t.ai_summary && (
          <div className="ai-panel" style={{ marginBottom: 14 }}>
            <div className="ai-hd"><span className="ai-pulse" />3-Line AI Summary</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {t.ai_summary.split('\n').filter(Boolean).map((line, i) => (
                <div key={i} style={{ display:'flex', gap:10, fontSize:'0.85rem', lineHeight:1.6 }}>
                  <span style={{ color:'var(--blue)', fontWeight:700, fontFamily:'var(--mono)', flexShrink:0 }}>{'①②③'[i]||''}</span>
                  <span style={{ color:'var(--text2)' }}>{line}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Original */}
        <div className="form-group">
          <label className="form-label">Customer Message</label>
          <div style={{ background:'var(--bg4)', border:'1px solid var(--border)', borderRadius:8, padding:'12px 14px', fontSize:'0.85rem', color:'var(--text2)', lineHeight:1.65, maxHeight:130, overflowY:'auto' }}>{t.description}</div>
        </div>

        {/* Metadata */}
        <div style={{ display:'flex', gap:6, flexWrap:'wrap', marginBottom:14 }}>
          {t.intent && <span className="badge badge-blue">{t.intent}</span>}
          {t.product_area && <span className="badge badge-purple">📦 {t.product_area}</span>}
          {t.platform && <span className="badge badge-cyan">📱 {t.platform}</span>}
          {t.severity && <span className={`badge ${t.severity==='P1'?'badge-red':t.severity==='P2'?'badge-amber':'badge-green'}`}>{t.severity}</span>}
          <span className="badge badge-blue">SLA: <SLATimer deadline={t.sla_deadline} breached={t.sla_breached} /></span>
        </div>

        {/* KB Suggestions */}
        {sugs.length > 0 && (
          <div style={{ marginBottom: 14 }}>
            <label className="form-label">📚 KB Solution Matches</label>
            <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
              {sugs.map((s, i) => (
                <div key={i} style={{ background:'var(--bg4)', border:'1px solid var(--border2)', borderRadius:8, padding:'10px 13px' }}>
                  <div style={{ display:'flex', justifyContent:'space-between', marginBottom:4 }}>
                    <span style={{ fontWeight:600, fontSize:'0.83rem' }}>{s.article_title}</span>
                    <span style={{ fontFamily:'var(--mono)', fontSize:'0.75rem', color: s.confidence_score>=0.8?'var(--green)':'var(--amber)' }}>
                      {(s.confidence_score*100).toFixed(0)}% match
                    </span>
                  </div>
                  {s.rewritten_steps && <div style={{ fontSize:'0.8rem', color:'var(--text2)', lineHeight:1.55 }}>{s.rewritten_steps}</div>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Draft */}
        <div style={{ marginBottom: 14 }}>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8 }}>
            <label className="form-label" style={{ margin:0 }}>✍️ Draft Reply</label>
            <button className="btn btn-secondary btn-sm" onClick={genDraft} disabled={loading}>
              {loading ? <><span className="spinner" style={{width:13,height:13}}/>Generating…</> : '🤖 Generate with AI'}
            </button>
          </div>
          {meta && (
            <div style={{ display:'flex', gap:6, marginBottom:8, flexWrap:'wrap' }}>
              <span className="badge badge-blue">Tone: {meta.tone_applied?.replace('_',' ')}</span>
              <span className={`badge ${meta.low_confidence?'badge-amber':'badge-green'}`}>
                Confidence: {(meta.confidence*100).toFixed(0)}%
              </span>
              {meta.policy_flags?.map((f,i) => <span key={i} className="badge badge-red">⚠ {f}</span>)}
            </div>
          )}
          <textarea className="textarea" style={{ minHeight:150, fontFamily:'var(--font)', fontSize:'0.87rem', lineHeight:1.7 }} value={draft} onChange={e => setDraft(e.target.value)} placeholder="Click 'Generate with AI' or type manually…" />
          {meta?.low_confidence && <div className="alert alert-warn" style={{ marginTop:8, fontSize:'0.8rem' }}>⚠ Low confidence — review before sending</div>}
        </div>

        {/* AI Solution Panel */}
        <SolutionPanel ticket={t} onUseAsDraft={(text) => setDraft(text)} />

        <div className="divider" />

        {/* Actions */}
        <div style={{ display:'flex', gap:8, justifyContent:'space-between', alignItems:'center' }}>
          <div>
            <a 
              href={`mailto:${t.customer_email}?subject=Re: ${encodeURIComponent(t.subject)}&body=${encodeURIComponent(draft)}`}
              className="btn btn-secondary" 
              style={{ display: draft ? 'inline-flex' : 'none', textDecoration: 'none' }}
            >
              ✉️ Open in Mail Client
            </a>
          </div>
          <div style={{ display:'flex', gap:8 }}>
            {saved
              ? <div className="alert alert-success" style={{ padding:'8px 14px' }}>✅ Saved!</div>
              : <>
                  <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
                  <button className="btn btn-primary" onClick={save} disabled={!draft}>💾 Save & Mark In Progress</button>
                </>
            }
          </div>
        </div>
      </div>
    </div>
  )
}

export default function AgentView() {
  const [tickets, setTickets] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)
  const [filter, setFilter] = useState('open')
  const [sortBy, setSortBy] = useState('urgency_score')

  const load = useCallback(async () => {
    const p = { sort_by: sortBy, limit: 60 }
    if (filter !== 'all') p.status = filter
    const r = await getTickets(p)
    setTickets(r.data)
    setLoading(false)
  }, [filter, sortBy])

  useEffect(() => { load() }, [load])
  useEffect(() => { const t = setInterval(load, 15000); return ()=>clearInterval(t) }, [load])

  const churn = tickets.filter(t=>t.is_churn_risk).length
  const esc = tickets.filter(t=>t.is_escalated).length
  const p1 = tickets.filter(t=>t.severity==='P1').length
  const breach = tickets.filter(t=>t.sla_breached).length

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">🎯 Agent Queue</div>
          <div className="page-sub">Urgency-sorted · Auto-refreshes every 15s · {tickets.length} tickets</div>
        </div>
        <div style={{ display:'flex', gap:8 }}>
          <select className="select" style={{width:130}} value={filter} onChange={e=>setFilter(e.target.value)}>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="all">All</option>
          </select>
          <select className="select" style={{width:150}} value={sortBy} onChange={e=>setSortBy(e.target.value)}>
            <option value="urgency_score">By Urgency</option>
            <option value="created_at">By Newest</option>
            <option value="emotion_score">By Emotion</option>
          </select>
          <button className="btn btn-secondary btn-sm" onClick={load}>⟳</button>
        </div>
      </div>

      <div className="page-body">
        {/* Stats */}
        <div className="stats-row" style={{ gridTemplateColumns:'repeat(4,1fr)' }}>
          {[
            { icon:'🎫', val:tickets.length, lbl:'Active Tickets', col:'var(--blue)', bg:'var(--bg4)' },
            { icon:'⚠️', val:churn, lbl:'Churn Risks', col:'var(--red)', bg:'var(--red-dim)' },
            { icon:'🔺', val:esc, lbl:'Escalated', col:'var(--amber)', bg:'var(--amber-dim)' },
            { icon:'🚨', val:breach, lbl:'SLA Breached', col:'var(--red)', bg:'var(--red-dim)' },
          ].map((s,i) => (
            <div className="stat-card" key={i}>
              <div className="stat-card-bg" style={{ background: s.col }} />
              <div className="stat-icon" style={{ background: s.bg }}>{s.icon}</div>
              <div className="stat-val" style={{ color: s.col }}>{s.val}</div>
              <div className="stat-lbl">{s.lbl}</div>
            </div>
          ))}
        </div>

        {loading ? (
          <div className="empty"><div className="spinner" style={{width:38,height:38,margin:'0 auto 14px'}}/><div>Loading tickets…</div></div>
        ) : tickets.length === 0 ? (
          <div className="empty"><div className="empty-icon">✅</div><div className="empty-title">Queue is clear!</div><div className="empty-sub">No tickets matching this filter</div></div>
        ) : (
          <div style={{ display:'flex', flexDirection:'column', gap:5 }}>
            {/* Column headers */}
            <div style={{ display:'grid', gridTemplateColumns:'90px 1fr 120px 100px 130px 95px 150px', gap:12, padding:'6px 16px', fontSize:'0.65rem', fontWeight:700, color:'var(--text3)', textTransform:'uppercase', letterSpacing:'0.07em' }}>
              <span>Urgency</span><span>Ticket</span><span>Emotion</span><span>Intent</span><span>Customer</span><span>SLA</span><span>Action</span>
            </div>

            {tickets.map(t => (
              <div
                key={t.id}
                className={`ticket-row ${t.is_churn_risk?'churn-risk':t.is_escalated?'escalated':''}`}
                style={{ gridTemplateColumns:'90px 1fr 120px 100px 130px 95px 150px' }}
                onClick={() => setSelected(t)}
              >
                {/* Urgency */}
                <div>
                  <span className={`badge ${urgencyClass(t.urgency_score)}`} style={{fontSize:'0.67rem'}}>
                    {urgencyLabel(t.urgency_score)}
                  </span>
                  <div style={{fontFamily:'var(--mono)',fontSize:'0.7rem',color:'var(--text3)',marginTop:3}}>{t.urgency_score?.toFixed(0)}/100</div>
                </div>

                {/* Subject */}
                <div>
                  <div className="ticket-subject">{t.subject}</div>
                  {t.ai_summary && <div className="ticket-summary">{t.ai_summary.split('\n')[0]}</div>}
                  <div className="ticket-tags">
                    {t.is_churn_risk && <span className="badge badge-red" style={{fontSize:'0.6rem'}}>⚠ Churn</span>}
                    {t.requires_human && <span className="badge badge-amber" style={{fontSize:'0.6rem'}}>👤 Human</span>}
                    {t.product_area && <span className="badge badge-blue" style={{fontSize:'0.6rem'}}>{t.product_area}</span>}
                  </div>
                </div>

                {/* Emotion */}
                <div>
                  <span className={`emo-badge emo-${t.emotion_type}`}>{EMO[t.emotion_type]||'😐'} {t.emotion_type}</span>
                  <div style={{fontFamily:'var(--mono)',fontSize:'0.7rem',color:'var(--text3)',marginTop:3}}>{t.emotion_score?.toFixed(1)}/10</div>
                </div>

                {/* Intent */}
                <div><span className="badge badge-blue" style={{fontSize:'0.68rem'}}>{t.intent||'—'}</span></div>

                {/* Customer */}
                <div>
                  <div style={{fontSize:'0.82rem',fontWeight:600}}>{t.customer_name||'Anon'}</div>
                  <div className={`tier-${t.customer_tier}`}>{t.customer_tier?.toUpperCase()}</div>
                </div>

                {/* SLA */}
                <div>
                  <SLATimer deadline={t.sla_deadline} breached={t.sla_breached} />
                  <div style={{fontSize:'0.68rem',color:'var(--text3)',marginTop:2}}>{t.severity}</div>
                </div>

                {/* Action */}
                <div onClick={e=>e.stopPropagation()}>
                  <button className="btn btn-primary btn-sm" onClick={()=>setSelected(t)} style={{fontSize:'0.74rem',width:'100%',justifyContent:'center'}}>
                    View Draft
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {selected && <TicketModal ticket={selected} onClose={()=>setSelected(null)} onUpdate={load} />}
    </>
  )
}
