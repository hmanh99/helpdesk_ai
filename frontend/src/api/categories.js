import { apiRequest } from './client'

export const categoriesApi = {
  async listCategories(params = {}) {
    const query = new URLSearchParams()
    if (params.department_id) query.append('department_id', params.department_id)
    if (params.active_only !== undefined) query.append('active_only', params.active_only)
    if (params.skip !== undefined) query.append('skip', params.skip)
    if (params.limit !== undefined) query.append('limit', params.limit)

    const qs = query.toString()
    return await apiRequest(`/categories${qs ? `?${qs}` : ''}`)
  },

  async getCategory(id) {
    return await apiRequest(`/categories/${id}`)
  },

  async createCategory(data) {
    return await apiRequest('/categories', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  async updateCategory(id, data) {
    return await apiRequest(`/categories/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  },

  async deleteCategory(id) {
    return await apiRequest(`/categories/${id}`, {
      method: 'DELETE',
    })
  },
}

