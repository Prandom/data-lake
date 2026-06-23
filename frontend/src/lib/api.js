/**
 * API client for communicating with the FastAPI backend.
 *
 * All requests go through the Vite proxy (/api → localhost:8000).
 * Auth tokens are automatically injected from the Firebase user.
 */

import { auth } from '@/lib/firebase'

const BASE_URL = '/api'

class ApiError extends Error {
  constructor(message, status, data) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}

/**
 * Get the current Firebase ID token for authenticated requests.
 * Returns null if the user is not signed in.
 */
async function _getToken() {
  const user = auth.currentUser
  if (!user) return null
  try {
    return await user.getIdToken()
  } catch {
    return null
  }
}

async function request(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`
  const token = await _getToken()

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  // Inject Bearer token if available
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const config = {
    ...options,
    headers,
  }

  const response = await fetch(url, config)

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new ApiError(
      data.error || `Request failed with status ${response.status}`,
      response.status,
      data
    )
  }

  return response.json()
}

/**
 * Send a query to the agent and get a response.
 */
export async function queryAgent(query) {
  return request('/agent/query', {
    method: 'POST',
    body: JSON.stringify({ query }),
  })
}

/**
 * Get the current system status (connected sources, etc.)
 */
export async function getStatus() {
  return request('/status')
}

/**
 * Get sync status and stats.
 */
export async function getSyncStatus() {
  return request('/sync/status')
}

/**
 * Trigger a manual sync.
 */
export async function triggerSync() {
  return request('/sync/trigger', { method: 'POST' })
}

/**
 * Get the system health.
 */
export async function getHealth() {
  return request('/health')
}

export { ApiError }
