import React, { useState, useEffect, useCallback } from 'react'
import { usersApi } from '../../api/users'
import { departmentsApi } from '../../api/departments'
import { useAuth } from '../../context/AuthContext'
import { RoleBadge } from '../common/Badge'
import { Icon } from '../common/Icons'
import { Modal } from '../common/Modal'

export function UsersView() {
  const { user: currentUser, addToast } = useAuth()
  const isAdmin = currentUser?.role === 'ADMIN'
  const isHRManager =
    currentUser?.role === 'DEPT_MANAGER' &&
    (() => {
      const deptName = (currentUser?.department?.name || '').toLowerCase()
      const keywords = ['nhân sự', 'nhan su', 'tổ chức', 'to chuc', 'tccb', 'hr']
      return keywords.some((kw) => deptName.includes(kw))
    })()
  const canManageRoles = isAdmin || isHRManager

  const [users, setUsers] = useState([])
  const [departments, setDepartments] = useState([])
  const [loading, setLoading] = useState(false)
  const [filterRole, setFilterRole] = useState('')
  const [searchTerm, setSearchTerm] = useState('')

  // Create user state
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [formName, setFormName] = useState('')
  const [formEmail, setFormEmail] = useState('')
  const [formPassword, setFormPassword] = useState('')
  const [formRole, setFormRole] = useState('STUDENT')
  const [formDeptId, setFormDeptId] = useState('')

  // Reset password modal
  const [resetModalUser, setResetModalUser] = useState(null)
  const [newPassword, setNewPassword] = useState('')

  // Edit role modal (Admin & HR Manager)
  const [roleModalUser, setRoleModalUser] = useState(null)
  const [editRole, setEditRole] = useState('STUDENT')
  const [editDeptId, setEditDeptId] = useState('')
  const [isUpdatingRole, setIsUpdatingRole] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const params = {}
      if (filterRole) params.role = filterRole
      const [userData, deptData] = await Promise.all([
        usersApi.listUsers(params),
        departmentsApi.listDepartments(),
      ])
      setUsers(userData)
      setDepartments(deptData)
    } catch (err) {
      addToast(err.message || 'Không thể tải danh sách tài khoản', 'error')
    } finally {
      setLoading(false)
    }
  }, [filterRole, addToast])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleCreateUser = async (e) => {
    e.preventDefault()
    if (!formEmail || !formName || !formPassword) return

    // Technician and Dept Manager require department
    if (['TECHNICIAN', 'DEPT_MANAGER'].includes(formRole) && !formDeptId) {
      addToast('Vai trò Kỹ thuật viên & Trưởng phòng bắt buộc phải chọn Phòng ban', 'error')
      return
    }

    try {
      const payload = {
        full_name: formName.trim(),
        email: formEmail.trim(),
        password: formPassword,
        role: formRole,
        department_id: formDeptId || null,
      }
      await usersApi.createUser(payload)
      addToast('Đã tạo tài khoản người dùng thành công!', 'success')
      setIsCreateOpen(false)
      setFormName('')
      setFormEmail('')
      setFormPassword('')
      setFormRole('STUDENT')
      setFormDeptId('')
      loadData()
    } catch (err) {
      addToast(err.message || 'Lỗi khi tạo người dùng', 'error')
    }
  }

  const handleToggleStatus = async (user) => {
    if (user.id === currentUser.id) {
      addToast('Bạn không thể tự vô hiệu hóa tài khoản của chính mình', 'error')
      return
    }

    try {
      await usersApi.updateUser(user.id, { is_active: !user.is_active })
      addToast(
        user.is_active ? 'Đã khóa tài khoản người dùng' : 'Đã kích hoạt lại tài khoản',
        'info'
      )
      setUsers((prev) =>
        prev.map((u) => (u.id === user.id ? { ...u, is_active: !u.is_active } : u))
      )
    } catch (err) {
      addToast(err.message || 'Không thể cập nhật trạng thái', 'error')
    }
  }

  const handleResetPassword = async (e) => {
    e.preventDefault()
    if (!resetModalUser || !newPassword || newPassword.length < 8) {
      addToast('Mật khẩu mới phải có ít nhất 8 ký tự', 'error')
      return
    }

    try {
      await usersApi.resetPassword(resetModalUser.id, newPassword)
      addToast(`Đã đổi mật khẩu cho ${resetModalUser.full_name}`, 'success')
      setResetModalUser(null)
      setNewPassword('')
    } catch (err) {
      addToast(err.message || 'Lỗi đặt lại mật khẩu', 'error')
    }
  }

  const handleOpenEditRole = (user) => {
    setRoleModalUser(user)
    setEditRole(user.role)
    setEditDeptId(user.department_id || '')
  }

  const handleSaveRole = async (e) => {
    e.preventDefault()
    if (!roleModalUser) return

    if (['TECHNICIAN', 'DEPT_MANAGER'].includes(editRole) && !editDeptId) {
      addToast('Vai trò Kỹ thuật viên & Trưởng phòng bắt buộc phải chọn Phòng ban', 'error')
      return
    }

    setIsUpdatingRole(true)
    try {
      const payload = {
        role: editRole,
        department_id: editDeptId || null,
      }
      const updated = await usersApi.updateUser(roleModalUser.id, payload)
      addToast(`Đã cập nhật chức vụ cho ${roleModalUser.full_name} thành công!`, 'success')
      setUsers((prev) =>
        prev.map((u) => (u.id === roleModalUser.id ? { ...u, ...updated } : u))
      )
      setRoleModalUser(null)
    } catch (err) {
      addToast(err.message || 'Lỗi khi cập nhật chức vụ', 'error')
    } finally {
      setIsUpdatingRole(false)
    }
  }

  const handleDeleteUser = async (user) => {
    if (user.id === currentUser.id) {
      addToast('Không thể xóa tài khoản đang đăng nhập', 'error')
      return
    }
    if (!window.confirm(`Bạn có chắc chắn muốn xóa tài khoản ${user.full_name} (${user.email})?`)) {
      return
    }

    try {
      await usersApi.deleteUser(user.id)
      addToast('Đã xóa tài khoản', 'success')
      setUsers((prev) => prev.filter((u) => u.id !== user.id))
    } catch (err) {
      addToast(err.message || 'Lỗi khi xóa tài khoản', 'error')
    }
  }

  const filteredUsers = users.filter((u) => {
    if (!searchTerm.trim()) return true
    const term = searchTerm.toLowerCase()
    return (
      u.full_name.toLowerCase().includes(term) ||
      u.email.toLowerCase().includes(term) ||
      (u.department?.name && u.department.name.toLowerCase().includes(term))
    )
  })

  return (
    <div className="view-container">
      {/* Header */}
      <div className="view-header">
        <div>
          <h1 className="view-title">Quản lý Tài khoản & Phân quyền</h1>
          <p className="view-subtitle">
            Quản trị thành viên, phân bổ kỹ thuật viên vào phòng ban và cấp phát vai trò người dùng
          </p>
        </div>
        <div className="header-actions">
          <button className="btn btn-outline" onClick={loadData} disabled={loading}>
            <Icon name="refresh" size={16} />
            <span>Làm mới</span>
          </button>
          {isAdmin && (
            <button className="btn btn-primary" onClick={() => setIsCreateOpen(true)}>
              <Icon name="plus" size={16} />
              <span>Thêm người dùng</span>
            </button>
          )}
        </div>
      </div>

      {/* Filter and Search */}
      <div className="filter-card">
        <div className="search-box">
          <Icon name="search" size={18} className="search-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Tìm theo họ tên, email hoặc phòng ban..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="filter-group">
          <select
            className="filter-select"
            value={filterRole}
            onChange={(e) => setFilterRole(e.target.value)}
          >
            <option value="">Tất cả vai trò</option>
            <option value="STUDENT">Sinh viên (STUDENT)</option>
            <option value="STAFF">Cán bộ / GV (STAFF)</option>
            <option value="TECHNICIAN">Kỹ thuật viên (TECHNICIAN)</option>
            <option value="DEPT_MANAGER">Trưởng phòng (DEPT_MANAGER)</option>
            <option value="ADMIN">Quản trị viên (ADMIN)</option>
          </select>
        </div>
      </div>

      {/* Users Table */}
      <div className="table-card">
        {loading ? (
          <div className="loading-state">
            <span className="spinner"></span>
            <p>Đang tải danh sách tài khoản...</p>
          </div>
        ) : filteredUsers.length === 0 ? (
          <div className="empty-state">
            <Icon name="users" size={48} className="empty-icon" />
            <h3>Không tìm thấy người dùng nào</h3>
            <p>Hãy điều chỉnh bộ lọc hoặc tạo tài khoản mới.</p>
          </div>
        ) : (
          <div className="responsive-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Họ và tên</th>
                  <th>Email</th>
                  <th>Vai trò</th>
                  <th>Phòng ban</th>
                  <th>Trạng thái</th>
                  <th>Ngày tạo</th>
                  <th>Hành động</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((u) => (
                  <tr key={u.id}>
                    <td>
                      <span className="font-semibold">{u.full_name}</span>
                    </td>
                    <td className="text-muted font-mono text-xs">{u.email}</td>
                    <td>
                      <RoleBadge role={u.role} />
                    </td>
                    <td>
                      {u.department ? (
                        <span className="dept-badge-text">🏢 {u.department.name}</span>
                      ) : (
                        <span className="text-muted text-xs">—</span>
                      )}
                    </td>
                    <td>
                      <button
                        className={`badge-status-btn ${u.is_active ? 'active' : 'inactive'}`}
                        onClick={() => handleToggleStatus(u)}
                        title={isAdmin ? 'Bật/tắt trạng thái hoạt động' : 'Chỉ Admin mới có quyền bật/tắt tài khoản'}
                        disabled={!isAdmin}
                      >
                        {u.is_active ? '🟢 Hoạt động' : '🔴 Bị khóa'}
                      </button>
                    </td>
                    <td className="text-muted text-xs whitespace-nowrap">
                      {new Date(u.created_at).toLocaleDateString('vi-VN')}
                    </td>
                    <td>
                      <div className="table-actions-row">
                        {canManageRoles && (
                          <button
                            className="btn-icon text-primary"
                            title={
                              u.role === 'ADMIN' && !isAdmin
                                ? 'Chỉ Admin mới có quyền sửa tài khoản Quản trị viên'
                                : 'Điều chỉnh chức vụ / vai trò'
                            }
                            onClick={() => handleOpenEditRole(u)}
                            disabled={u.role === 'ADMIN' && !isAdmin}
                          >
                            <Icon name="shield" size={15} />
                          </button>
                        )}
                        {isAdmin && (
                          <>
                            <button
                              className="btn-icon"
                              title="Đặt lại mật khẩu"
                              onClick={() => setResetModalUser(u)}
                            >
                              <Icon name="key" size={15} />
                            </button>
                            <button
                              className="btn-icon text-red"
                              title="Xóa tài khoản"
                              onClick={() => handleDeleteUser(u)}
                            >
                              <Icon name="trash" size={15} />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal Edit User Role (Admin & HR Manager) */}
      <Modal
        isOpen={Boolean(roleModalUser)}
        onClose={() => setRoleModalUser(null)}
        title={`Điều chỉnh chức vụ cho ${roleModalUser?.full_name}`}
      >
        <form onSubmit={handleSaveRole} className="generic-form">
          <div
            style={{
              padding: '12px 16px',
              background: 'var(--bg-subtle)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-color)',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong style={{ fontSize: '0.92rem' }}>{roleModalUser?.full_name}</strong>
              <span className="text-muted text-xs font-mono">{roleModalUser?.email}</span>
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', fontSize: '0.82rem' }}>
              <span className="text-muted">Chức vụ hiện tại:</span>
              <RoleBadge role={roleModalUser?.role} />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">
              Chức vụ / Vai trò mới <span className="text-red">*</span>
            </label>
            <select
              className="form-select"
              value={editRole}
              onChange={(e) => setEditRole(e.target.value)}
              required
            >
              <option value="STUDENT">Sinh viên (STUDENT)</option>
              <option value="STAFF">Cán bộ / Giảng viên (STAFF)</option>
              <option value="TECHNICIAN">Kỹ thuật viên (TECHNICIAN)</option>
              <option value="DEPT_MANAGER">Trưởng phòng (DEPT_MANAGER)</option>
              {isAdmin && <option value="ADMIN">Quản trị viên (ADMIN)</option>}
            </select>
            {!isAdmin && isHRManager && (
              <span className="form-hint">
                Trưởng bộ phận nhân sự có thể điều chỉnh giữa Sinh viên, Cán bộ, Kỹ thuật viên và Trưởng phòng.
              </span>
            )}
          </div>

          <div className="form-group">
            <label className="form-label">
              Phòng ban trực thuộc{' '}
              {['TECHNICIAN', 'DEPT_MANAGER'].includes(editRole) && (
                <span className="text-red">*</span>
              )}
            </label>
            <select
              className="form-select"
              value={editDeptId}
              onChange={(e) => setEditDeptId(e.target.value)}
              required={['TECHNICIAN', 'DEPT_MANAGER'].includes(editRole)}
            >
              <option value="">-- Chọn phòng ban --</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
            {['TECHNICIAN', 'DEPT_MANAGER'].includes(editRole) && (
              <span className="form-hint">
                Kỹ thuật viên và Trưởng phòng bắt buộc phải trực thuộc một phòng ban cụ thể.
              </span>
            )}
          </div>

          <div className="modal-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setRoleModalUser(null)}
              disabled={isUpdatingRole}
            >
              Hủy bỏ
            </button>
            <button type="submit" className="btn btn-primary" disabled={isUpdatingRole}>
              {isUpdatingRole ? <span className="spinner"></span> : <Icon name="check" size={16} />}
              <span>Lưu thay đổi</span>
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal Create User */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Thêm mới Người dùng vào hệ thống"
      >
        <form onSubmit={handleCreateUser} className="generic-form">
          <div className="form-group">
            <label className="form-label">Họ và tên <span className="text-red">*</span></label>
            <input
              type="text"
              className="form-input"
              placeholder="Trần Văn B"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Email tài khoản <span className="text-red">*</span></label>
            <input
              type="email"
              className="form-input"
              placeholder="user@helpdesk.edu.vn"
              value={formEmail}
              onChange={(e) => setFormEmail(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Mật khẩu khởi tạo <span className="text-red">*</span></label>
            <input
              type="password"
              className="form-input"
              placeholder="Tối thiểu 8 ký tự"
              value={formPassword}
              onChange={(e) => setFormPassword(e.target.value)}
              required
            />
          </div>
          <div className="form-row">
            <div className="form-group col">
              <label className="form-label">Vai trò (Role) <span className="text-red">*</span></label>
              <select
                className="form-select"
                value={formRole}
                onChange={(e) => setFormRole(e.target.value)}
              >
                <option value="STUDENT">Sinh viên (STUDENT)</option>
                <option value="STAFF">Cán bộ / Giảng viên (STAFF)</option>
                <option value="TECHNICIAN">Kỹ thuật viên (TECHNICIAN)</option>
                <option value="DEPT_MANAGER">Trưởng phòng (DEPT_MANAGER)</option>
                <option value="ADMIN">Quản trị viên (ADMIN)</option>
              </select>
            </div>
            <div className="form-group col">
              <label className="form-label">
                Phòng ban {['TECHNICIAN', 'DEPT_MANAGER'].includes(formRole) && <span className="text-red">*</span>}
              </label>
              <select
                className="form-select"
                value={formDeptId}
                onChange={(e) => setFormDeptId(e.target.value)}
                required={['TECHNICIAN', 'DEPT_MANAGER'].includes(formRole)}
              >
                <option value="">-- Chọn phòng ban --</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={() => setIsCreateOpen(false)}>
              Hủy
            </button>
            <button type="submit" className="btn btn-primary">
              Tạo tài khoản
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal Reset Password */}
      <Modal
        isOpen={Boolean(resetModalUser)}
        onClose={() => setResetModalUser(null)}
        title={`Đặt lại mật khẩu cho ${resetModalUser?.full_name}`}
      >
        <form onSubmit={handleResetPassword} className="generic-form">
          <div className="form-group">
            <label className="form-label">Mật khẩu mới <span className="text-red">*</span></label>
            <input
              type="password"
              className="form-input"
              placeholder="Nhập mật khẩu mới (tối thiểu 8 ký tự)"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={() => setResetModalUser(null)}>
              Hủy
            </button>
            <button type="submit" className="btn btn-primary">
              Cập nhật mật khẩu
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}

