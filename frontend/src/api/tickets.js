import { apiRequest } from './client'

export const ticketsApi = {
  async listTickets(params = {}) {
    const query = new URLSearchParams()
    if (params.status) query.append('status', params.status)
    if (params.category_id) query.append('category_id', params.category_id)
    if (params.department_id) query.append('department_id', params.department_id)
    if (params.unassigned_only !== undefined) query.append('unassigned_only', params.unassigned_only)
    if (params.assigned_to_me !== undefined) query.append('assigned_to_me', params.assigned_to_me)
    if (params.skip !== undefined) query.append('skip', params.skip)
    if (params.limit !== undefined) query.append('limit', params.limit)

    const qs = query.toString()
    return await apiRequest(`/tickets${qs ? `?${qs}` : ''}`)
  },

  async getTicket(id) {
    return await apiRequest(`/tickets/${id}`)
  },

  async createTicket(ticketData) {
    return await apiRequest('/tickets', {
      method: 'POST',
      body: JSON.stringify(ticketData),
    })
  },

  async acceptTicket(id, note = null) {
    return await apiRequest(`/tickets/${id}/accept`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    })
  },

  async assignTicket(id, assigneeId, note = null) {
    return await apiRequest(`/tickets/${id}/assign`, {
      method: 'POST',
      body: JSON.stringify({ assignee_id: assigneeId, note }),
    })
  },

  async updateTicketStatus(id, status, note = null) {
    return await apiRequest(`/tickets/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status, note }),
    })
  },

  async updateTicket(id, data) {
    return await apiRequest(`/tickets/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  },

  async deleteTicket(id) {
    return await apiRequest(`/tickets/${id}`, {
      method: 'DELETE',
    })
  },

  async listComments(id) {
    return await apiRequest(`/tickets/${id}/comments`)
  },

  async addComment(id, { content, is_internal = false }) {
    return await apiRequest(`/tickets/${id}/comments`, {
      method: 'POST',
      body: JSON.stringify({ content, is_internal }),
    })
  },
}

