import React, { useState, useEffect } from 'react'
import { departmentsApi } from '../../api/departments'
import { categoriesApi } from '../../api/categories'
import { useAuth } from '../../context/AuthContext'
import { Icon } from '../common/Icons'
import { Modal } from '../common/Modal'

export function DepartmentsView() {
  const { user, addToast } = useAuth()
  const isAdmin = user?.role === 'ADMIN'
  const isDeptManager = user?.role === 'DEPT_MANAGER'

  // Helper checking if user can manage categories of a given department
  const canManageDeptCategories = (deptId) => {
    if (isAdmin) return true
    if (isDeptManager && user?.department_id && String(user.department_id) === String(deptId)) {
      return true
    }
    return false
  }

  const [departments, setDepartments] = useState([])
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(false)

  // Create dept modal (Admin only)
  const [isDeptModalOpen, setIsDeptModalOpen] = useState(false)
  const [deptName, setDeptName] = useState('')
  const [deptDesc, setDeptDesc] = useState('')

  // Create category modal (Admin & Dept Manager)
  const [isCatModalOpen, setIsCatModalOpen] = useState(false)
  const [catName, setCatName] = useState('')
  const [catDeptId, setCatDeptId] = useState('')
  const [catDesc, setCatDesc] = useState('')
  const [slaResponse, setSlaResponse] = useState(60)
  const [slaResolve, setSlaResolve] = useState(1440)

  // Edit category modal (Admin & Dept Manager)
  const [isEditCatModalOpen, setIsEditCatModalOpen] = useState(false)
  const [editingCat, setEditingCat] = useState(null)
  const [editCatName, setEditCatName] = useState('')
  const [editCatDeptId, setEditCatDeptId] = useState('')
  const [editCatDesc, setEditCatDesc] = useState('')
  const [editSlaResponse, setEditSlaResponse] = useState(60)
  const [editSlaResolve, setEditSlaResolve] = useState(1440)
  const [editIsActive, setEditIsActive] = useState(true)

  const loadData = async () => {
    setLoading(true)
    try {
      const [depts, cats] = await Promise.all([
        departmentsApi.listDepartments(),
        categoriesApi.listCategories(),
      ])
      setDepartments(depts)
      setCategories(cats)
      if (depts.length > 0 && !catDeptId) {
        if (isDeptManager && user?.department_id) {
          setCatDeptId(user.department_id)
        } else {
          setCatDeptId(depts[0].id)
        }
      }
    } catch (err) {
      addToast(err.message || 'Lỗi khi tải dữ liệu phòng ban', 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleCreateDept = async (e) => {
    e.preventDefault()
    if (!deptName.trim()) return

    try {
      await departmentsApi.createDepartment({
        name: deptName.trim(),
        description: deptDesc.trim() || undefined,
      })
      addToast('Đã thêm phòng ban mới thành công!', 'success')
      setIsDeptModalOpen(false)
      setDeptName('')
      setDeptDesc('')
      loadData()
    } catch (err) {
      addToast(err.message || 'Lỗi tạo phòng ban', 'error')
    }
  }

  const handleOpenCreateCategory = (targetDeptId = null) => {
    if (targetDeptId) {
      setCatDeptId(targetDeptId)
    } else if (isDeptManager && user?.department_id) {
      setCatDeptId(user.department_id)
    } else if (departments.length > 0 && !catDeptId) {
      setCatDeptId(departments[0].id)
    }
    setCatName('')
    setCatDesc('')
    setSlaResponse(60)
    setSlaResolve(1440)
    setIsCatModalOpen(true)
  }

  const handleCreateCat = async (e) => {
    e.preventDefault()
    if (!catName.trim() || !catDeptId) {
      addToast('Vui lòng nhập tên danh mục và chọn phòng ban', 'error')
      return
    }

    try {
      await categoriesApi.createCategory({
        name: catName.trim(),
        department_id: catDeptId,
        description: catDesc.trim() || undefined,
        sla_response_minutes: Number(slaResponse),
        sla_resolve_minutes: Number(slaResolve),
        is_active: true,
      })
      addToast('Đã thêm danh mục dịch vụ mới!', 'success')
      setIsCatModalOpen(false)
      setCatName('')
      setCatDesc('')
      loadData()
    } catch (err) {
      addToast(err.message || 'Lỗi tạo danh mục', 'error')
    }
  }

  const handleOpenEditCategory = (cat) => {
    setEditingCat(cat)
    setEditCatName(cat.name || '')
    setEditCatDeptId(cat.department_id || '')
    setEditCatDesc(cat.description || '')
    setEditSlaResponse(cat.sla_response_minutes ?? 60)
    setEditSlaResolve(cat.sla_resolve_minutes ?? 1440)
    setEditIsActive(cat.is_active !== undefined ? cat.is_active : true)
    setIsEditCatModalOpen(true)
  }

  const handleUpdateCat = async (e) => {
    e.preventDefault()
    if (!editCatName.trim() || !editingCat) {
      addToast('Vui lòng nhập tên danh mục', 'error')
      return
    }

    try {
      const payload = {
        name: editCatName.trim(),
        description: editCatDesc.trim() || undefined,
        sla_response_minutes: Number(editSlaResponse),
        sla_resolve_minutes: Number(editSlaResolve),
        is_active: editIsActive,
      }
      if (isAdmin && editCatDeptId) {
        payload.department_id = editCatDeptId
      }

      const updated = await categoriesApi.updateCategory(editingCat.id, payload)
      addToast('Cập nhật danh mục dịch vụ thành công!', 'success')
      setCategories((prev) =>
        prev.map((c) => (c.id === editingCat.id ? { ...c, ...updated } : c))
      )
      setIsEditCatModalOpen(false)
      setEditingCat(null)
    } catch (err) {
      addToast(err.message || 'Lỗi cập nhật danh mục', 'error')
    }
  }

  const handleDeleteCategory = async (cat) => {
    if (!window.confirm(`Xóa danh mục "${cat.name}"?`)) return
    try {
      await categoriesApi.deleteCategory(cat.id)
      addToast('Đã xóa danh mục thành công!', 'success')
      setCategories((prev) => prev.filter((c) => c.id !== cat.id))
    } catch (err) {
      addToast(err.message || 'Không thể xóa danh mục', 'error')
    }
  }

  return (
    <div className="view-container">
      {/* Header */}
      <div className="view-header">
        <div>
          <h1 className="view-title">Phòng ban & Danh mục Dịch vụ</h1>
          <p className="view-subtitle">
            Cơ cấu tổ chức tiếp nhận hỗ trợ, quy định thời hạn cam kết SLA và phân quyền quản lý danh mục dịch vụ phụ trách
          </p>
        </div>
        <div className="header-actions">
          {isAdmin && (
            <button className="btn btn-outline" onClick={() => setIsDeptModalOpen(true)}>
              <Icon name="plus" size={16} />
              <span>Thêm phòng ban</span>
            </button>
          )}
          {(isAdmin || isDeptManager) && (
            <button className="btn btn-primary" onClick={() => handleOpenCreateCategory()}>
              <Icon name="plus" size={16} />
              <span>Thêm danh mục</span>
            </button>
          )}
        </div>
      </div>

      {/* Grid of Departments and their Categories */}
      {loading ? (
        <div className="loading-state">
          <span className="spinner"></span>
          <p>Đang tải thông tin cấu trúc tổ chức...</p>
        </div>
      ) : (
        <div className="departments-grid">
          {departments.map((dept) => {
            const deptCats = categories.filter((c) => c.department_id === dept.id)
            const canManageThisDept = canManageDeptCategories(dept.id)

            return (
              <div key={dept.id} className="dept-card">
                <div className="dept-card-header">
                  <div className="dept-icon-box">
                    <Icon name="building" size={24} />
                  </div>
                  <div className="dept-title-box">
                    <h3 className="dept-name">{dept.name}</h3>
                    <p className="dept-desc">
                      {dept.description || 'Chưa có thông tin mô tả chi tiết'}
                    </p>
                  </div>
                </div>

                <div className="dept-categories-list">
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '8px',
                    }}
                  >
                    <h4 className="dept-categories-title" style={{ margin: 0 }}>
                      Danh mục dịch vụ phụ trách ({deptCats.length}):
                    </h4>
                    {canManageThisDept && (
                      <button
                        type="button"
                        className="btn btn-xs btn-outline"
                        style={{ padding: '2px 8px', fontSize: '12px' }}
                        onClick={() => handleOpenCreateCategory(dept.id)}
                        title="Thêm danh mục phụ trách cho phòng ban này"
                      >
                        <Icon name="plus" size={12} />
                        <span>Thêm</span>
                      </button>
                    )}
                  </div>

                  {deptCats.length === 0 ? (
                    <div className="text-muted text-xs p-2">Chưa có danh mục trực thuộc.</div>
                  ) : (
                    <div className="cat-items">
                      {deptCats.map((cat) => (
                        <div key={cat.id} className="cat-item">
                          <div className="cat-item-info">
                            <span className="cat-item-name">{cat.name}</span>
                            {cat.description && (
                              <span className="cat-item-desc">{cat.description}</span>
                            )}
                            <div className="cat-sla-row">
                              <span>⏱ Phản hồi: {cat.sla_response_minutes} phút</span>
                              <span>• Xử lý: {Math.round(cat.sla_resolve_minutes / 60)} giờ</span>
                            </div>
                          </div>
                          {canManageThisDept && (
                            <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                              <button
                                className="btn-icon text-primary"
                                title="Chỉnh sửa danh mục"
                                onClick={() => handleOpenEditCategory(cat)}
                              >
                                <Icon name="edit" size={14} />
                              </button>
                              <button
                                className="btn-icon text-red"
                                title="Xóa danh mục"
                                onClick={() => handleDeleteCategory(cat)}
                              >
                                <Icon name="trash" size={14} />
                              </button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Modal Add Department (ADMIN only) */}
      <Modal
        isOpen={isDeptModalOpen}
        onClose={() => setIsDeptModalOpen(false)}
        title="Thêm phòng ban mới"
      >
        <form onSubmit={handleCreateDept} className="generic-form">
          <div className="form-group">
            <label className="form-label">Tên phòng ban <span className="text-red">*</span></label>
            <input
              type="text"
              className="form-input"
              placeholder="Ví dụ: Phòng Quản trị Thiết bị"
              value={deptName}
              onChange={(e) => setDeptName(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Mô tả chức năng nhiệm vụ</label>
            <textarea
              className="form-textarea"
              rows="3"
              placeholder="Chuyên xử lý các sự cố về trang thiết bị phòng học, máy chiếu..."
              value={deptDesc}
              onChange={(e) => setDeptDesc(e.target.value)}
            />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={() => setIsDeptModalOpen(false)}>
              Hủy
            </button>
            <button type="submit" className="btn btn-primary">
              Tạo phòng ban
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal Add Category (ADMIN & DEPT_MANAGER) */}
      <Modal
        isOpen={isCatModalOpen}
        onClose={() => setIsCatModalOpen(false)}
        title="Thêm danh mục dịch vụ hỗ trợ"
      >
        <form onSubmit={handleCreateCat} className="generic-form">
          <div className="form-group">
            <label className="form-label">Phòng ban phụ trách <span className="text-red">*</span></label>
            <select
              className="form-select"
              value={catDeptId}
              onChange={(e) => setCatDeptId(e.target.value)}
              disabled={!isAdmin && isDeptManager}
              required
            >
              {departments
                .filter((d) => isAdmin || String(d.id) === String(user?.department_id))
                .map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
            </select>
            {!isAdmin && isDeptManager && (
              <span className="text-xs text-muted" style={{ marginTop: '4px', display: 'block' }}>
                * Với quyền Trưởng bộ phận, bạn chỉ tạo danh mục cho phòng ban của mình.
              </span>
            )}
          </div>
          <div className="form-group">
            <label className="form-label">Tên danh mục dịch vụ <span className="text-red">*</span></label>
            <input
              type="text"
              className="form-input"
              placeholder="Ví dụ: Sự cố Cáp mạng & Wifi phòng Lab"
              value={catName}
              onChange={(e) => setCatName(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Mô tả chi tiết dịch vụ</label>
            <textarea
              className="form-textarea"
              rows="2"
              placeholder="Các lỗi mất tín hiệu mạng, không thể kết nối mạng dây..."
              value={catDesc}
              onChange={(e) => setCatDesc(e.target.value)}
            />
          </div>
          <div className="form-row">
            <div className="form-group col">
              <label className="form-label">SLA Phản hồi (phút)</label>
              <input
                type="number"
                className="form-input"
                min="1"
                value={slaResponse}
                onChange={(e) => setSlaResponse(e.target.value)}
              />
            </div>
            <div className="form-group col">
              <label className="form-label">SLA Giải quyết (phút)</label>
              <input
                type="number"
                className="form-input"
                min="1"
                value={slaResolve}
                onChange={(e) => setSlaResolve(e.target.value)}
              />
            </div>
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={() => setIsCatModalOpen(false)}>
              Hủy
            </button>
            <button type="submit" className="btn btn-primary">
              Tạo danh mục
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal Edit Category (ADMIN & DEPT_MANAGER) */}
      <Modal
        isOpen={isEditCatModalOpen}
        onClose={() => {
          setIsEditCatModalOpen(false)
          setEditingCat(null)
        }}
        title="Chỉnh sửa danh mục dịch vụ"
      >
        <form onSubmit={handleUpdateCat} className="generic-form">
          {isAdmin && (
            <div className="form-group">
              <label className="form-label">Phòng ban phụ trách <span className="text-red">*</span></label>
              <select
                className="form-select"
                value={editCatDeptId}
                onChange={(e) => setEditCatDeptId(e.target.value)}
                required
              >
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div className="form-group">
            <label className="form-label">Tên danh mục dịch vụ <span className="text-red">*</span></label>
            <input
              type="text"
              className="form-input"
              value={editCatName}
              onChange={(e) => setEditCatName(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Mô tả chi tiết dịch vụ</label>
            <textarea
              className="form-textarea"
              rows="2"
              value={editCatDesc}
              onChange={(e) => setEditCatDesc(e.target.value)}
            />
          </div>
          <div className="form-row">
            <div className="form-group col">
              <label className="form-label">SLA Phản hồi (phút)</label>
              <input
                type="number"
                className="form-input"
                min="1"
                value={editSlaResponse}
                onChange={(e) => setEditSlaResponse(e.target.value)}
              />
            </div>
            <div className="form-group col">
              <label className="form-label">SLA Giải quyết (phút)</label>
              <input
                type="number"
                className="form-input"
                min="1"
                value={editSlaResolve}
                onChange={(e) => setEditSlaResolve(e.target.value)}
              />
            </div>
          </div>
          <div className="form-group">
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={editIsActive}
                onChange={(e) => setEditIsActive(e.target.checked)}
              />
              <span className="form-label" style={{ margin: 0 }}>Đang hoạt động (Kích hoạt cho tiếp nhận sự cố)</span>
            </label>
          </div>
          <div className="modal-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                setIsEditCatModalOpen(false)
                setEditingCat(null)
              }}
            >
              Hủy
            </button>
            <button type="submit" className="btn btn-primary">
              <Icon name="check" size={16} />
              <span>Lưu thay đổi</span>
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
