import { useState, useEffect } from 'react'
import {
  getIngestStatus, triggerRedditIngest, triggerAppStoreIngest, triggerEmailIngest,
  getManagerAlerts, dismissAlert
} from '../api/client'

/* ── Helpers ──────────────────────────────────────────── */
const statusColor = (s) => {
  if (!s || s === 'never') return 'var(--text3)'
  if (s === 'ok') return 'var(--green)'
  if (s === 'running') return 'var(--blue)'
  return 'var(--red)'
}
const statusIcon = (s) => {
  if (!s || s === 'never') return '○'
  if (s === 'ok') return '✓'
  if (s === 'running') return '⟳'
  return '✕'
}

/* ── Spike Alert Card ──────────────────────────────────── */
function SpikeAlertCard({ alert, onDismiss }) {
  const isCrit = alert.severity === 'critical'
  return (
    <div style={{
      background: isCrit ? 'rgba(244,63,94,0.1)' : 'rgba(245,158,11,0.1)',
      border: `1px solid ${isCrit ? 'rgba(244,63,94,0.4)' : 'rgba(245,158,11,0.4)'}`,
      borderRadius: 11, padding: '14px 18px',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 14,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <div style={{
          width: 44, height: 44, borderRadius: 11, flexShrink: 0,
          background: isCrit ? 'rgba(244,63,94,0.2)' : 'rgba(245,158,11,0.2)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.4rem',
        }}>
          {isCrit ? '🚨' : '⚠️'}
        </div>
        <div>
          <div style={{ fontWeight: 700, fontSize: '0.92rem', color: isCrit ? 'var(--red)' : 'var(--amber)', marginBottom: 4 }}>
            {alert.category} tickets spiked {alert.spike_pct}%
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text2)', lineHeight: 1.6 }}>
            <strong style={{ color: 'var(--text)' }}>{alert.count_30m}</strong> tickets in the last 30 min
            &nbsp;vs&nbsp;
            <strong style={{ color: 'var(--text)' }}>{alert.avg_hourly}/hr</strong> 7-day average
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text3)', marginTop: 4 }}>
            Detected at {new Date(alert.timestamp).toLocaleTimeString()} — possible system outage or viral issue
          </div>
        </div>
      </div>
      <button
        className="btn btn-ghost btn-sm"
        onClick={() => onDismiss(alert.id)}
        style={{ flexShrink: 0, fontSize: '0.9rem', padding: '5px 10px', borderRadius: 7 }}
      >
        Dismiss ✕
      </button>
    </div>
  )
}

/* ── Source Card ───────────────────────────────────────── */
function SourceCard({ icon, title, description, status, lastCount, lastRun, onTrigger, loading, children }) {
  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 44, height: 44, borderRadius: 11, background: 'var(--bg4)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.4rem', flexShrink: 0,
          }}>
            {icon}
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.95rem', marginBottom: 3 }}>{title}</div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text3)' }}>{description}</div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ color: statusColor(status), fontSize: '0.78rem', fontWeight: 600 }}>
            {statusIcon(status)} {status === 'never' ? 'Not run yet' : status === 'running' ? 'Running…' : status === 'ok' ? `${lastCount} tickets` : status}
          </span>
        </div>
      </div>

      {children && (
        <div style={{ marginBottom: 14, display: 'flex', flexDirection: 'column', gap: 8 }}>
          {children}
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ fontSize: '0.74rem', color: 'var(--text3)' }}>
          {lastRun ? `Last run: ${new Date(lastRun).toLocaleString()}` : 'Never synced'}
        </div>
        <button
          className="btn btn-primary btn-sm"
          onClick={onTrigger}
          disabled={loading || status === 'running'}
          style={{ minWidth: 120, justifyContent: 'center' }}
        >
          {loading ? <><span className="spinner" style={{ width: 13, height: 13 }} /> Triggering…</> : '▶ Run Now'}
        </button>
      </div>
    </div>
  )
}

/* ── Input helper ──────────────────────────────────────── */
function Field({ label, value, onChange, placeholder, hint }) {
  return (
    <div>
      <label className="form-label" style={{ marginBottom: 4 }}>{label}</label>
      <input className="input" style={{ height: 36 }} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} />
      {hint && <div style={{ fontSize: '0.71rem', color: 'var(--text3)', marginTop: 3 }}>{hint}</div>}
    </div>
  )
}

/* ── Main Page ─────────────────────────────────────────── */
export default function DataSources() {
  const [status, setStatus] = useState({ reddit: {}, appstore: {}, email: {} })
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState({})

  // Reddit config
  const [subreddits, setSubreddits] = useState('stripe,techsupport,softwaregore')
  const [redditLimit, setRedditLimit] = useState('20')

  // App Store config
  const [appleId, setAppleId] = useState('')
  const [googleId, setGoogleId] = useState('')

  // Email config
  const [maxEmails, setMaxEmails] = useState('20')

  const poll = async () => {
    try {
      const [s, a] = await Promise.all([getIngestStatus(), getManagerAlerts()])
      setStatus(s.data)
      setAlerts(a.data)
    } catch {}
  }

  useEffect(() => {
    poll()
    const t = setInterval(poll, 10000)  // refresh every 10s
    return () => clearInterval(t)
  }, [])

  const trigger = async (key, fn) => {
    setLoading(p => ({ ...p, [key]: true }))
    try {
      await fn()
      setTimeout(poll, 1500)
    } catch (e) {
      alert(e.response?.data?.detail || 'Ingestion failed — check backend logs')
    }
    setLoading(p => ({ ...p, [key]: false }))
  }

  const handleDismiss = async (id) => {
    await dismissAlert(id).catch(() => {})
    setAlerts(p => p.filter(a => a.id !== id))
  }


  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">📡 Data Sources & Ingestion</div>
          <div className="page-sub">Ingest tickets from Reddit, App Stores, Email — monitor live spike alerts</div>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={poll}>⟳ Refresh</button>
      </div>

      <div className="page-body">

        {/* ── Spike Alerts ──────────────────────────────── */}
        <div className="card" style={{ marginBottom: 22 }}>
          <div className="card-hd">
            <span className="card-hd-dot" style={{ background: 'var(--red)' }} />
            🚨 Live Spike Alerter
            <span style={{ marginLeft: 'auto', fontSize: '0.74rem', color: 'var(--text3)', fontWeight: 400 }}>
              APScheduler · checks every 5 minutes · 2× average threshold
            </span>
          </div>

          {alerts.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '30px 0', color: 'var(--text3)', fontSize: '0.86rem' }}>
              <div style={{ fontSize: '2rem', marginBottom: 10 }}>🟢</div>
              No active spike alerts — all ticket volumes within normal range
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {alerts.map(a => (
                <SpikeAlertCard key={a.id} alert={a} onDismiss={handleDismiss} />
              ))}
            </div>
          )}

          <div style={{ marginTop: 16, padding: '10px 14px', background: 'var(--bg4)', borderRadius: 9, fontSize: '0.78rem', color: 'var(--text3)', lineHeight: 1.7 }}>
            💡 <strong style={{ color: 'var(--text2)' }}>Demo tip:</strong> Submit 5+ tickets on the same topic from the <em>Submit Ticket</em> page — within the next scheduler run (max 5 min), an alert will fire here automatically.
          </div>
        </div>


        {/* ── Ingestion Sources ─────────────────────────── */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>

          {/* Reddit */}
          <SourceCard
            icon="🤖"
            title="Reddit — PRAW"
            description="Fetches complaint posts from subreddits · filters by issue keywords"
            status={status.reddit?.status}
            lastCount={status.reddit?.last_count}
            lastRun={status.reddit?.last_run}
            loading={loading.reddit}
            onTrigger={() => trigger('reddit', () => triggerRedditIngest({
              subreddits: subreddits.split(',').map(s => s.trim()).filter(Boolean),
              limit_per_sub: parseInt(redditLimit) || 20,
            }))}
          >
            <Field
              label="Subreddits (comma separated)"
              value={subreddits}
              onChange={setSubreddits}
              placeholder="stripe, techsupport, notion"
              hint="Posts with bug/issue/help keywords are auto-filtered"
            />
            <Field
              label="Posts per subreddit"
              value={redditLimit}
              onChange={setRedditLimit}
              placeholder="20"
              hint="Requires REDDIT_CLIENT_ID + REDDIT_CLIENT_SECRET in .env"
            />
          </SourceCard>

          {/* App Store */}
          <SourceCard
            icon="📱"
            title="App Store Reviews"
            description="Pulls 1-2 star reviews · Apple (free RSS) + Google Play"
            status={status.appstore?.status}
            lastCount={status.appstore?.last_count}
            lastRun={status.appstore?.last_run}
            loading={loading.appstore}
            onTrigger={() => trigger('appstore', () => triggerAppStoreIngest({
              apple_app_id: appleId.trim() || null,
              google_app_id: googleId.trim() || null,
            }))}
          >
            <Field
              label="Apple App Store ID"
              value={appleId}
              onChange={setAppleId}
              placeholder="e.g. 1232780281 (Notion)"
              hint="Find in the app's App Store URL — no API key needed"
            />
            <Field
              label="Google Play Package ID"
              value={googleId}
              onChange={setGoogleId}
              placeholder="e.g. notion.id"
              hint="Package name from the Play Store URL"
            />
          </SourceCard>

          {/* Email IMAP */}
          <SourceCard
            icon="✉️"
            title="Email — IMAP"
            description="Reads unread emails from Gmail or Outlook · auto-creates tickets"
            status={status.email?.status}
            lastCount={status.email?.last_count}
            lastRun={status.email?.last_run}
            loading={loading.email}
            onTrigger={() => trigger('email', () => triggerEmailIngest({ max_emails: parseInt(maxEmails) || 20 }))}
          >
            <Field
              label="Max emails to fetch"
              value={maxEmails}
              onChange={setMaxEmails}
              placeholder="20"
              hint="Requires EMAIL_ADDRESS + EMAIL_APP_PASSWORD in backend/.env"
            />
            <div style={{ fontSize: '0.74rem', color: 'var(--text3)', background: 'var(--bg4)', borderRadius: 8, padding: '8px 12px', lineHeight: 1.7 }}>
              <strong style={{ color: 'var(--text2)' }}>Gmail setup:</strong> myaccount.google.com → Security → App Passwords<br />
              IMAP_HOST defaults to <code style={{ color: 'var(--blue)' }}>imap.gmail.com</code> · Outlook: <code style={{ color: 'var(--blue)' }}>outlook.office365.com</code>
            </div>
          </SourceCard>

          {/* Whisper Voice — info card */}
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
              <div style={{
                width: 44, height: 44, borderRadius: 11, background: 'var(--bg4)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.4rem', flexShrink: 0,
              }}>🎙️</div>
              <div>
                <div style={{ fontWeight: 700, fontSize: '0.95rem', marginBottom: 3 }}>Voice Note Transcription (Whisper)</div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text3)' }}>Upload audio → Whisper AI transcribes → runs full pipeline</div>
              </div>
            </div>
            <div style={{ fontSize: '0.82rem', color: 'var(--text2)', lineHeight: 1.8, marginBottom: 12 }}>
              ✅ <strong>Available now</strong> on the <strong>Submit Ticket</strong> page<br />
              Supported formats: <code style={{ color: 'var(--blue)' }}>.mp3 .wav .ogg .m4a .webm .flac</code><br />
              Model: <code style={{ color: 'var(--blue)' }}>whisper-base</code> · runs locally, no API key
            </div>
            <div style={{ fontSize: '0.74rem', color: 'var(--text3)', background: 'var(--bg4)', borderRadius: 8, padding: '8px 12px', lineHeight: 1.7 }}>
              <strong style={{ color: 'var(--amber)' }}>First run:</strong> Whisper will download ~145MB base model automatically. Subsequent runs are instant.
            </div>
          </div>

        </div>
      </div>
    </>
  )
}
