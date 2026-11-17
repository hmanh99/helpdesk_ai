import React from 'react'
import { useAuth } from '../../context/AuthContext'
import { Icon } from './Icons'

export function Sidebar({ activeTab, onSelectTab }) {
  const { user } = useAuth()
  const isAdmin = user?.role === 'ADMIN'
  const isManagerOrAdmin = user?.role === 'ADMIN' || user?.role === 'DEPT_MANAGER'
  const isHRManager =
    user?.role === 'DEPT_MANAGER' &&
    (() => {
      const deptName = (user?.department?.name || '').toLowerCase()
      const keywords = ['nhân sự', 'nhan su', 'tổ chức', 'to chuc', 'tccb', 'hr']
      return keywords.some((kw) => deptName.includes(kw))
    })()

  const mainNavItems = [
    {
      id: 'chat',
      label: 'Trợ lý AI (RAG)',
      icon: 'bot',
      desc: 'Hỏi đáp & hỗ trợ tự động',
      badge: 'AI',
    },
    {
      id: 'tickets',
      label: 'Phiếu hỗ trợ (Tickets)',
      icon: 'ticket',
      desc: 'Quản lý yêu cầu & xử lý sự cố',
    },
  ]

  const manageNavItems = [
    ...(isManagerOrAdmin
      ? [
          {
            id: 'knowledge',
            label: 'Cơ sở tri thức (RAG)',
            icon: 'book',
            desc: 'Quản lý tài liệu & vector DB',
          },
        ]
      : []),
    {
      id: 'departments',
      label: 'Phòng ban & Danh mục',
      icon: 'building',
      desc: 'Cơ cấu phòng ban & dịch vụ',
    },
    ...((isAdmin || isHRManager)
      ? [
          {
            id: 'users',
            label: 'Quản lý người dùng',
            icon: 'users',
            desc: isHRManager ? 'Quản lý & điều chỉnh chức vụ' : 'Phân quyền tài khoản hệ thống',
          },
        ]
      : []),
  ]

  const personalNavItems = [
    {
      id: 'profile',
      label: 'Tài khoản & Hệ thống',
      icon: 'shield',
      desc: 'Đổi mật khẩu & trạng thái API',
    },
  ]

  const renderNavGroup = (title, items) => {
    if (!items || items.length === 0) return null
    return (
      <div className="sidebar-group">
        <div className="sidebar-group-title">{title}</div>
        <div className="sidebar-group-items">
          {items.map((item) => {
            const isActive = activeTab === item.id
            return (
              <button
                key={item.id}
                type="button"
                className={`sidebar-item ${isActive ? 'active' : ''}`}
                onClick={() => onSelectTab(item.id)}
              >
                <div className="sidebar-item-icon">
                  <Icon name={item.icon} size={18} />
                </div>
                <div className="sidebar-item-content">
                  <span className="sidebar-item-label">{item.label}</span>
                  <span className="sidebar-item-desc">{item.desc}</span>
                </div>
                {item.badge && <span className="sidebar-item-badge">{item.badge}</span>}
                {isActive && <div className="sidebar-item-indicator" />}
              </button>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <aside className="sidebar">
      <nav className="sidebar-nav">
        {renderNavGroup('TRỢ LÝ & PHIẾU YÊU CẦU', mainNavItems)}
        {renderNavGroup('QUẢN LÝ DỊCH VỤ', manageNavItems)}
        {renderNavGroup('CÁ NHÂN & CÀI ĐẶT', personalNavItems)}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-footer-card">
          <div className="system-pill">
            <span className="status-dot online"></span>
            <span>NEU Helpdesk • Gemini & RAG</span>
          </div>
          <div className="portal-hint">Cổng thông tin hỗ trợ sinh viên</div>
        </div>
      </div>
    </aside>
  )
}
