import { useState, useEffect } from 'react'
import { getWeeklyDigest } from '../api/client'

export default function WeeklyDigest() {
  const [digest, setDigest] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetch = async () => {
    setLoading(true); setError(null)
    try { const r = await getWeeklyDigest(); setDigest(r.data) }
    catch { setError('Failed to generate — check backend connection.') }
    finally { setLoading(false) }
  }

  useEffect(() => { fetch() }, [])

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">📋 Weekly Digest</div>
          <div className="page-sub">SLM-generated plain-English narrative for team leads · Powered by llama3.2:3b</div>
        </div>
        <button className="btn btn-primary btn-sm" onClick={fetch} disabled={loading}>
          {loading ? <><span className="spinner" style={{width:13,height:13}}/>Generating…</> : '🔄 Regenerate'}
        </button>
      </div>

      <div className="page-body" style={{ maxWidth:900, margin:'0 auto' }}>
        {loading && !digest && (
          <div className="empty" style={{ paddingTop:80 }}>
            <div style={{ display:'flex', justifyContent:'center', marginBottom:20 }}>
              <div className="ai-pulse" style={{ width:24, height:24 }} />
            </div>
            <div style={{ fontSize:'1.05rem', color:'var(--text2)', marginBottom:8 }}>Generating weekly digest…</div>
            <div style={{ fontSize:'0.82rem', color:'var(--text3)' }}>This may take 15–30 seconds with llama3.2:3b</div>
          </div>
        )}

        {error && <div className="alert alert-danger">{error}</div>}

        {digest && (
          <>
            {/* Header card */}
            <div style={{ marginBottom:18, padding:'22px 26px', background:'linear-gradient(135deg,rgba(79,142,247,0.07),rgba(124,92,252,0.07))', border:'1px solid rgba(79,142,247,0.18)', borderRadius:'var(--r-xl)' }}>
              <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:14 }}>
                <div>
                  <div style={{ fontSize:'0.68rem', fontWeight:700, color:'var(--blue)', textTransform:'uppercase', letterSpacing:'0.1em', marginBottom:4 }}>Weekly Support Digest</div>
                  <div style={{ fontSize:'1.3rem', fontWeight:800, letterSpacing:'-0.02em' }}>Period: {digest.period}</div>
                </div>
                <div style={{ fontSize:'0.75rem', color:'var(--text3)' }}>Generated {new Date(digest.generated_at).toLocaleString()}</div>
              </div>
              {/* KPI pills */}
              <div style={{ display:'flex', gap:10, flexWrap:'wrap' }}>
                {[
                  { label:'CSAT Avg', value: digest.csat_summary.avg ?? 'N/A', change: digest.csat_summary.change, color:'var(--green)' },
                  { label:'SLA Breach Rate', value:`${digest.sla_summary.breach_rate}%`, color: digest.sla_summary.breach_rate > 10 ? 'var(--red)' : 'var(--amber)' },
                  ...digest.top_categories.map((c,i) => ({ label:`#${i+1} Category`, value:`${c.area} (${c.count})`, color:'var(--blue)' })),
                ].map((p,i) => (
                  <div key={i} style={{ background:'var(--bg3)', border:'1px solid var(--border)', borderRadius:9, padding:'9px 14px', minWidth:110 }}>
                    <div style={{ fontSize:'0.65rem', color:'var(--text3)', marginBottom:3, textTransform:'uppercase', letterSpacing:'0.05em' }}>{p.label}</div>
                    <div style={{ fontWeight:700, color:p.color, fontSize:'0.9rem' }}>
                      {p.value}
                      {p.change !== undefined && p.change !== 'N/A' && (
                        <span style={{ fontSize:'0.72rem', marginLeft:5, color:p.change>=0?'var(--green)':'var(--red)' }}>
                          {p.change>=0?'↑':'↓'}{Math.abs(p.change)}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Narrative */}
            <div className="card" style={{ marginBottom:16 }}>
              <div className="ai-hd" style={{ marginBottom:16 }}><span className="ai-pulse"/>AI-Generated Narrative</div>
              <div style={{ fontSize:'0.95rem', lineHeight:1.85, color:'var(--text2)', whiteSpace:'pre-wrap' }}>{digest.narrative}</div>
            </div>

            {/* Recommendation */}
            <div className="alert alert-info" style={{ padding:'14px 18px' }}>
              <div>
                <div style={{ fontWeight:700, marginBottom:5, fontSize:'0.9rem' }}>💡 Recommended Action for Next Week</div>
                <div style={{ fontSize:'0.88rem', lineHeight:1.65 }}>{digest.recommendation}</div>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  )
}
