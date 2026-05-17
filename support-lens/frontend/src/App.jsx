import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import AgentView from './pages/AgentView'
import ManagerDashboard from './pages/ManagerDashboard'
import ManagerAnalytics from './pages/ManagerAnalytics'
import TicketInbox from './pages/TicketInbox'
import WeeklyDigest from './pages/WeeklyDigest'
import { getHealth, getTickets } from './api/client'

function Sidebar({ health, urgentCount }) {
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
            {health?.ollama_connected ? `${health.ollama_model} · connected` : 'Connecting to Ollama...'}
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

      {health && (
        <div className="sidebar-footer">
          <div className="sidebar-stat"><span>Tickets</span><span>{health.tickets_count}</span></div>
          <div className="sidebar-stat"><span>KB Articles</span><span>{health.kb_articles_count}</span></div>
          <div className="sidebar-stat">
            <span>RAG Index</span>
            <span style={{ color: health.rag_index_ready ? 'var(--green)' : 'var(--amber)' }}>
              {health.rag_index_ready ? '✓ Ready' : 'Building...'}
            </span>
          </div>
        </div>
      )}
    </aside>
  )
}

export default function App() {
  const [health, setHealth] = useState(null)
  const [urgentCount, setUrgentCount] = useState(0)

  useEffect(() => {
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
  }, [])

  return (
    <BrowserRouter>
      <div className="app">
        <Sidebar health={health} urgentCount={urgentCount} />
        <main className="main">
          <Routes>
            <Route path="/" element={<AgentView />} />
            <Route path="/inbox" element={<TicketInbox />} />
            <Route path="/dashboard" element={<ManagerDashboard />} />
            <Route path="/analytics" element={<ManagerAnalytics />} />
            <Route path="/digest" element={<WeeklyDigest />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
