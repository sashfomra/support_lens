import { createContext, useContext, useState, useEffect } from 'react'
import { ALLOWED_MICROSOFT_DOMAIN } from './authConfig'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Restore session from sessionStorage
    try {
      const saved = sessionStorage.getItem('sl_user')
      if (saved) setUser(JSON.parse(saved))
    } catch {}
    setLoading(false)
  }, [])

  const loginWithGoogle = (googleUser) => {
    const u = {
      name: googleUser.name,
      email: googleUser.email,
      picture: googleUser.picture,
      provider: 'google',
      accessToken: googleUser.credential,
    }
    setUser(u)
    sessionStorage.setItem('sl_user', JSON.stringify(u))
  }

  const loginWithMicrosoft = (msalAccount) => {
    const email = msalAccount.username || msalAccount.idTokenClaims?.email || ''
    if (!email.toLowerCase().endsWith(`@${ALLOWED_MICROSOFT_DOMAIN}`)) {
      throw new Error(`Only @${ALLOWED_MICROSOFT_DOMAIN} accounts are allowed. Got: ${email}`)
    }
    const u = {
      name: msalAccount.name || msalAccount.idTokenClaims?.name || email,
      email,
      picture: null,
      provider: 'microsoft',
      accessToken: msalAccount.idToken,
    }
    setUser(u)
    sessionStorage.setItem('sl_user', JSON.stringify(u))
  }

  const logout = () => {
    setUser(null)
    sessionStorage.removeItem('sl_user')
  }

  return (
    <AuthContext.Provider value={{ user, loading, loginWithGoogle, loginWithMicrosoft, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
