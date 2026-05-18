import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import AgentView from './pages/AgentView'
import ManagerDashboard from './pages/ManagerDashboard'
import ManagerAnalytics from './pages/ManagerAnalytics'
import TicketInbox from './pages/TicketInbox'
import WeeklyDigest from './pages/WeeklyDigest'
import DataSources from './pages/DataSources'
import LoginPage from './pages/LoginPage'
import { useAuth } from './auth/AuthContext'
import { getHealth, getTickets } from './api/client'

function UserAvatar({ user, onLogout }) {
  const [open, setOpen] = useState(false)
  const initials = user.name?.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || '??'

  return (
    <div style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          display: 'flex', alignItems: 'center', gap: 9, width: '100%',
          background: 'transparent', border: 'none', cursor: 'pointer',
          padding: '8px 0', borderRadius: 10,
        }}
      >
        {user.picture ? (
          <img src={user.picture} alt={user.name} style={{ width: 32, height: 32, borderRadius: '50%', border: '2px solid var(--border2)', flexShrink: 0 }} />
        ) : (
          <div style={{
            width: 32, height: 32, borderRadius: '50%', flexShrink: 0,
            background: 'linear-gradient(135deg, var(--blue), var(--purple))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '0.72rem', fontWeight: 800, color: '#fff',
            border: '2px solid var(--border2)',
          }}>{initials}</div>
        )}
        <div style={{ flex: 1, textAlign: 'left', overflow: 'hidden' }}>
          <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {user.name?.split(' ')[0] || 'User'}
          </div>
          <div style={{ fontSize: '0.64rem', color: 'var(--text3)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {user.provider === 'microsoft' ? '🏢' : '🔵'} {user.email}
          </div>
        </div>
        <span style={{ color: 'var(--text3)', fontSize: '0.7rem', flexShrink: 0 }}>▾</span>
      </button>

      {open && (
        <>
          <div style={{ position: 'fixed', inset: 0, zIndex: 999 }} onClick={() => setOpen(false)} />
          <div style={{
            position: 'absolute', bottom: '110%', left: 0, right: 0, zIndex: 1000,
            background: 'var(--bg4)', border: '1px solid var(--border2)',
            borderRadius: 12, padding: 8, boxShadow: 'var(--shadow)',
          }}>
            <div style={{ padding: '8px 12px', fontSize: '0.75rem', color: 'var(--text3)', borderBottom: '1px solid var(--border)', marginBottom: 6 }}>
              Signed in via <strong style={{ color: 'var(--text2)' }}>{user.provider}</strong>
            </div>
            <button
              onClick={() => { setOpen(false); onLogout() }}
              style={{
                width: '100%', padding: '8px 12px', background: 'transparent',
                border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center',
                gap: 8, fontSize: '0.82rem', color: 'var(--red)', borderRadius: 8,
                fontFamily: 'var(--font)', textAlign: 'left',
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--red-dim)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              ⎋ Sign out
            </button>
          </div>
        </>
      )}
    </div>
  )
}

function Sidebar({ health, urgentCount, user, onLogout }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-logo">
          <div className="brand-icon">🔍</div>
          <div>
            <div className="brand-name">SupportLens</div>
            <div className="brand-sub">AI Intelligence</div>
          </div>
        </div>
        <div className="status-row">
          <div className={`dot ${health?.ollama_connected ? 'dot-green' : 'dot-amber'}`} />
          <span className="status-text">
            {health?.ollama_connected ? `${health.ollama_model} · connected` : 'Connecting to Ollama…'}
          </span>
        </div>
      </div>

      <span className="nav-label">Agent Workspace</span>
      <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
        <span className="nav-icon">🎯</span>
        Urgency Queue
        {urgentCount > 0 && <span className="nav-count">{urgentCount}</span>}
      </NavLink>
      <NavLink to="/inbox" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
        <span className="nav-icon">📥</span>
        Submit Ticket
      </NavLink>

      <span className="nav-label" style={{ marginTop: 8 }}>Manager View</span>
      <NavLink to="/dashboard" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
        <span className="nav-icon">📊</span>
        Dashboard
      </NavLink>
      <NavLink to="/analytics" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
        <span className="nav-icon">📈</span>
        Analytics
      </NavLink>
      <NavLink to="/digest" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
        <span className="nav-icon">📋</span>
        Weekly Digest
      </NavLink>
      <NavLink to="/sources" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
        <span className="nav-icon">📡</span>
        Data Sources
      </NavLink>

      {health && (
        <div className="sidebar-footer">
          <div className="sidebar-stat"><span>Tickets</span><span>{health.tickets_count}</span></div>
          <div className="sidebar-stat"><span>KB Articles</span><span>{health.kb_articles_count}</span></div>
          <div className="sidebar-stat">
            <span>RAG Index</span>
            <span style={{ color: health.rag_index_ready ? 'var(--green)' : 'var(--amber)' }}>
              {health.rag_index_ready ? '✓ Ready' : 'Building…'}
            </span>
          </div>
          <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
            <UserAvatar user={user} onLogout={onLogout} />
          </div>
        </div>
      )}

      {/* Show user avatar even when health isn't loaded */}
      {!health && user && (
        <div className="sidebar-footer">
          <UserAvatar user={user} onLogout={onLogout} />
        </div>
      )}
    </aside>
  )
}

export default function App() {
  const { user, loading, logout } = useAuth()
  const [health, setHealth] = useState(null)
  const [urgentCount, setUrgentCount] = useState(0)

  useEffect(() => {
    if (!user) return
    const poll = async () => {
      try {
        const [hRes, tRes] = await Promise.all([
          getHealth(),
          getTickets({ status: 'open', sort_by: 'urgency_score', limit: 100 })
        ])
        setHealth(hRes.data)
        const urgent = tRes.data.filter(t => t.urgency_score >= 65 || t.is_churn_risk)
        setUrgentCount(urgent.length)
      } catch {}
    }
    poll()
    const t = setInterval(poll, 30000)
    return () => clearInterval(t)
  }, [user])

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', background: '#070810', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <div className="spinner" style={{ width: 40, height: 40, margin: '0 auto 16px' }} />
          <div style={{ color: 'var(--text3)', fontSize: '0.88rem' }}>Loading…</div>
        </div>
      </div>
    )
  }

  if (!user) {
    return <LoginPage />
  }

  return (
    <BrowserRouter>
      <div className="app">
        <Sidebar health={health} urgentCount={urgentCount} user={user} onLogout={logout} />
        <main className="main">
          <Routes>
            <Route path="/" element={<AgentView />} />
            <Route path="/inbox" element={<TicketInbox />} />
            <Route path="/dashboard" element={<ManagerDashboard />} />
            <Route path="/analytics" element={<ManagerAnalytics />} />
            <Route path="/digest" element={<WeeklyDigest />} />
            <Route path="/sources" element={<DataSources />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
