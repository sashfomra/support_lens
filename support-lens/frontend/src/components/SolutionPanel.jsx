import { useState } from 'react'
import axios from 'axios'

const api = axios.create({ baseURL: '/api', timeout: 120000 })

const SOURCE_ICONS = { docs: '📄', reddit: '🔴', stackoverflow: '🟧' }
const SOURCE_LABELS = { docs: 'Docs', reddit: 'Reddit', stackoverflow: 'Stack Overflow' }

function ConfidenceBadge({ score }) {
  const pct = Math.round(score * 100)
  const color = pct >= 75 ? 'var(--green)' : 'var(--amber)'
  return (
    <span style={{ fontSize:'0.68rem', fontWeight:700, color, fontFamily:'var(--mono)', background: pct>=75?'var(--green-dim)':'var(--amber-dim)', padding:'2px 8px', borderRadius:100, border:`1px solid ${pct>=75?'rgba(16,217,140,0.3)':'rgba(245,158,11,0.3)'}` }}>
      {pct}% confident
    </span>
  )
}

function SourceChip({ source }) {
  const label = `${SOURCE_ICONS[source.type]||'🔗'} ${SOURCE_LABELS[source.type]||source.type}`
  const short = source.url ? source.url.replace(/^https?:\/\/(www\.)?/,'').split('/')[0] : source.type
  return (
    <a href={source.url || '#'} target="_blank" rel="noreferrer"
      style={{ display:'inline-flex', alignItems:'center', gap:4, padding:'3px 9px', borderRadius:100, fontSize:'0.69rem', fontWeight:600, background:'var(--bg4)', border:'1px solid var(--border2)', color:'var(--text2)', textDecoration:'none', transition:'all 0.15s' }}
      onMouseEnter={e=>e.currentTarget.style.borderColor='var(--blue)'}
      onMouseLeave={e=>e.currentTarget.style.borderColor='var(--border2)'}
    >
      {label} · {short}
    </a>
  )
}

function FeedbackPanel({ ticketId, onDone }) {
  const [rating, setRating] = useState(null)
  const [comment, setComment] = useState('')
  const [sent, setSent] = useState(false)

  const submit = async () => {
    try {
      await api.post('/api/solution/feedback', { ticket_id: ticketId, rating, comment })
      setSent(true)
      setTimeout(onDone, 1500)
    } catch {}
  }

  if (sent) return <div style={{ fontSize:'0.8rem', color:'var(--green)' }}>✓ Feedback recorded</div>

  return (
    <div style={{ marginTop:10, display:'flex', flexDirection:'column', gap:8 }}>
      <div style={{ display:'flex', gap:8 }}>
        <button className="btn btn-secondary btn-sm" onClick={()=>setRating(1)} style={{ flex:1, justifyContent:'center', borderColor: rating===1?'var(--green)':'var(--border2)', color: rating===1?'var(--green)':'inherit' }}>👍 Helpful</button>
        <button className="btn btn-secondary btn-sm" onClick={()=>setRating(-1)} style={{ flex:1, justifyContent:'center', borderColor: rating===-1?'var(--red)':'var(--border2)', color: rating===-1?'var(--red)':'inherit' }}>👎 Not helpful</button>
      </div>
      {rating === -1 && (
        <>
          <input className="input" style={{fontSize:'0.8rem'}} placeholder="What was wrong with this solution?" value={comment} onChange={e=>setComment(e.target.value)} />
          <button className="btn btn-primary btn-sm" onClick={submit} disabled={!comment.trim()} style={{alignSelf:'flex-end'}}>Submit feedback</button>
        </>
      )}
      {rating === 1 && (
        <button className="btn btn-primary btn-sm" onClick={submit} style={{alignSelf:'flex-start'}}>Submit</button>
      )}
    </div>
  )
}

export default function SolutionPanel({ ticket, onUseAsDraft }) {
  const [solution, setSolution] = useState(null)
  const [loading, setLoading] = useState(false)
  const [fetched, setFetched] = useState(false)
  const [copied, setCopied] = useState(false)
  const [showFeedback, setShowFeedback] = useState(false)

  const fetchSolution = async () => {
    setLoading(true)
    try {
      const r = await api.post('/api/solution', {
        ticket_id: String(ticket.id),
        summary: ticket.ai_summary || ticket.subject,
        issue_category: ticket.product_area || ticket.intent || 'General',
        product_name: 'SupportLens',
        emotion_score: ticket.emotion_score || 5,
        intent: ticket.intent || 'general_complaint',
      })
      setSolution(r.data)
      setFetched(true)
    } catch (e) {
      setSolution({ fallback_flag: true, message: 'Solution engine unavailable', confidence_score: 0, sources_used: [] })
      setFetched(true)
    }
    setLoading(false)
  }

  const copy = () => {
    navigator.clipboard.writeText(solution.solution_text || '')
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!fetched) {
    return (
      <div style={{ marginTop:14 }}>
        <div style={{ fontSize:'0.7rem', fontWeight:700, color:'var(--text3)', textTransform:'uppercase', letterSpacing:'0.08em', marginBottom:8 }}>💡 AI Suggested Solution</div>
        <button className="btn btn-secondary btn-sm" onClick={fetchSolution} style={{width:'100%', justifyContent:'center'}}>
          🔍 Find Solution (ChromaDB + Reddit + Stack Overflow)
        </button>
      </div>
    )
  }

  if (loading) {
    return (
      <div style={{ marginTop:14 }}>
        <div style={{ fontSize:'0.7rem', fontWeight:700, color:'var(--text3)', textTransform:'uppercase', letterSpacing:'0.08em', marginBottom:8 }}>💡 AI Suggested Solution</div>
        <div style={{ display:'flex', alignItems:'center', gap:10, padding:'14px', background:'var(--bg4)', borderRadius:9, border:'1px solid var(--border)' }}>
          <span className="spinner" /><span style={{ fontSize:'0.83rem', color:'var(--text2)' }}>Searching docs · Reddit · Stack Overflow…</span>
        </div>
      </div>
    )
  }

  const isGood = solution && !solution.fallback_flag && solution.solution_text

  return (
    <div style={{ marginTop:14 }}>
      <div style={{ fontSize:'0.7rem', fontWeight:700, color:'var(--text3)', textTransform:'uppercase', letterSpacing:'0.08em', marginBottom:8 }}>💡 AI Suggested Solution</div>

      {isGood ? (
        <div style={{ background:'rgba(16,217,140,0.04)', border:'1px solid rgba(16,217,140,0.25)', borderLeft:`3px solid ${solution.is_general_knowledge ? 'var(--amber)' : 'var(--green)'}`, borderRadius:9, padding:'13px 14px' }}>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:10 }}>
            <div style={{ display:'flex', gap:6, alignItems:'center', flexWrap:'wrap' }}>
              {solution.is_general_knowledge
                ? <span style={{ fontSize:'0.68rem', fontWeight:700, color:'var(--amber)', background:'var(--amber-dim)', padding:'2px 8px', borderRadius:100, border:'1px solid rgba(245,158,11,0.3)' }}>🧠 AI General Knowledge — review before sending</span>
                : <ConfidenceBadge score={solution.confidence_score} />
              }
              {solution.is_general_knowledge && solution.confidence_score > 0 &&
                <span style={{ fontSize:'0.67rem', color:'var(--text3)' }}>No KB match found</span>
              }
            </div>
            <div style={{ display:'flex', gap: 6 }}>
              {onUseAsDraft && solution.solution_text && (
                <button className="btn btn-secondary btn-sm" onClick={() => onUseAsDraft(solution.solution_text)} style={{fontSize:'0.72rem'}}>
                  📝 Use as Draft
                </button>
              )}
              <button className="btn btn-ghost btn-sm" onClick={copy} style={{fontSize:'0.72rem'}}>
                {copied ? 'Copied!' : '📋 Copy'}
              </button>
            </div>
          </div>
          <div style={{ fontSize:'0.86rem', lineHeight:1.75, color:'var(--text2)', whiteSpace:'pre-wrap', marginBottom:12 }}>
            {solution.solution_text}
          </div>
          {!solution.is_general_knowledge && solution.sources_used?.length > 0 && (
            <div>
              <div style={{ fontSize:'0.67rem', color:'var(--text3)', marginBottom:5, fontWeight:600, textTransform:'uppercase', letterSpacing:'0.06em' }}>Sources</div>
              <div style={{ display:'flex', gap:6, flexWrap:'wrap' }}>
                {solution.sources_used.map((s,i) => <SourceChip key={i} source={s} />)}
              </div>
            </div>
          )}
          <div style={{ marginTop:12, paddingTop:10, borderTop:'1px solid rgba(16,217,140,0.15)' }}>
            {!showFeedback
              ? <button className="btn btn-ghost btn-sm" onClick={()=>setShowFeedback(true)} style={{fontSize:'0.75rem'}}>Rate this solution 👍👎</button>
              : <FeedbackPanel ticketId={String(ticket.id)} onDone={()=>setShowFeedback(false)} />
            }
          </div>
        </div>
      ) : (
        <div style={{ background:'rgba(244,63,94,0.04)', border:'1px solid rgba(244,63,94,0.25)', borderLeft:'3px solid var(--red)', borderRadius:9, padding:'13px 14px' }}>
          <div style={{ fontWeight:700, color:'var(--red)', fontSize:'0.86rem', marginBottom:5 }}>⚠ No Verified Solution Found</div>
          <div style={{ fontSize:'0.82rem', color:'var(--text2)', marginBottom:12 }}>{solution?.message || 'No verified solution found — escalating to senior agent'}</div>
          <button className="btn btn-primary btn-sm">🔺 Escalate to Senior Agent</button>
        </div>
      )}
    </div>
  )
}
