import React, { useState, useEffect } from 'react'
import { authApi } from '../../api/auth'
import { healthApi } from '../../api/health'
import { useAuth } from '../../context/AuthContext'
import { RoleBadge } from '../common/Badge'
import { Icon } from '../common/Icons'

export function ProfileView() {
  const { user, addToast } = useAuth()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [changingPass, setChangingPass] = useState(false)

  // System Health
  const [health, setHealth] = useState(null)
  const [loadingHealth, setLoadingHealth] = useState(false)

  const checkHealth = async () => {
    setLoadingHealth(true)
    try {
      const data = await healthApi.getHealth()
      setHealth(data)
    } catch {
      setHealth({ status: 'unreachable', database: 'error' })
    } finally {
      setLoadingHealth(false)
    }
  }

  useEffect(() => {
    checkHealth()
  }, [])

  const handleChangePassword = async (e) => {
    e.preventDefault()
    if (!currentPassword || !newPassword) {
      addToast('Vui lòng điền mật khẩu hiện tại và mật khẩu mới', 'error')
      return
    }
    if (newPassword.length < 8) {
      addToast('Mật khẩu mới phải có ít nhất 8 ký tự', 'error')
      return
    }
    if (newPassword !== confirmPassword) {
      addToast('Mật khẩu xác nhận không khớp', 'error')
      return
    }

    setChangingPass(true)
    try {
      await authApi.changePassword(currentPassword, newPassword)
      addToast('Đổi mật khẩu thành công!', 'success')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err) {
      addToast(err.message || 'Lỗi đổi mật khẩu', 'error')
    } finally {
      setChangingPass(false)
    }
  }

  return (
    <div className="view-container">
      <div className="view-header">
        <div>
          <h1 className="view-title">Tài khoản & Hệ thống</h1>
          <p className="view-subtitle">
            Thông tin hồ sơ người dùng, bảo mật mật khẩu và giám sát trạng thái dịch vụ AI & CSDL
          </p>
        </div>
      </div>

      <div className="profile-grid">
        {/* User Info Card */}
        <div className="card-box">
          <div className="card-box-header">
            <Icon name="user" size={20} className="text-primary" />
            <h3>Thông tin tài khoản</h3>
          </div>

          <div className="profile-details-list">
            <div className="profile-row">
              <span className="profile-lbl">Họ và tên:</span>
              <span className="profile-val font-semibold">{user?.full_name}</span>
            </div>
            <div className="profile-row">
              <span className="profile-lbl">Email:</span>
              <span className="profile-val font-mono text-sm">{user?.email}</span>
            </div>
            <div className="profile-row">
              <span className="profile-lbl">Vai trò phân quyền:</span>
              <span className="profile-val">
                <RoleBadge role={user?.role} />
              </span>
            </div>
            <div className="profile-row">
              <span className="profile-lbl">Phòng ban phụ trách:</span>
              <span className="profile-val">
                {user?.department ? `🏢 ${user.department.name}` : 'Không có (Người dùng chung)'}
              </span>
            </div>
            <div className="profile-row">
              <span className="profile-lbl">Ngày tạo tài khoản:</span>
              <span className="profile-val text-muted text-sm">
                {user?.created_at ? new Date(user.created_at).toLocaleString('vi-VN') : '—'}
              </span>
            </div>
            <div className="profile-row">
              <span className="profile-lbl">Đăng nhập gần nhất:</span>
              <span className="profile-val text-muted text-sm">
                {user?.last_login_at
                  ? new Date(user.last_login_at).toLocaleString('vi-VN')
                  : 'Hiện tại'}
              </span>
            </div>
          </div>
        </div>

        {/* Change Password Card */}
        <div className="card-box">
          <div className="card-box-header">
            <Icon name="key" size={20} className="text-amber" />
            <h3>Đổi mật khẩu</h3>
          </div>

          <form onSubmit={handleChangePassword} className="generic-form">
            <div className="form-group">
              <label className="form-label">Mật khẩu hiện tại</label>
              <input
                type="password"
                className="form-input"
                placeholder="••••••••"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Mật khẩu mới (tối thiểu 8 ký tự)</label>
              <input
                type="password"
                className="form-input"
                placeholder="••••••••"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Xác nhận mật khẩu mới</label>
              <input
                type="password"
                className="form-input"
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
            </div>
            <button type="submit" className="btn btn-primary" disabled={changingPass}>
              {changingPass ? <span className="spinner"></span> : <Icon name="check" size={16} />}
              <span>Cập nhật mật khẩu</span>
            </button>
          </form>
        </div>

        {/* System Health Card */}
        <div className="card-box full-width">
          <div className="card-box-header space-between">
            <div className="d-flex align-center gap-2">
              <Icon name="shield" size={20} className="text-green" />
              <h3>Giám sát trạng thái Hệ thống Helpdesk AI</h3>
            </div>
            <button
              className="btn btn-outline btn-sm"
              onClick={checkHealth}
              disabled={loadingHealth}
            >
              <Icon name="refresh" size={14} />
              <span>Kiểm tra lại</span>
            </button>
          </div>

          <div className="health-grid">
            <div className="health-card">
              <span className="health-title">Backend API Core</span>
              <div className="health-status">
                <span
                  className={`status-dot ${
                    health?.status === 'ok' || health?.status === 'healthy' ? 'online' : 'offline'
                  }`}
                />
                <span className="font-semibold">
                  {health?.status === 'ok' || health?.status === 'healthy'
                    ? 'Hoạt động tốt (FastAPI)'
                    : 'Không khả dụng'}
                </span>
              </div>
              <span className="health-sub">Cổng mặc định: 8000</span>
            </div>

            <div className="health-card">
              <span className="health-title">Cơ sở dữ liệu & pgvector</span>
              <div className="health-status">
                <span
                  className={`status-dot ${
                    health?.database === 'connected' ||
                    health?.database === 'ok' ||
                    health?.status === 'ok'
                      ? 'online'
                      : 'offline'
                  }`}
                />
                <span className="font-semibold">
                  {health?.database === 'connected' ||
                  health?.database === 'ok' ||
                  health?.status === 'ok'
                    ? 'Kết nối PostgreSQL + Vector DB'
                    : 'Mất kết nối CSDL'}
                </span>
              </div>
              <span className="health-sub">Vector Embeddings Ready</span>
            </div>

            <div className="health-card">
              <span className="health-title">AI Intent & Classifier</span>
              <div className="health-status">
                <span className="status-dot online" />
                <span className="font-semibold">Gemini / Fake Fallback</span>
              </div>
              <span className="health-sub">Tự động phân loại Ticket & RAG</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

