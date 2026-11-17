import { apiRequest } from './client'

export const chatApi = {
  async createSession() {
    return await apiRequest('/chat/sessions', {
      method: 'POST',
    })
  },

  async listSessions(skip = 0, limit = 50) {
    return await apiRequest(`/chat/sessions?skip=${skip}&limit=${limit}`)
  },

  async getSession(id) {
    return await apiRequest(`/chat/sessions/${id}`)
  },

  async updateSession(id, title) {
    return await apiRequest(`/chat/sessions/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ title }),
    })
  },

  async deleteSession(id) {
    return await apiRequest(`/chat/sessions/${id}`, {
      method: 'DELETE',
    })
  },

  async sendMessage(id, content) {
    return await apiRequest(`/chat/sessions/${id}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    })
  },

  async submitFeedback(id, resolved) {
    return await apiRequest(`/chat/sessions/${id}/feedback`, {
      method: 'POST',
      body: JSON.stringify({ resolved }),
    })
  },

  async confirmTicket(id, ticketData = null) {
    return await apiRequest(`/chat/sessions/${id}/ticket`, {
      method: 'POST',
      body: ticketData ? JSON.stringify(ticketData) : undefined,
    })
  },
}

