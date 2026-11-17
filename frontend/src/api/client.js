const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export const getAuthToken = () => {
  return localStorage.getItem('helpdesk_token')
}

export const setAuthToken = (token) => {
  if (token) {
    localStorage.setItem('helpdesk_token', token)
  } else {
    localStorage.removeItem('helpdesk_token')
  }
}

export async function apiRequest(endpoint, options = {}) {
  const url = endpoint.startsWith('http') ? endpoint : `${BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`
  const headers = new Headers(options.headers || {})

  const token = getAuthToken()
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  // Set default JSON Content-Type if body is not FormData
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(url, {
    ...options,
    headers,
  })

  if (response.status === 401) {
    if (!endpoint.includes('/auth/login')) {
      setAuthToken(null)
      window.dispatchEvent(new CustomEvent('auth:unauthorized'))
    }
  }

  if (response.status === 204) {
    return null
  }

  const contentType = response.headers.get('content-type') || ''
  let data
  if (contentType.includes('application/json')) {
    data = await response.json()
  } else {
    data = await response.text()
  }

  if (!response.ok) {
    let errorMsg = 'Đã có lỗi xảy ra'
    if (data && typeof data === 'object') {
      if (typeof data.detail === 'string') {
        errorMsg = data.detail
      } else if (Array.isArray(data.detail)) {
        errorMsg = data.detail.map((d) => d.msg || JSON.stringify(d)).join(', ')
      } else if (data.message) {
        errorMsg = data.message
      }
    }
    const error = new Error(errorMsg)
    error.status = response.status
    error.data = data
    throw error
  }

  return data
}
