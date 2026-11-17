import { apiRequest } from './client'

export const knowledgeApi = {
  async listDocuments(params = {}) {
    const query = new URLSearchParams()
    if (params.category_id) query.append('category_id', params.category_id)
    if (params.published_only !== undefined) query.append('published_only', params.published_only)
    if (params.status) query.append('status', params.status)
    if (params.skip !== undefined) query.append('skip', params.skip)
    if (params.limit !== undefined) query.append('limit', params.limit)

    const qs = query.toString()
    return await apiRequest(`/knowledge${qs ? `?${qs}` : ''}`)
  },

  async getDocument(id) {
    return await apiRequest(`/knowledge/${id}`)
  },

  async getChunks(id) {
    return await apiRequest(`/knowledge/${id}/chunks`)
  },

  async createDocument(data) {
    return await apiRequest('/knowledge', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  async uploadDocument(formData) {
    return await apiRequest('/knowledge/upload', {
      method: 'POST',
      body: formData,
    })
  },

  async updateDocument(id, data) {
    return await apiRequest(`/knowledge/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  },

  async deleteDocument(id) {
    return await apiRequest(`/knowledge/${id}`, {
      method: 'DELETE',
    })
  },

  async publishDocument(id) {
    return await apiRequest(`/knowledge/${id}/publish`, {
      method: 'POST',
    })
  },

  async unpublishDocument(id) {
    return await apiRequest(`/knowledge/${id}/unpublish`, {
      method: 'POST',
    })
  },

  async reprocessDocument(id) {
    return await apiRequest(`/knowledge/${id}/reprocess`, {
      method: 'POST',
    })
  },
}

