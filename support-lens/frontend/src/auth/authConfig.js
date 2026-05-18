/**
 * SupportLens Auth Configuration
 * 
 * Google OAuth:  Any Google account
 * Microsoft SSO: Only @relanto.ai domain accounts
 * 
 * Setup instructions:
 * 1. Google: https://console.cloud.google.com → Create OAuth 2.0 Client ID
 *    - Add http://localhost:5173 to Authorized JavaScript origins
 * 2. Microsoft: https://portal.azure.com → Azure Active Directory → App registrations
 *    - Add http://localhost:5173 as redirect URI (SPA)
 *    - Set "Supported account types" = "Accounts in any organizational directory"
 */

// ── Google OAuth ─────────────────────────────────────────────────────────────
export const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || 'YOUR_GOOGLE_CLIENT_ID'

// ── Microsoft MSAL ───────────────────────────────────────────────────────────
export const MICROSOFT_CLIENT_ID = import.meta.env.VITE_MICROSOFT_CLIENT_ID || 'YOUR_MICROSOFT_CLIENT_ID'
export const MICROSOFT_TENANT_ID = import.meta.env.VITE_MICROSOFT_TENANT_ID || 'common'

// Only allow email addresses from this domain for Microsoft login
export const ALLOWED_MICROSOFT_DOMAIN = 'relanto.ai'

export const msalConfig = {
  auth: {
    clientId: MICROSOFT_CLIENT_ID,
    authority: `https://login.microsoftonline.com/${MICROSOFT_TENANT_ID}`,
    redirectUri: window.location.origin,
    postLogoutRedirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: 'sessionStorage',
    storeAuthStateInCookie: false,
  },
  system: {
    loggerOptions: {
      loggerCallback: () => {},
      piiLoggingEnabled: false,
    },
  },
}

export const msalLoginRequest = {
  scopes: ['openid', 'profile', 'email', 'User.Read'],
  prompt: 'select_account',
}
