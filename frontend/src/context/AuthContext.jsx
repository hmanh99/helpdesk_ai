import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { authApi } from '../api/auth'
import { getAuthToken, setAuthToken } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [toasts, setToasts] = useState([])

  const addToast = useCallback((message, type = 'info') => {
    const id = Date.now() + Math.random().toString(36).substring(2, 9)
    setToasts((prev) => [...prev, { id, message, type }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 4500)
  }, [])

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const fetchCurrentUser = useCallback(async () => {
    const token = getAuthToken()
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }

    try {
      const userData = await authApi.getMe()
      setUser(userData)
    } catch {
      setUser(null)
      setAuthToken(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchCurrentUser()

    const handleUnauthorized = () => {
      setUser(null)
      addToast('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.', 'error')
    }

    window.addEventListener('auth:unauthorized', handleUnauthorized)
    return () => {
      window.removeEventListener('auth:unauthorized', handleUnauthorized)
    }
  }, [fetchCurrentUser, addToast])

  const login = async (email, password) => {
    const data = await authApi.login(email, password)
    setUser(data.user)
    addToast(`Chào mừng ${data.user.full_name}!`, 'success')
    return data.user
  }

  const register = async (email, fullName, password) => {
    const newUser = await authApi.register(email, fullName, password)
    addToast('Đăng ký tài khoản thành công! Vui lòng đăng nhập.', 'success')
    return newUser
  }

  const logout = () => {
    authApi.logout()
    setUser(null)
    addToast('Đã đăng xuất tài khoản.', 'info')
  }

  const refreshUser = async () => {
    try {
      const userData = await authApi.getMe()
      setUser(userData)
    } catch (err) {
      console.error('Refresh user error:', err)
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        logout,
        refreshUser,
        toasts,
        addToast,
        removeToast,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
