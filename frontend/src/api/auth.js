import { apiRequest, setAuthToken } from './client'

export const authApi = {
  async login(email, password) {
    const data = await apiRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    if (data.access_token) {
      setAuthToken(data.access_token)
    }
    return data
  },

  async register(email, full_name, password) {
    return await apiRequest('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, full_name, password }),
    })
  },

  async getMe() {
    return await apiRequest('/auth/me')
  },

  async changePassword(current_password, new_password) {
    return await apiRequest('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password, new_password }),
    })
  },

  logout() {
    setAuthToken(null)
  },
}

