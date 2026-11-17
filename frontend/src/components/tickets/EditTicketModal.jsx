import React, { useState, useEffect } from 'react'
import { ticketsApi } from '../../api/tickets'
import { categoriesApi } from '../../api/categories'
import { useAuth } from '../../context/AuthContext'
import { Modal } from '../common/Modal'
import { Icon } from '../common/Icons'

export function EditTicketModal({ ticket, isOpen, onClose, onUpdated }) {
  const { addToast } = useAuth()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [priority, setPriority] = useState('MEDIUM')
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isOpen && ticket) {
      setTitle(ticket.title || '')
      setDescription(ticket.description || '')
      setCategoryId(ticket.category_id || '')
      setPriority(ticket.priority || 'MEDIUM')

      categoriesApi
        .listCategories({ active_only: true })
        .then((cats) => setCategories(cats))
        .catch(() => {})
    }
  }, [isOpen, ticket])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!title.trim() || !description.trim()) {
      addToast('Vui lòng nhập tiêu đề và nội dung chi tiết', 'error')
      return
    }

    setLoading(true)
    try {
      const payload = {
        title: title.trim(),
        description: description.trim(),
        priority,
        category_id: categoryId ? categoryId : null,
      }
      const updatedTicket = await ticketsApi.updateTicket(ticket.id, payload)
      addToast('Cập nhật phiếu hỗ trợ thành công!', 'success')
      if (onUpdated) onUpdated(updatedTicket)
      onClose()
    } catch (err) {
      addToast(err.message || 'Lỗi khi cập nhật ticket', 'error')
    } finally {
      setLoading(false)
    }
  }

  if (!ticket) return null

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Chỉnh sửa Phiếu hỗ trợ #${ticket.id.substring(0, 8)}`}
    >
      <form onSubmit={handleSubmit} className="ticket-form">
        <div className="form-group">
          <label className="form-label">
            Tiêu đề yêu cầu / sự cố <span className="text-red">*</span>
          </label>
          <input
            type="text"
            className="form-input"
            placeholder="Ví dụ: Không thể đăng nhập vào cổng đăng ký học phần"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label">
            Chi tiết nội dung sự cố <span className="text-red">*</span>
          </label>
          <textarea
            className="form-textarea"
            rows="4"
            placeholder="Mô tả cụ thể vấn đề gặp phải..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
          />
        </div>

        <div className="form-row">
          <div className="form-group col">
            <label className="form-label">Danh mục dịch vụ</label>
            <select
              className="form-select"
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
            >
              <option value="">-- Chọn danh mục dịch vụ --</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} {c.department_name ? `(${c.department_name})` : ''}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group col">
            <label className="form-label">Mức độ ưu tiên</label>
            <select
              className="form-select"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
            >
              <option value="LOW">Thấp (LOW)</option>
              <option value="MEDIUM">Trung bình (MEDIUM)</option>
              <option value="HIGH">Cao (HIGH)</option>
              <option value="CRITICAL">Khẩn cấp (CRITICAL)</option>
            </select>
          </div>
        </div>

        <div className="modal-actions">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClose}
            disabled={loading}
          >
            Hủy
          </button>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            <Icon name="check" size={16} />
            <span>{loading ? 'Đang lưu...' : 'Lưu thay đổi'}</span>
          </button>
        </div>
      </form>
    </Modal>
  )
}
