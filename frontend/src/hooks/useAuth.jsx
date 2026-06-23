/**
 * useAuth — React hook for Firebase Authentication state.
 *
 * Provides:
 * - user: the Firebase User object (or null)
 * - loading: true while the initial auth state is being resolved
 * - error: any auth error message
 * - loginWithGoogle: triggers Google OAuth popup
 * - loginWithEmail: email + password sign-in
 * - signupWithEmail: email + password account creation
 * - logout: signs the user out
 *
 * Usage:
 *   const { user, loading, loginWithGoogle, logout } = useAuth()
 */

import { useState, useEffect, useCallback, createContext, useContext } from 'react'
import {
  onAuthStateChanged,
  signInWithPopup,
  signInWithRedirect,
  getRedirectResult,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
} from 'firebase/auth'
import { auth, googleProvider } from '@/lib/firebase'

// ─── Context ────────────────────────────────────────────────────────────────
const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Listen to Firebase auth state changes + handle redirect result
  useEffect(() => {
    // Check if we landed back from a redirect sign-in
    getRedirectResult(auth).catch(() => {})

    const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
      setUser(firebaseUser)
      setLoading(false)
    })
    return unsubscribe
  }, [])

  // ── Auth methods ──────────────────────────────────────────────────────────

  const clearError = useCallback(() => setError(null), [])

  const loginWithGoogle = useCallback(async () => {
    try {
      setError(null)
      // Try popup first; fall back to redirect if blocked (e.g. Safari, some configs)
      await signInWithPopup(auth, googleProvider)
    } catch (err) {
      if (
        err?.code === 'auth/popup-blocked' ||
        err?.code === 'auth/popup-closed-by-user' ||
        err?.code === 'auth/cancelled-popup-request'
      ) {
        // Fallback to redirect flow
        await signInWithRedirect(auth, googleProvider)
        return
      }
      setError(_friendlyError(err))
      throw err
    }
  }, [])

  const loginWithEmail = useCallback(async (email, password) => {
    try {
      setError(null)
      await signInWithEmailAndPassword(auth, email, password)
    } catch (err) {
      setError(_friendlyError(err))
      throw err
    }
  }, [])

  const signupWithEmail = useCallback(async (email, password) => {
    try {
      setError(null)
      await createUserWithEmailAndPassword(auth, email, password)
    } catch (err) {
      setError(_friendlyError(err))
      throw err
    }
  }, [])

  const logout = useCallback(async () => {
    try {
      setError(null)
      await signOut(auth)
    } catch (err) {
      setError(_friendlyError(err))
      throw err
    }
  }, [])

  const value = {
    user,
    loading,
    error,
    clearError,
    loginWithGoogle,
    loginWithEmail,
    signupWithEmail,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

/**
 * Hook to access auth state from any component.
 */
export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an <AuthProvider>')
  }
  return context
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Convert Firebase error codes to user-friendly messages.
 */
function _friendlyError(err) {
  const code = err?.code || ''
  const map = {
    'auth/invalid-email':           'Please enter a valid email address.',
    'auth/user-disabled':           'This account has been disabled.',
    'auth/user-not-found':          'No account found with this email.',
    'auth/wrong-password':          'Incorrect password. Please try again.',
    'auth/email-already-in-use':    'An account with this email already exists.',
    'auth/weak-password':           'Password must be at least 6 characters.',
    'auth/popup-closed-by-user':    'Sign-in popup was closed. Please try again.',
    'auth/network-request-failed':  'Network error. Please check your connection.',
    'auth/too-many-requests':       'Too many attempts. Please wait and try again.',
    'auth/invalid-credential':      'Invalid email or password. Please try again.',
    'auth/configuration-not-found': 'Google Sign-In is not enabled. Please enable the Google provider in your Firebase Console → Authentication → Sign-in method.',
    'auth/unauthorized-domain':     'This domain is not authorized. Add it to Firebase Console → Authentication → Settings → Authorized domains.',
    'auth/operation-not-allowed':   'This sign-in method is not enabled. Enable it in Firebase Console → Authentication → Sign-in method.',
  }
  return map[code] || err?.message || 'Something went wrong. Please try again.'
}
