import React, { useState, useEffect } from 'react'
import { knowledgeApi } from '../../api/knowledge'
import { categoriesApi } from '../../api/categories'
import { useAuth } from '../../context/AuthContext'
import { Modal } from '../common/Modal'
import { Icon } from '../common/Icons'

export function CreateDocModal({ isOpen, onClose, onCreated }) {
  const { addToast } = useAuth()
  const [tab, setTab] = useState('text') // 'text' | 'file'
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [sourceUrl, setSourceUrl] = useState('')
  const [isPublished, setIsPublished] = useState(true)
  const [selectedFile, setSelectedFile] = useState(null)
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

    if (tab === 'text') {
      if (!title.trim() || !content.trim()) {
        addToast('Vui lòng nhập tiêu đề và nội dung bài viết', 'error')
        return
      }

      setLoading(true)
      try {
        const payload = {
          title: title.trim(),
          content: content.trim(),
          category_id: categoryId || null,
          source_url: sourceUrl.trim() || null,
        }
        const doc = await knowledgeApi.createDocument(payload)
        // If published was selected, publish it
        if (isPublished) {
          try {
            await knowledgeApi.publishDocument(doc.id)
          } catch {
            // Ignored
          }
        }
        addToast('Đã thêm tài liệu tri thức thành công!', 'success')
        onCreated(doc)
        resetForm()
        onClose()
      } catch (err) {
        addToast(err.message || 'Lỗi khi tạo tài liệu', 'error')
      } finally {
        setLoading(false)
      }
    } else {
      // File upload
      if (!selectedFile) {
        addToast('Vui lòng chọn tệp tài liệu để tải lên', 'error')
        return
      }

      setLoading(true)
      try {
        const formData = new FormData()
        formData.append('file', selectedFile)
        formData.append('title', title.trim() || selectedFile.name)
        if (categoryId) formData.append('category_id', categoryId)
        if (sourceUrl) formData.append('source_url', sourceUrl)
        formData.append('is_published', isPublished ? 'true' : 'false')

        const doc = await knowledgeApi.uploadDocument(formData)
        addToast('Tải lên và bắt đầu trích xuất tài liệu thành công!', 'success')
        onCreated(doc)
        resetForm()
        onClose()
      } catch (err) {
        addToast(err.message || 'Lỗi tải lên tệp', 'error')
      } finally {
        setLoading(false)
      }
    }
  }

  const resetForm = () => {
    setTitle('')
    setContent('')
    setCategoryId('')
    setSourceUrl('')
    setSelectedFile(null)
    setIsPublished(true)
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Thêm tài liệu vào Cơ sở tri thức (RAG)" maxWidth="700px">
      <div className="tab-buttons mb-4">
        <button
          type="button"
          className={`tab-btn ${tab === 'text' ? 'active' : ''}`}
          onClick={() => setTab('text')}
        >
          <Icon name="fileText" size={16} />
          <span>Nhập văn bản trực tiếp</span>
        </button>
        <button
          type="button"
          className={`tab-btn ${tab === 'file' ? 'active' : ''}`}
          onClick={() => setTab('file')}
        >
          <Icon name="upload" size={16} />
          <span>Tải tệp lên (PDF, DOCX, TXT, MD)</span>
        </button>
      </div>

      <form onSubmit={handleSubmit} className="knowledge-form">
        <div className="form-group">
          <label className="form-label">
            Tiêu đề tài liệu {tab === 'text' && <span className="text-red">*</span>}
          </label>
          <input
            type="text"
            className="form-input"
            placeholder={tab === 'file' ? 'Để trống nếu lấy theo tên tệp' : 'Ví dụ: Hướng dẫn kết nối VPN nội bộ'}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required={tab === 'text'}
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
              <option value="">-- Chọn danh mục (Không bắt buộc) --</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} {c.department_name ? `(${c.department_name})` : ''}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group col">
            <label className="form-label">Đường dẫn tham khảo (Source URL)</label>
            <input
              type="url"
              className="form-input"
              placeholder="https://..."
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
            />
          </div>
        </div>

        {tab === 'text' ? (
          <div className="form-group">
            <label className="form-label">
              Nội dung tri thức <span className="text-red">*</span>
            </label>
            <textarea
              className="form-textarea font-mono"
              rows="8"
              placeholder="Nhập nội dung tài liệu, quy trình, chính sách hoặc câu hỏi thường gặp..."
              value={content}
              onChange={(e) => setContent(e.target.value)}
              required
            />
            <span className="form-hint">
              Hệ thống sẽ tự động phân tách văn bản thành các chunks và tính toán vector embeddings cho tìm kiếm ngữ nghĩa.
            </span>
          </div>
        ) : (
          <div className="form-group">
            <label className="form-label">
              Tệp tài liệu <span className="text-red">*</span>
            </label>
            <div className="file-dropzone">
              <input
                type="file"
                id="rag-file-input"
                className="file-hidden-input"
                accept=".pdf,.docx,.txt,.md"
                onChange={(e) => setSelectedFile(e.target.files[0] || null)}
                required
              />
              <label htmlFor="rag-file-input" className="dropzone-label">
                <Icon name="upload" size={32} />
                <span className="dropzone-text">
                  {selectedFile ? selectedFile.name : 'Kéo thả hoặc nhấn để chọn tệp tài liệu'}
                </span>
                <span className="dropzone-hint">Định dạng hỗ trợ: PDF, DOCX, TXT, Markdown (Tối đa 25MB)</span>
              </label>
            </div>
          </div>
        )}

        <div className="form-group checkbox-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={isPublished}
              onChange={(e) => setIsPublished(e.target.checked)}
            />
            <span>Xuất bản ngay (Sẵn sàng phục vụ hỏi đáp AI sau khi xử lý xong)</span>
          </label>
        </div>

        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
            Hủy bỏ
          </button>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? <span className="spinner"></span> : <Icon name="check" size={16} />}
            <span>{tab === 'text' ? 'Lưu tài liệu' : 'Tải lên & Xử lý'}</span>
          </button>
        </div>
      </form>
    </Modal>
  )
}

