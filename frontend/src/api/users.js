import { apiRequest } from './client'

export const usersApi = {
  async listUsers(params = {}) {
    const query = new URLSearchParams()
    if (params.role) query.append('role', params.role)
    if (params.department_id) query.append('department_id', params.department_id)
    if (params.is_active !== undefined) query.append('is_active', params.is_active)
    if (params.skip !== undefined) query.append('skip', params.skip)
    if (params.limit !== undefined) query.append('limit', params.limit)

    const qs = query.toString()
    return await apiRequest(`/users${qs ? `?${qs}` : ''}`)
  },

  async createUser(data) {
    return await apiRequest('/users', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  async getUser(id) {
    return await apiRequest(`/users/${id}`)
  },

  async updateUser(id, data) {
    return await apiRequest(`/users/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  },

  async deleteUser(id) {
    return await apiRequest(`/users/delete/${id}`, {
      method: 'DELETE',
    })
  },

  async resetPassword(id, newPassword) {
    return await apiRequest(`/users/${id}/reset-password`, {
      method: 'POST',
      body: JSON.stringify({ new_password: newPassword }),
    })
  },
}

