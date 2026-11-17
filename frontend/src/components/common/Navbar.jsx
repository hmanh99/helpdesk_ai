import React from 'react'
import { useAuth } from '../../context/AuthContext'
import { RoleBadge } from './Badge'
import { Icon } from './Icons'

export function Navbar({ activeTab, onSelectTab }) {
  const { user, logout } = useAuth()

  // Generate initials for avatar
  const getInitials = (name) => {
    if (!name) return 'U'
    const parts = name.trim().split(/\s+/)
    if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase()
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
  }

  return (
    <header className="navbar">
      <div className="navbar-left">
        <div className="navbar-brand" onClick={() => onSelectTab && onSelectTab('chat')} style={{ cursor: 'pointer' }}>
          <div className="brand-logo">
            <Icon name="bot" size={22} />
          </div>
          <div className="brand-text">
            <div className="brand-name-row">
              <span className="brand-name">NEU Helpdesk AI</span>
              <span className="brand-version-badge">v2.5</span>
            </div>
            <span className="brand-tag">Hệ thống hỗ trợ thông minh • ĐH Kinh tế Quốc dân</span>
          </div>
        </div>

        <div className="navbar-system-status">
          <span className="status-dot online pulse"></span>
          <span className="status-text">AI RAG Sẵn sàng</span>
        </div>
      </div>

      <div className="navbar-right">
        {user && (
          <div className="user-profile">
            <button
              type="button"
              className="user-profile-btn"
              onClick={() => onSelectTab && onSelectTab('profile')}
              title="Xem thông tin tài khoản"
            >
              <div className="user-avatar-circle">
                {getInitials(user.full_name)}
              </div>
              <div className="user-info">
                <span className="user-name">{user.full_name}</span>
                <div className="user-role-dept">
                  <RoleBadge role={user.role} />
                  {user.department && (
                    <span className="user-dept" title={user.department.name}>
                      🏢 {user.department.name}
                    </span>
                  )}
                </div>
              </div>
            </button>

            <button
              type="button"
              className="btn btn-outline btn-sm logout-btn"
              onClick={logout}
              title="Đăng xuất khỏi hệ thống"
            >
              <Icon name="logout" size={15} />
              <span>Đăng xuất</span>
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
