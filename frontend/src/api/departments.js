import { apiRequest } from './client'

export const departmentsApi = {
  async listDepartments(skip = 0, limit = 100) {
    return await apiRequest(`/departments?skip=${skip}&limit=${limit}`)
  },

  async getDepartment(id) {
    return await apiRequest(`/departments/${id}`)
  },

  async createDepartment(data) {
    return await apiRequest('/departments', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  async getDepartmentMembers(id) {
    return await apiRequest(`/departments/${id}/members`)
  },
}

