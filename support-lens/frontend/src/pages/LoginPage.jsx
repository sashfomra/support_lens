import { useState, useEffect } from 'react'
import { useGoogleLogin } from '@react-oauth/google'
import { useMsal } from '@azure/msal-react'
import { useAuth } from '../auth/AuthContext'
import { msalLoginRequest, ALLOWED_MICROSOFT_DOMAIN } from '../auth/authConfig'

const PARTICLES = Array.from({ length: 22 }, (_, i) => ({
  id: i,
  x: Math.random() * 100,
  y: Math.random() * 100,
  size: 1.5 + Math.random() * 3,
  delay: Math.random() * 5,
  duration: 4 + Math.random() * 6,
}))

function FloatingParticle({ x, y, size, delay, duration }) {
  return (
    <div
      style={{
        position: 'absolute',
        left: `${x}%`,
        top: `${y}%`,
        width: size,
        height: size,
        borderRadius: '50%',
        background: 'rgba(79,142,247,0.4)',
        animation: `float-particle ${duration}s ${delay}s ease-in-out infinite alternate`,
        pointerEvents: 'none',
      }}
    />
  )
}

export default function LoginPage() {
  const { loginWithGoogle, loginWithMicrosoft } = useAuth()
  const { instance } = useMsal()
  const [error, setError] = useState(null)
  const [loadingProvider, setLoadingProvider] = useState(null)
  const [mounted, setMounted] = useState(false)

  useEffect(() => { setTimeout(() => setMounted(true), 50) }, [])

  // ── Google ──────────────────────────────────────────────────────────────────
  const handleGoogleLogin = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      try {
        const res = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
          headers: { Authorization: `Bearer ${tokenResponse.access_token}` },
        })
        const profile = await res.json()
        loginWithGoogle({
          name: profile.name,
          email: profile.email,
          picture: profile.picture,
          credential: tokenResponse.access_token,
        })
      } catch {
        setError('Failed to fetch Google profile. Please try again.')
      }
      setLoadingProvider(null)
    },
    onError: () => {
      setError('Google sign-in was cancelled or failed.')
      setLoadingProvider(null)
    },
  })

  const onGoogleClick = () => {
    setError(null)
    setLoadingProvider('google')
    handleGoogleLogin()
  }

  // ── Microsoft ────────────────────────────────────────────────────────────────
  const onMicrosoftClick = async () => {
    setError(null)
    setLoadingProvider('microsoft')
    try {
      const result = await instance.loginPopup(msalLoginRequest)
      loginWithMicrosoft(result.account)
    } catch (e) {
      if (e.message?.includes('Only @')) {
        setError(e.message)
      } else if (e.errorCode === 'user_cancelled') {
        setError('Microsoft sign-in was cancelled.')
      } else {
        setError('Microsoft sign-in failed. Please try again.')
      }
    }
    setLoadingProvider(null)
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'radial-gradient(ellipse at 20% 50%, rgba(79,142,247,0.12) 0%, transparent 60%), radial-gradient(ellipse at 80% 20%, rgba(124,92,252,0.1) 0%, transparent 55%), #070810',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: 'var(--font)',
      position: 'relative',
      overflow: 'hidden',
    }}>

      {/* Animated grid lines */}
      <div style={{
        position: 'absolute', inset: 0, opacity: 0.04,
        backgroundImage: 'linear-gradient(var(--border) 1px, transparent 1px), linear-gradient(90deg, var(--border) 1px, transparent 1px)',
        backgroundSize: '50px 50px',
        pointerEvents: 'none',
      }} />

      {/* Floating particles */}
      {PARTICLES.map(p => <FloatingParticle key={p.id} {...p} />)}

      {/* Glow orbs */}
      <div style={{ position:'absolute', width:600, height:600, borderRadius:'50%', background:'radial-gradient(circle, rgba(79,142,247,0.08) 0%, transparent 70%)', top:'10%', left:'-10%', pointerEvents:'none' }} />
      <div style={{ position:'absolute', width:500, height:500, borderRadius:'50%', background:'radial-gradient(circle, rgba(124,92,252,0.07) 0%, transparent 70%)', bottom:'0%', right:'-5%', pointerEvents:'none' }} />

      {/* Login card */}
      <div style={{
        width: '100%',
        maxWidth: 440,
        margin: '0 20px',
        opacity: mounted ? 1 : 0,
        transform: mounted ? 'translateY(0)' : 'translateY(24px)',
        transition: 'all 0.5s cubic-bezier(0.16, 1, 0.3, 1)',
      }}>
        {/* Brand */}
        <div style={{ textAlign: 'center', marginBottom: 36 }}>
          <div style={{
            width: 68, height: 68, borderRadius: 18,
            background: 'linear-gradient(135deg, #4f8ef7, #7c5cfc)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 30, margin: '0 auto 18px',
            boxShadow: '0 0 40px rgba(79,142,247,0.35), 0 8px 32px rgba(0,0,0,0.4)',
          }}>🔍</div>
          <div style={{ fontSize: '1.85rem', fontWeight: 900, letterSpacing: '-0.03em', color: '#eef0ff', marginBottom: 6 }}>
            SupportLens
          </div>
          <div style={{ fontSize: '0.88rem', color: '#4a5070', fontWeight: 500 }}>
            AI Support Intelligence Platform
          </div>
        </div>

        {/* Card */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(24,27,39,0.95), rgba(18,20,31,0.98))',
          border: '1px solid rgba(255,255,255,0.07)',
          borderRadius: 24,
          padding: '36px 32px',
          backdropFilter: 'blur(24px)',
          boxShadow: '0 24px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(79,142,247,0.08)',
        }}>
          <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#eef0ff', marginBottom: 6 }}>
            Sign in to continue
          </div>
          <div style={{ fontSize: '0.8rem', color: '#4a5070', marginBottom: 28, lineHeight: 1.6 }}>
            Use your Google account or your <strong style={{ color: '#8b92b8' }}>@relanto.ai</strong> Microsoft account
          </div>

          {/* Error */}
          {error && (
            <div style={{
              background: 'rgba(244,63,94,0.1)', border: '1px solid rgba(244,63,94,0.3)',
              borderRadius: 10, padding: '11px 14px', marginBottom: 18,
              fontSize: '0.82rem', color: '#f43f5e', lineHeight: 1.55,
              display: 'flex', gap: 8, alignItems: 'flex-start',
            }}>
              <span style={{ flexShrink: 0, marginTop: 1 }}>⚠</span>
              <span>{error}</span>
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Google Button */}
            <button
              onClick={onGoogleClick}
              disabled={!!loadingProvider}
              style={{
                width: '100%', padding: '13px 20px',
                borderRadius: 12, border: '1px solid rgba(255,255,255,0.1)',
                background: loadingProvider === 'google'
                  ? 'rgba(255,255,255,0.05)'
                  : 'rgba(255,255,255,0.04)',
                color: '#eef0ff', cursor: loadingProvider ? 'not-allowed' : 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12,
                fontSize: '0.92rem', fontWeight: 600, fontFamily: 'var(--font)',
                transition: 'all 0.2s',
                opacity: loadingProvider && loadingProvider !== 'google' ? 0.4 : 1,
              }}
              onMouseEnter={e => { if (!loadingProvider) { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.18)' }}}
              onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)' }}
            >
              {loadingProvider === 'google' ? (
                <span className="spinner" style={{ width: 18, height: 18 }} />
              ) : (
                <svg width="20" height="20" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
              )}
              {loadingProvider === 'google' ? 'Signing in…' : 'Continue with Google'}
            </button>

            {/* Divider */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '2px 0' }}>
              <div style={{ flex: 1, height: 1, background: 'rgba(255,255,255,0.07)' }} />
              <span style={{ fontSize: '0.72rem', color: '#2a2e45', fontWeight: 600, letterSpacing: '0.05em' }}>OR</span>
              <div style={{ flex: 1, height: 1, background: 'rgba(255,255,255,0.07)' }} />
            </div>

            {/* Microsoft Button */}
            <button
              onClick={onMicrosoftClick}
              disabled={!!loadingProvider}
              style={{
                width: '100%', padding: '13px 20px',
                borderRadius: 12, border: '1px solid rgba(0,114,240,0.25)',
                background: loadingProvider === 'microsoft'
                  ? 'rgba(0,114,240,0.08)'
                  : 'rgba(0,114,240,0.05)',
                color: '#eef0ff', cursor: loadingProvider ? 'not-allowed' : 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12,
                fontSize: '0.92rem', fontWeight: 600, fontFamily: 'var(--font)',
                transition: 'all 0.2s',
                opacity: loadingProvider && loadingProvider !== 'microsoft' ? 0.4 : 1,
              }}
              onMouseEnter={e => { if (!loadingProvider) { e.currentTarget.style.background = 'rgba(0,114,240,0.12)'; e.currentTarget.style.borderColor = 'rgba(0,114,240,0.4)' }}}
              onMouseLeave={e => { e.currentTarget.style.background = 'rgba(0,114,240,0.05)'; e.currentTarget.style.borderColor = 'rgba(0,114,240,0.25)' }}
            >
              {loadingProvider === 'microsoft' ? (
                <span className="spinner" style={{ width: 18, height: 18 }} />
              ) : (
                <svg width="20" height="20" viewBox="0 0 23 23">
                  <rect x="1" y="1" width="10" height="10" fill="#F25022"/>
                  <rect x="12" y="1" width="10" height="10" fill="#7FBA00"/>
                  <rect x="1" y="12" width="10" height="10" fill="#00A4EF"/>
                  <rect x="12" y="12" width="10" height="10" fill="#FFB900"/>
                </svg>
              )}
              {loadingProvider === 'microsoft' ? 'Signing in…' : 'Continue with Microsoft'}
            </button>
          </div>

          {/* Microsoft domain note */}
          <div style={{
            marginTop: 20, padding: '10px 14px',
            background: 'rgba(0,114,240,0.06)', border: '1px solid rgba(0,114,240,0.15)',
            borderRadius: 10, display: 'flex', alignItems: 'flex-start', gap: 9,
          }}>
            <span style={{ fontSize: '0.9rem', flexShrink: 0, marginTop: 1 }}>🏢</span>
            <div style={{ fontSize: '0.76rem', color: '#4a5070', lineHeight: 1.6 }}>
              Microsoft login is restricted to{' '}
              <strong style={{ color: '#4f8ef7' }}>@{ALLOWED_MICROSOFT_DOMAIN}</strong>{' '}
              accounts only. Other accounts will be rejected.
            </div>
          </div>
        </div>

        {/* Footer */}
        <div style={{ textAlign: 'center', marginTop: 24, fontSize: '0.73rem', color: '#2a2e45' }}>
          Relanto Hackathon 2026 · SupportLens AI Intelligence
        </div>
      </div>

      <style>{`
        @keyframes float-particle {
          from { transform: translateY(0px) translateX(0px); opacity: 0.3; }
          to   { transform: translateY(-20px) translateX(10px); opacity: 0.7; }
        }
      `}</style>
    </div>
  )
}
