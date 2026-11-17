import React, { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import { Icon } from '../common/Icons'

export function AuthPage() {
  const [isLogin, setIsLogin] = useState(true)
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const { login, register } = useAuth()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (!email || !password) {
      setError('Vui lòng điền đầy đủ email và mật khẩu')
      return
    }

    const trimmedEmail = email.trim().toLowerCase()
    if (!trimmedEmail.endsWith('@st.neu.edu.vn') || trimmedEmail === '@st.neu.edu.vn') {
      setError('Hệ thống chỉ chấp nhận tài khoản có đuôi email @st.neu.edu.vn (Ví dụ: sinhvien@st.neu.edu.vn)')
      return
    }

    if (!isLogin) {
      if (!fullName.trim()) {
        setError('Vui lòng nhập họ và tên')
        return
      }
      if (password.length < 8) {
        setError('Mật khẩu phải có ít nhất 8 ký tự')
        return
      }
      if (password !== confirmPassword) {
        setError('Mật khẩu xác nhận không khớp')
        return
      }
    }

    setLoading(true)
    try {
      if (isLogin) {
        await login(email, password)
      } else {
        await register(email, fullName, password)
        setIsLogin(true)
        setPassword('')
        setConfirmPassword('')
      }
    } catch (err) {
      setError(err.message || 'Thao tác thất bại. Vui lòng thử lại.')
    } finally {
      setLoading(false)
    }
  }

  const handleQuickLogin = async (demoEmail, demoPass) => {
    setEmail(demoEmail)
    setPassword(demoPass)
    setIsLogin(true)
    setError('')
    setLoading(true)
    try {
      await login(demoEmail, demoPass)
    } catch (err) {
      setError(err.message || 'Đăng nhập tài khoản mẫu thất bại')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-background-glow">
        <div className="glow-circle glow-1"></div>
        <div className="glow-circle glow-2"></div>
      </div>

      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-uni-badge">
            🏛️ ĐẠI HỌC KINH TẾ QUỐC DÂN (NEU)
          </div>
          <div className="auth-icon-wrap">
            <Icon name="bot" size={32} />
          </div>
          <h1 className="auth-title">NEU Helpdesk AI</h1>
          <p className="auth-subtitle">
            Hệ thống hỗ trợ tự động thông minh tích hợp RAG & Quản lý Ticket chuyên nghiệp
          </p>
        </div>

        <div className="auth-tabs">
          <button
            type="button"
            className={`auth-tab ${isLogin ? 'active' : ''}`}
            onClick={() => {
              setIsLogin(true)
              setError('')
            }}
          >
            Đăng nhập hệ thống
          </button>
          <button
            type="button"
            className={`auth-tab ${!isLogin ? 'active' : ''}`}
            onClick={() => {
              setIsLogin(false)
              setError('')
            }}
          >
            Đăng ký tài khoản
          </button>
        </div>

        {error && (
          <div className="alert alert-error">
            <Icon name="alertCircle" size={16} />
            <div className="alert-text">
              <span>{error}</span>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          {!isLogin && (
            <div className="form-group">
              <label className="form-label">Họ và tên sinh viên / Cán bộ</label>
              <input
                type="text"
                className="form-input"
                placeholder="Nguyễn Văn A"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required={!isLogin}
              />
            </div>
          )}

          <div className="form-group">
            <label className="form-label">Địa chỉ Email (@st.neu.edu.vn)</label>
            <input
              type="email"
              className="form-input"
              placeholder="sinhvien@st.neu.edu.vn"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <span className="form-hint">Hệ thống chỉ chấp nhận email trường có đuôi @st.neu.edu.vn</span>
          </div>

          <div className="form-group">
            <label className="form-label">Mật khẩu</label>
            <input
              type="password"
              className="form-input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            {!isLogin && (
              <span className="form-hint">Tối thiểu 8 ký tự</span>
            )}
          </div>

          {!isLogin && (
            <div className="form-group">
              <label className="form-label">Xác nhận mật khẩu</label>
              <input
                type="password"
                className="form-input"
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required={!isLogin}
              />
            </div>
          )}

          <button
            type="submit"
            className="btn btn-primary btn-block btn-lg"
            disabled={loading}
          >
            {loading ? (
              <span className="spinner"></span>
            ) : isLogin ? (
              'Đăng nhập tài khoản'
            ) : (
              'Tạo tài khoản mới'
            )}
          </button>
        </form>

        <div className="auth-quick-login">
          <span className="quick-login-title">⚡ Đăng nhập nhanh tài khoản mẫu:</span>
          <div className="quick-login-badges">
            <button
              type="button"
              className="chip-btn"
              onClick={() => handleQuickLogin('admin@st.neu.edu.vn', 'Admin@123')}
            >
              👑 Quản trị viên (admin@st.neu.edu.vn)
            </button>
            <button
              type="button"
              className="chip-btn"
              onClick={() => handleQuickLogin('manager.nhansu@st.neu.edu.vn', 'Password123!')}
            >
              👔 Trưởng phòng Nhân sự (manager.nhansu@st.neu.edu.vn)
            </button>
            <button
              type="button"
              className="chip-btn"
              onClick={() => handleQuickLogin('student@st.neu.edu.vn', 'Password123!')}
            >
              🎓 Sinh viên (student@st.neu.edu.vn)
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
