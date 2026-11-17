import React, { useState, useEffect } from 'react'
import { ticketsApi } from '../../api/tickets'
import { categoriesApi } from '../../api/categories'
import { useAuth } from '../../context/AuthContext'
import { Modal } from '../common/Modal'
import { Icon } from '../common/Icons'

export function CreateTicketModal({ isOpen, onClose, onCreated }) {
  const { addToast } = useAuth()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [priority, setPriority] = useState('MEDIUM')
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isOpen) {
      categoriesApi
        .listCategories({ active_only: true })
        .then((cats) => setCategories(cats))
        .catch(() => {})
    }
  }, [isOpen])

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
        channel: 'WEB_FORM',
      }
      const newTicket = await ticketsApi.createTicket(payload)
      addToast('Đã gửi yêu cầu hỗ trợ thành công!', 'success')
      onCreated(newTicket)
      onClose()
      setTitle('')
      setDescription('')
      setCategoryId('')
      setPriority('MEDIUM')
    } catch (err) {
      addToast(err.message || 'Lỗi khi tạo ticket', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Tạo mới Phiếu hỗ trợ (Ticket)">
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
            placeholder="Mô tả cụ thể vấn đề gặp phải, thông báo lỗi nếu có..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
          />
        </div>

        <div className="form-row">
          <div className="form-group col">
            <label className="form-label">Danh mục yêu cầu</label>
            <select
              className="form-select"
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
            >
              <option value="">🤖 Để AI tự động phân loại & định tuyến</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} {c.department_name ? `(${c.department_name})` : ''}
                </option>
              ))}
            </select>
            <span className="form-hint">
              Hệ thống AI sẽ phân tích nội dung để chuyển tới phòng ban thích hợp nếu để trống.
            </span>
          </div>

          <div className="form-group col">
            <label className="form-label">Mức độ ưu tiên</label>
            <select
              className="form-select"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
            >
              <option value="LOW">Thấp (Low)</option>
              <option value="MEDIUM">Bình thường (Medium)</option>
              <option value="HIGH">Cao (High)</option>
              <option value="CRITICAL">Khẩn cấp (Critical)</option>
            </select>
          </div>
        </div>

        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
            Hủy bỏ
          </button>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? <span className="spinner"></span> : <Icon name="send" size={16} />}
            <span>Gửi phiếu hỗ trợ</span>
          </button>
        </div>
      </form>
    </Modal>
  )
}

