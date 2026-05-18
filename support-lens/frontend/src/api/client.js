import axios from 'axios'

const api = axios.create({ baseURL: '/api', timeout: 120000 })

// Tickets
export const getTickets = (params = {}) => api.get('/tickets/', { params })
export const getTicket = (id) => api.get(`/tickets/${id}`)
export const createTicket = (data) => api.post('/tickets/', data)
export const createTicketSync = (data) => api.post('/tickets/process-sync', data)
export const updateTicket = (id, data) => api.patch(`/tickets/${id}`, data)
export const getTicketSuggestions = (id) => api.get(`/tickets/${id}/suggestions`)
export const getDraftReply = (ticketId, agentId = 'agent-1') =>
  api.post('/tickets/draft-reply', { ticket_id: ticketId, agent_id: agentId })

// Manager
export const getDashboard = () => api.get('/manager/dashboard')
export const askManager = (question) => api.post('/manager/ask', { question })
export const getClusters = () => api.get('/manager/clusters')
export const getAgentStats = () => api.get('/manager/agents/stats')
export const getWeeklyDigest = () => api.get('/manager/weekly-digest')
export const getManagerAlerts = () => api.get('/manager/alerts')
export const dismissAlert = (id) => api.delete(`/manager/alerts/${id}`)

// Insights
export const getHeatmap = () => api.get('/insights/heatmap')
export const getSLABreakdown = () => api.get('/insights/sla-breakdown')
export const getSentimentTrend = () => api.get('/insights/sentiment-trend')
export const getCSATForecast = () => api.get('/insights/csat-forecast')

// Solution Engine
export const getSolution = (data) => api.post('/api/solution', data)
export const submitSolutionFeedback = (data) => api.post('/api/solution/feedback', data)

// Voice Transcription
export const transcribeAudio = (formData) => api.post('/voice/transcribe', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
  timeout: 300000,  // 5 min — Whisper can be slow on first run
})

// Ingestion
export const triggerRedditIngest = (data) => api.post('/ingest/reddit', data)
export const triggerAppStoreIngest = (data) => api.post('/ingest/appstore', data)
export const triggerEmailIngest = (data) => api.post('/ingest/email', data)
export const getIngestStatus = () => api.get('/ingest/status')

// Health
export const getHealth = () => api.get('/health')

export default api

