import { useState } from 'react'
import { createTicketSync } from '../api/client'

const SAMPLES = [
  { subject:"Payment keeps failing — charged twice", description:"I've tried to renew 3 times, payment fails each time but my bank shows 2 charges of $49. Order ORD-88291. This is unacceptable — fix this NOW!", customer_name:"Jennifer Walsh", customer_email:"j.walsh@example.com", customer_tier:"premium" },
  { subject:"Switching to competitor unless you match their price", description:"Been a customer 2 years but just got an offer 30% cheaper from a competitor. Unless you match it I'm cancelling next month. Last chance to keep my business.", customer_name:"Robert Chen", customer_email:"rchen@business.com", customer_tier:"standard" },
  { subject:"App crashes on every launch — entire team affected", description:"Since your update yesterday the Android app crashes immediately on open. Android 14, app v4.2.1. Cleared cache, reinstalled 3x. My whole team of 15 is blocked — we're enterprise paying for reliability!", customer_name:"Sandra O'Connor", customer_email:"soconnor@bigcorp.com", customer_tier:"enterprise" },
  { subject:"How do I export all my ticket history?", description:"Hi, I need to export all ticket history to CSV for a quarterly audit. I've checked Settings but can't find the export option. No rush, just need it sometime this week.", customer_name:"Mark Johnson", customer_email:"mark.j@company.org", customer_tier:"standard" },
]

const STEPS = [
  { icon:'🔒', label:'PII masking' },
  { icon:'😡', label:'Emotion detection' },
  { icon:'🎯', label:'Intent classification' },
  { icon:'⚠️', label:'Churn risk analysis' },
  { icon:'📊', label:'Urgency scoring' },
  { icon:'🏷️', label:'Auto-tagging (SLM)' },
  { icon:'📝', label:'3-line summary (SLM)' },
  { icon:'🔍', label:'RAG KB search' },
]

function Step({ label, icon, done, active }) {
  return (
    <div style={{ display:'flex', alignItems:'center', gap:12, padding:'7px 0', borderBottom:'1px solid var(--border)', transition:'all 0.3s' }}>
      <div style={{ width:28, height:28, borderRadius:'50%', display:'flex', alignItems:'center', justifyContent:'center', fontSize:'0.85rem', flexShrink:0, transition:'all 0.3s',
        background: done ? 'var(--green-dim)' : active ? 'var(--blue-dim)' : 'var(--bg5)',
        border: `1px solid ${done ? 'rgba(16,217,140,0.3)' : active ? 'rgba(79,142,247,0.3)' : 'var(--border)'}`,
      }}>
        {done ? '✓' : active ? <span className="spinner" style={{width:13,height:13}} /> : icon}
      </div>
      <span style={{ fontSize:'0.87rem', fontWeight: done || active ? 600 : 400, transition:'color 0.3s',
        color: done ? 'var(--green)' : active ? 'var(--blue)' : 'var(--text3)',
      }}>{label}</span>
    </div>
  )
}

function ResultPanel({ r }) {
  const urgencyColor = r.urgency_score>=65?'var(--red)':r.urgency_score>=35?'var(--amber)':'var(--green)'
  const urgencyLabel = r.urgency_score>=65?'🔴 HIGH':r.urgency_score>=35?'🟡 MEDIUM':'🟢 LOW'
  const EMO = {angry:'😡',frustrated:'😤',confused:'🤔',neutral:'😐',happy:'😊',worried:'😟'}

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:14 }}>
      <div className="ai-panel">
        <div className="ai-hd"><span className="ai-pulse"/>AI Pipeline Complete</div>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:10, textAlign:'center' }}>
          <div>
            <div style={{ fontSize:'0.65rem', color:'var(--text3)', marginBottom:5, textTransform:'uppercase', letterSpacing:'0.05em' }}>Urgency</div>
            <div style={{ fontSize:'1.3rem', fontWeight:900, color:urgencyColor }}>{urgencyLabel}</div>
            <div style={{ fontFamily:'var(--mono)', fontSize:'0.8rem', color:'var(--text2)' }}>{r.urgency_score?.toFixed(0)}/100</div>
          </div>
          <div>
            <div style={{ fontSize:'0.65rem', color:'var(--text3)', marginBottom:5, textTransform:'uppercase', letterSpacing:'0.05em' }}>Emotion</div>
            <div style={{ fontSize:'1.1rem' }}>{EMO[r.emotion_type]||'😐'} <span style={{fontWeight:700}}>{r.emotion_type}</span></div>
            <div style={{ fontFamily:'var(--mono)', fontSize:'0.8rem', color:'var(--text2)' }}>{r.emotion_score?.toFixed(1)}/10</div>
          </div>
          <div>
            <div style={{ fontSize:'0.65rem', color:'var(--text3)', marginBottom:5, textTransform:'uppercase', letterSpacing:'0.05em' }}>Intent</div>
            <span className="badge badge-blue">{r.intent}</span>
          </div>
        </div>
      </div>

      {(r.is_churn_risk || r.requires_human) && (
        <div style={{ display:'flex', gap:8 }}>
          {r.is_churn_risk && <div className="alert alert-danger" style={{flex:1}}>⚠️ <strong>Churn Risk</strong> — retention agent notified</div>}
          {r.requires_human && <div className="alert alert-warn" style={{flex:1}}>👤 <strong>Human Required</strong></div>}
        </div>
      )}

      <div>
        <div className="form-label">Auto-Tags</div>
        <div style={{ display:'flex', gap:6, flexWrap:'wrap' }}>
          {r.product_area && <span className="badge badge-purple">📦 {r.product_area}</span>}
          {r.platform && <span className="badge badge-cyan">📱 {r.platform}</span>}
          {r.severity && <span className={`badge ${r.severity==='P1'?'badge-red':r.severity==='P2'?'badge-amber':'badge-green'}`}>🚦 {r.severity}</span>}
          {r.customer_tier && <span className="badge badge-blue">👤 {r.customer_tier}</span>}
        </div>
      </div>

      {r.ai_summary && (
        <div>
          <div className="form-label">3-Line AI Summary</div>
          <div className="ai-panel" style={{ padding:13 }}>
            {r.ai_summary.split('\n').filter(Boolean).map((line,i) => (
              <div key={i} style={{ display:'flex', gap:10, padding:'5px 0', borderBottom:i<2?'1px solid rgba(79,142,247,0.1)':'none' }}>
                <span style={{ color:'var(--blue)', fontWeight:700, fontFamily:'var(--mono)', fontSize:'0.9rem', flexShrink:0 }}>{'①②③'[i]}</span>
                <span style={{ fontSize:'0.85rem', color:'var(--text2)', lineHeight:1.6 }}>{line}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="alert alert-success">✅ Ticket saved — open <strong>Agent Queue</strong> to see it ranked by urgency</div>
    </div>
  )
}

export default function TicketInbox() {
  const [form, setForm] = useState({ subject:'', description:'', customer_name:'', customer_email:'', customer_tier:'standard' })
  const [processing, setProcessing] = useState(false)
  const [step, setStep] = useState(-1)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const loadSample = (s) => { setForm({ ...s }); setResult(null); setError(null); setStep(-1) }

  const submit = async (e) => {
    e.preventDefault()
    setProcessing(true); setResult(null); setError(null); setStep(0)
    const iv = setInterval(() => setStep(p => p < STEPS.length-1 ? p+1 : p), 900)
    try {
      const r = await createTicketSync(form)
      clearInterval(iv); setStep(STEPS.length); setResult(r.data)
    } catch (err) {
      clearInterval(iv); setError(err.response?.data?.detail || 'Failed — is the backend running?')
    }
    setProcessing(false)
  }

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">📥 Submit Ticket</div>
          <div className="page-sub">Watch the full 8-step AI pipeline process in real time</div>
        </div>
      </div>

      <div className="page-body">
        <div className="grid-2" style={{ alignItems:'start', gap:22 }}>
          {/* Left */}
          <div>
            <div className="card" style={{ marginBottom:16 }}>
              <div className="card-hd"><span className="card-hd-dot"/>Quick Load — Sample Tickets</div>
              <div style={{ display:'flex', flexDirection:'column', gap:7 }}>
                {SAMPLES.map((s,i) => (
                  <button key={i} className="btn btn-secondary btn-sm" onClick={()=>loadSample(s)} style={{ justifyContent:'space-between', textAlign:'left', padding:'9px 12px', height:'auto' }}>
                    <span style={{ fontSize:'0.81rem', flex:1, textAlign:'left' }}>{s.subject}</span>
                    <span className={`tier-${s.customer_tier}`} style={{ marginLeft:10, flexShrink:0 }}>{s.customer_tier.toUpperCase()}</span>
                  </button>
                ))}
              </div>
            </div>

            <form className="card" onSubmit={submit}>
              <div className="card-hd"><span className="card-hd-dot"/>Ticket Details</div>
              <div className="form-group">
                <label className="form-label">Subject *</label>
                <input className="input" required value={form.subject} onChange={e=>setForm({...form,subject:e.target.value})} placeholder="Brief issue description…" />
              </div>
              <div className="form-group">
                <label className="form-label">Customer Message *</label>
                <textarea className="textarea" required style={{minHeight:130}} value={form.description} onChange={e=>setForm({...form,description:e.target.value})} placeholder="Paste the full customer message — include frustration, urgency, account info…" />
              </div>
              <div className="grid-2" style={{ gap:10 }}>
                <div className="form-group" style={{margin:0}}>
                  <label className="form-label">Name</label>
                  <input className="input" value={form.customer_name} onChange={e=>setForm({...form,customer_name:e.target.value})} placeholder="Jane Smith" />
                </div>
                <div className="form-group" style={{margin:0}}>
                  <label className="form-label">Email</label>
                  <input className="input" type="email" value={form.customer_email} onChange={e=>setForm({...form,customer_email:e.target.value})} placeholder="jane@company.com" />
                </div>
              </div>
              <div className="form-group" style={{ marginTop:10 }}>
                <label className="form-label">Customer Tier</label>
                <select className="select" value={form.customer_tier} onChange={e=>setForm({...form,customer_tier:e.target.value})}>
                  <option value="standard">Standard</option>
                  <option value="premium">Premium</option>
                  <option value="enterprise">Enterprise</option>
                </select>
              </div>
              <div style={{ display:'flex', gap:8, marginTop:6 }}>
                <button type="submit" className="btn btn-primary" disabled={processing} style={{ flex:1, justifyContent:'center' }}>
                  {processing ? <><span className="spinner" style={{width:15,height:15}}/>Processing…</> : '🚀 Process with AI Pipeline'}
                </button>
                {result && <button type="button" className="btn btn-secondary" onClick={()=>{setResult(null);setStep(-1)}}>New</button>}
              </div>
            </form>
          </div>

          {/* Right */}
          <div>
            <div className="card" style={{ marginBottom:16 }}>
              <div className="card-hd"><span className="card-hd-dot"/>AI Pipeline Progress</div>
              {STEPS.map((s,i) => (
                <Step key={i} icon={s.icon} label={s.label} done={step>i} active={processing && step===i} />
              ))}
            </div>
            {error && <div className="alert alert-danger">{error}</div>}
            {result && (
              <div className="card">
                <div className="card-hd"><span className="card-hd-dot"/>Pipeline Results</div>
                <ResultPanel r={result} />
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
