import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { ticketsApi } from '../../api/tickets'
import { departmentsApi } from '../../api/departments'
import { useAuth } from '../../context/AuthContext'
import { StatusBadge, PriorityBadge } from '../common/Badge'
import { Icon } from '../common/Icons'
import { CreateTicketModal } from './CreateTicketModal'
import { EditTicketModal } from './EditTicketModal'
import { TicketDetailModal } from './TicketDetailModal'

export function TicketsView({ initialTicketId }) {
  const { user, addToast } = useAuth()
  const [tickets, setTickets] = useState([])
  const [departments, setDepartments] = useState([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('all') // 'all', 'unassigned', 'my_tickets', 'in_progress', 'resolved'
  const [filterStatus, setFilterStatus] = useState('')
  const [filterDept, setFilterDept] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [acceptingId, setAcceptingId] = useState(null)

  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [selectedTicket, setSelectedTicket] = useState(null)
  const [isDetailOpen, setIsDetailOpen] = useState(false)

  // Edit ticket state
  const [editingTicket, setEditingTicket] = useState(null)
  const [isEditOpen, setIsEditOpen] = useState(false)

  const isStaffOrTech =
    user && ['ADMIN', 'DEPT_MANAGER', 'TECHNICIAN', 'STAFF'].includes(user.role)

  const canAcceptTickets =
    user && ['ADMIN', 'DEPT_MANAGER', 'TECHNICIAN'].includes(user.role)

  const loadDepartments = async () => {
    try {
      const data = await departmentsApi.listDepartments()
      setDepartments(data || [])
    } catch {
      // Ignored
    }
  }

  const loadTickets = useCallback(async () => {
    setLoading(true)
    try {
      const params = {}
      if (filterStatus) params.status = filterStatus
      if (filterDept) params.department_id = filterDept

      // Apply active queue tab filters
      if (activeTab === 'unassigned') {
        params.unassigned_only = true
      } else if (activeTab === 'my_tickets') {
        params.assigned_to_me = true
      } else if (activeTab === 'in_progress') {
        params.status = 'IN_PROGRESS'
      } else if (activeTab === 'resolved') {
        params.status = 'RESOLVED'
      }

      const data = await ticketsApi.listTickets(params)
      setTickets(data || [])

      // If initialTicketId was specified, open it
      if (initialTicketId) {
        const found = (data || []).find((t) => t.id === initialTicketId)
        if (found) {
          setSelectedTicket(found)
          setIsDetailOpen(true)
        }
      }
    } catch (err) {
      addToast(err.message || 'Không thể tải danh sách phiếu hỗ trợ', 'error')
    } finally {
      setLoading(false)
    }
  }, [filterStatus, filterDept, activeTab, initialTicketId, addToast])

  useEffect(() => {
    loadDepartments()
  }, [])

  useEffect(() => {
    loadTickets()
  }, [loadTickets])

  const handleOpenDetail = (ticket) => {
    setSelectedTicket(ticket)
    setIsDetailOpen(true)
  }

  const handleTicketCreated = (newTicket) => {
    setTickets((prev) => [newTicket, ...prev])
    setSelectedTicket(newTicket)
    setIsDetailOpen(true)
  }

  const handleTicketUpdated = (updated) => {
    setTickets((prev) =>
      prev.map((t) => (t.id === updated.id ? { ...t, ...updated } : t))
    )
    if (selectedTicket?.id === updated.id) {
      setSelectedTicket((prev) => ({ ...prev, ...updated }))
    }
  }

  const handleTicketDeleted = (deletedId) => {
    setTickets((prev) => prev.filter((t) => t.id !== deletedId))
    if (selectedTicket?.id === deletedId) {
      setSelectedTicket(null)
      setIsDetailOpen(false)
    }
  }

  // 1-Click Accept from Table Row
  const handleQuickAccept = async (ticket) => {
    setAcceptingId(ticket.id)
    try {
      const updated = await ticketsApi.acceptTicket(ticket.id)
      handleTicketUpdated(updated)
      addToast(
        `Đã tiếp nhận xử lý phiếu #${ticket.id.substring(0, 8)}!`,
        'success'
      )
    } catch (err) {
      addToast(err.message || 'Không thể tiếp nhận phiếu', 'error')
    } finally {
      setAcceptingId(null)
    }
  }

  // Quick Cancel from Table Row
  const handleQuickCancel = async (ticket) => {
    const reason = window.prompt(`Hủy phiếu #${ticket.id.substring(0, 8)}? Nhập lý do (tùy chọn):`, '')
    if (reason === null) return

    try {
      const updated = await ticketsApi.updateTicketStatus(
        ticket.id,
        'CANCELLED',
        reason.trim() || 'Người dùng đã hủy phiếu hỗ trợ'
      )
      handleTicketUpdated(updated)
      addToast('Đã hủy phiếu hỗ trợ thành công!', 'success')
    } catch (err) {
      addToast(err.message || 'Lỗi khi hủy phiếu', 'error')
    }
  }

  // Quick Delete from Table Row
  const handleQuickDelete = async (ticket) => {
    if (
      !window.confirm(
        `Bạn có chắc chắn muốn xóa vĩnh viễn phiếu #${ticket.id.substring(0, 8)} không?`
      )
    ) {
      return
    }

    try {
      await ticketsApi.deleteTicket(ticket.id)
      handleTicketDeleted(ticket.id)
      addToast('Đã xóa phiếu hỗ trợ thành công!', 'success')
    } catch (err) {
      addToast(err.message || 'Lỗi khi xóa phiếu', 'error')
    }
  }

  // Filtered tickets by search box
  const filteredTickets = useMemo(() => {
    return tickets.filter((t) => {
      if (!searchTerm.trim()) return true
      const term = searchTerm.toLowerCase()
      return (
        t.title.toLowerCase().includes(term) ||
        t.description.toLowerCase().includes(term) ||
        (t.department_name && t.department_name.toLowerCase().includes(term)) ||
        (t.category_name && t.category_name.toLowerCase().includes(term)) ||
        (t.assignee_name && t.assignee_name.toLowerCase().includes(term)) ||
        t.id.toLowerCase().includes(term)
      )
    })
  }, [tickets, searchTerm])

  // Count unassigned tickets in the currently loaded tickets or for badge
  const unassignedCount = useMemo(() => {
    return tickets.filter(
      (t) => !t.assignee_id && ['NEW', 'TRIAGED'].includes(t.status)
    ).length
  }, [tickets])

  const myTicketsCount = useMemo(() => {
    return tickets.filter((t) => user && t.assignee_id === user.id).length
  }, [tickets, user])

  const stats = useMemo(() => {
    return {
      total: tickets.length,
      unassigned: tickets.filter((t) => !t.assignee_id && ['NEW', 'TRIAGED'].includes(t.status)).length,
      inProgress: tickets.filter((t) => ['IN_PROGRESS', 'ASSIGNED', 'PENDING_USER'].includes(t.status)).length,
      resolved: tickets.filter((t) => t.status === 'RESOLVED').length,
      cancelled: tickets.filter((t) => t.status === 'CANCELLED').length,
    }
  }, [tickets])

  return (
    <div className="view-container">
      {/* Top Header */}
      <div className="view-header">
        <div>
          <h1 className="view-title">
            {isStaffOrTech ? 'Quản lý & Tiếp nhận Phiếu hỗ trợ' : 'Phiếu hỗ trợ của tôi (Tickets)'}
          </h1>
          <p className="view-subtitle">
            Hệ thống tiếp nhận yêu cầu từ sinh viên, AI tự động phân loại nghiệp vụ và điều phối xử lý
          </p>
        </div>
        <div className="header-actions">
          <button
            className="btn btn-outline"
            onClick={loadTickets}
            disabled={loading}
            title="Làm mới"
          >
            <Icon name="refresh" size={16} />
            <span>Làm mới</span>
          </button>
          <button className="btn btn-primary" onClick={() => setIsCreateOpen(true)}>
            <Icon name="plus" size={16} />
            <span>Tạo phiếu mới</span>
          </button>
        </div>
      </div>

      {/* KPI Stats Overview Cards */}
      <div className="kpi-stats-grid">
        <div className="kpi-card" onClick={() => setActiveTab('all')}>
          <div className="kpi-card-header">
            <span className="kpi-card-title">Tổng số phiếu</span>
            <div className="kpi-icon-wrap blue">
              <Icon name="ticket" size={18} />
            </div>
          </div>
          <div className="kpi-card-val">{stats.total}</div>
          <div className="kpi-card-hint">Tất cả yêu cầu trên hệ thống</div>
        </div>

        <div className="kpi-card" onClick={() => setActiveTab('unassigned')}>
          <div className="kpi-card-header">
            <span className="kpi-card-title">Chờ tiếp nhận</span>
            <div className="kpi-icon-wrap amber">
              <Icon name="alertCircle" size={18} />
            </div>
          </div>
          <div className="kpi-card-val text-amber">{stats.unassigned}</div>
          <div className="kpi-card-hint">Phiếu mới & chờ phân công</div>
        </div>

        <div className="kpi-card" onClick={() => setActiveTab('in_progress')}>
          <div className="kpi-card-header">
            <span className="kpi-card-title">Đang xử lý</span>
            <div className="kpi-icon-wrap indigo">
              <Icon name="clock" size={18} />
            </div>
          </div>
          <div className="kpi-card-val text-indigo">{stats.inProgress}</div>
          <div className="kpi-card-hint">Kỹ thuật viên đang giải quyết</div>
        </div>

        <div className="kpi-card" onClick={() => setActiveTab('resolved')}>
          <div className="kpi-card-header">
            <span className="kpi-card-title">Đã giải quyết</span>
            <div className="kpi-icon-wrap emerald">
              <Icon name="check" size={18} />
            </div>
          </div>
          <div className="kpi-card-val text-emerald">{stats.resolved}</div>
          <div className="kpi-card-hint">Hoàn tất xử lý thành công</div>
        </div>

        <div className="kpi-card" onClick={() => setFilterStatus('CANCELLED')}>
          <div className="kpi-card-header">
            <span className="kpi-card-title">Đã hủy</span>
            <div className="kpi-icon-wrap red">
              <Icon name="x" size={18} />
            </div>
          </div>
          <div className="kpi-card-val text-red">{stats.cancelled}</div>
          <div className="kpi-card-hint">Yêu cầu đã được hủy</div>
        </div>
      </div>

      {/* Staff Queue Alert Banner */}
      {isStaffOrTech && unassignedCount > 0 && activeTab !== 'unassigned' && (
        <div className="queue-alert-banner">
          <div className="queue-alert-info">
            <span className="queue-alert-icon">⚡</span>
            <span>
              Có <strong>{unassignedCount} phiếu hỗ trợ</strong> đang chờ phòng ban tiếp nhận xử lý.
            </span>
          </div>
          <button
            className="btn btn-sm btn-primary"
            onClick={() => setActiveTab('unassigned')}
          >
            Xem hàng đợi tiếp nhận
          </button>
        </div>
      )}

      {/* Role-based Queue Tabs */}
      <div className="queue-tabs-card">
        <div className="tab-buttons">
          <button
            className={`tab-btn ${activeTab === 'all' ? 'active' : ''}`}
            onClick={() => setActiveTab('all')}
          >
            <Icon name="ticket" size={16} />
            <span>Tất cả phiếu</span>
          </button>

          {isStaffOrTech && (
            <>
              <button
                className={`tab-btn ${activeTab === 'unassigned' ? 'active' : ''}`}
                onClick={() => setActiveTab('unassigned')}
              >
                <Icon name="alertCircle" size={16} />
                <span>Chờ tiếp nhận</span>
                {unassignedCount > 0 && (
                  <span className="tab-badge-pill">{unassignedCount}</span>
                )}
              </button>

              <button
                className={`tab-btn ${activeTab === 'my_tickets' ? 'active' : ''}`}
                onClick={() => setActiveTab('my_tickets')}
              >
                <Icon name="user" size={16} />
                <span>Việc của tôi</span>
                {myTicketsCount > 0 && (
                  <span className="tab-badge-pill tab-badge-neutral">{myTicketsCount}</span>
                )}
              </button>
            </>
          )}

          <button
            className={`tab-btn ${activeTab === 'in_progress' ? 'active' : ''}`}
            onClick={() => setActiveTab('in_progress')}
          >
            <Icon name="clock" size={16} />
            <span>Đang xử lý</span>
          </button>

          <button
            className={`tab-btn ${activeTab === 'resolved' ? 'active' : ''}`}
            onClick={() => setActiveTab('resolved')}
          >
            <Icon name="check" size={16} />
            <span>Đã giải quyết</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="filter-card">
        <div className="search-box">
          <Icon name="search" size={18} className="search-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Tìm theo tiêu đề, mô tả, phòng ban hoặc kỹ thuật viên phụ trách..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="filter-group">
          {activeTab === 'all' && (
            <select
              className="filter-select"
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
            >
              <option value="">Tất cả trạng thái</option>
              <option value="NEW">Mới tạo (NEW)</option>
              <option value="TRIAGED">Đã phân loại AI (TRIAGED)</option>
              <option value="ASSIGNED">Đã phân công (ASSIGNED)</option>
              <option value="IN_PROGRESS">Đang xử lý (IN_PROGRESS)</option>
              <option value="PENDING_USER">Chờ phản hồi (PENDING_USER)</option>
              <option value="RESOLVED">Đã giải quyết (RESOLVED)</option>
              <option value="CANCELLED">Đã hủy (CANCELLED)</option>
            </select>
          )}

          <select
            className="filter-select"
            value={filterDept}
            onChange={(e) => setFilterDept(e.target.value)}
          >
            <option value="">Tất cả phòng ban</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Tickets Table */}
      <div className="table-card">
        {loading ? (
          <div className="loading-state">
            <span className="spinner"></span>
            <p>Đang tải danh sách yêu cầu...</p>
          </div>
        ) : filteredTickets.length === 0 ? (
          <div className="empty-state">
            <Icon name="ticket" size={48} className="empty-icon" />
            <h3>Chưa có phiếu hỗ trợ nào phù hợp</h3>
            <p>
              {activeTab === 'unassigned'
                ? 'Tuyệt vời! Hiện không còn phiếu nào đang chờ tiếp nhận.'
                : activeTab === 'my_tickets'
                ? 'Bạn chưa được phân công hoặc chưa tiếp nhận phiếu hỗ trợ nào.'
                : 'Hãy tạo phiếu hỗ trợ mới hoặc thay đổi bộ lọc tìm kiếm.'}
            </p>
            {user?.role === 'STUDENT' && (
              <button className="btn btn-primary btn-sm" onClick={() => setIsCreateOpen(true)}>
                <Icon name="plus" size={16} />
                <span>Tạo phiếu hỗ trợ</span>
              </button>
            )}
          </div>
        ) : (
          <div className="responsive-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Mã Ticket</th>
                  <th>Tiêu đề & Nội dung</th>
                  <th>Phòng ban</th>
                  <th>Phụ trách</th>
                  <th>Ưu tiên</th>
                  <th>Trạng thái</th>
                  <th>Ngày gửi</th>
                  <th style={{ textAlign: 'right' }}>Hành động</th>
                </tr>
              </thead>
              <tbody>
                {filteredTickets.map((t) => {
                  const isRequester =
                    user && user.id && String(user.id) === String(t.requester_id)
                  const canManageThisTicket =
                    user && (user.role === 'ADMIN' || isRequester)

                  const canClaim =
                    canAcceptTickets &&
                    !t.assignee_id &&
                    (user.role === 'ADMIN' ||
                      !t.department_id ||
                      user.department_id === t.department_id)

                  const canCancel =
                    (user?.role === 'ADMIN' ||
                      isRequester ||
                      ['DEPT_MANAGER', 'TECHNICIAN'].includes(user?.role)) &&
                    t.status !== 'CANCELLED' &&
                    t.status !== 'RESOLVED'

                  return (
                    <tr
                      key={t.id}
                      className="table-row-clickable"
                      onClick={() => handleOpenDetail(t)}
                    >
                      <td className="font-mono text-xs font-semibold text-primary">
                        #{t.id.substring(0, 8)}
                      </td>
                      <td>
                        <div className="ticket-title-col">
                          <span className="ticket-title-text">{t.title}</span>
                          <span className="ticket-desc-snippet">{t.description}</span>
                        </div>
                      </td>
                      <td>
                        <div className="ticket-dept-col">
                          <span className="dept-badge-text">
                            🏢 {t.department_name || 'Đang phân loại'}
                          </span>
                          {t.category_name && (
                            <span className="cat-badge-text">{t.category_name}</span>
                          )}
                        </div>
                      </td>
                      <td>
                        {t.assignee_name ? (
                          <span className="assignee-cell font-medium">
                            👤 {t.assignee_name}
                          </span>
                        ) : (
                          <span className="badge badge-amber text-xs">
                            Chưa tiếp nhận
                          </span>
                        )}
                      </td>
                      <td>
                        <PriorityBadge priority={t.priority} />
                      </td>
                      <td>
                        <StatusBadge status={t.status} />
                      </td>
                      <td className="text-muted text-xs whitespace-nowrap">
                        {new Date(t.created_at).toLocaleDateString('vi-VN', {
                          day: '2-digit',
                          month: '2-digit',
                          year: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>
                      <td>
                        <div
                          className="table-row-actions"
                          style={{
                            display: 'flex',
                            gap: '6px',
                            justifyContent: 'flex-end',
                            alignItems: 'center',
                          }}
                        >
                          {canClaim && (
                            <button
                              type="button"
                              className="btn btn-sm btn-primary-soft"
                              title="Tiếp nhận phiếu ngay"
                              disabled={acceptingId === t.id}
                              onClick={(e) => {
                                e.stopPropagation()
                                handleQuickAccept(t)
                              }}
                            >
                              <Icon name="check" size={14} />
                              <span>{acceptingId === t.id ? '...' : 'Tiếp nhận'}</span>
                            </button>
                          )}
                          {canManageThisTicket && (
                            <>
                              <button
                                type="button"
                                className="btn btn-sm btn-outline"
                                title="Chỉnh sửa phiếu"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setEditingTicket(t)
                                  setIsEditOpen(true)
                                }}
                              >
                                <Icon name="edit" size={13} />
                                <span>Sửa</span>
                              </button>
                              <button
                                type="button"
                                className="btn btn-sm btn-outline"
                                style={{ color: '#dc2626', borderColor: '#fca5a5' }}
                                title="Xóa phiếu"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleQuickDelete(t)
                                }}
                              >
                                <Icon name="trash" size={13} />
                                <span>Xóa</span>
                              </button>
                            </>
                          )}
                          {canCancel && (
                            <button
                              type="button"
                              className="btn btn-sm btn-outline"
                              style={{ color: '#dc2626', borderColor: '#fca5a5' }}
                              title="Hủy phiếu này"
                              onClick={(e) => {
                                e.stopPropagation()
                                handleQuickCancel(t)
                              }}
                            >
                              <Icon name="x" size={13} />
                              <span>Hủy</span>
                            </button>
                          )}
                          <button
                            type="button"
                            className="btn btn-sm btn-outline"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleOpenDetail(t)
                            }}
                          >
                            Chi tiết
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create Ticket Modal */}
      <CreateTicketModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onCreated={handleTicketCreated}
      />

      {/* Edit Ticket Modal */}
      <EditTicketModal
        ticket={editingTicket}
        isOpen={isEditOpen}
        onClose={() => {
          setIsEditOpen(false)
          setEditingTicket(null)
        }}
        onUpdated={handleTicketUpdated}
      />

      {/* Ticket Detail Modal */}
      <TicketDetailModal
        ticket={selectedTicket}
        isOpen={isDetailOpen}
        onClose={() => {
          setIsDetailOpen(false)
          setSelectedTicket(null)
        }}
        onTicketUpdated={handleTicketUpdated}
        onTicketDeleted={handleTicketDeleted}
      />
    </div>
  )
}
