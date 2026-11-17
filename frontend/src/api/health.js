import { apiRequest } from './client'

export const healthApi = {
  async getHealth() {
    return await apiRequest('/health')
  },
}

