import React, { useState, useEffect, useCallback } from 'react'
import { knowledgeApi } from '../../api/knowledge'
import { categoriesApi } from '../../api/categories'
import { useAuth } from '../../context/AuthContext'
import { DocStatusBadge } from '../common/Badge'
import { Icon } from '../common/Icons'
import { CreateDocModal } from './CreateDocModal'
import { DocDetailModal } from './DocDetailModal'

export function KnowledgeView() {
  const { addToast } = useAuth()
  const [documents, setDocuments] = useState([])
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterCat, setFilterCat] = useState('')
  const [filterStatus, setFilterStatus] = useState('')

  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [selectedDoc, setSelectedDoc] = useState(null)
  const [isDetailOpen, setIsDetailOpen] = useState(false)

  const loadCategories = async () => {
    try {
      const data = await categoriesApi.listCategories()
      setCategories(data)
    } catch {
      // Ignored
    }
  }

  const loadDocuments = useCallback(async () => {
    setLoading(true)
    try {
      const params = {}
      if (filterCat) params.category_id = filterCat
      if (filterStatus) params.status = filterStatus
      const data = await knowledgeApi.listDocuments(params)
      setDocuments(data)
    } catch (err) {
      addToast(err.message || 'Không thể tải cơ sở tri thức', 'error')
    } finally {
      setLoading(false)
    }
  }, [filterCat, filterStatus, addToast])

  useEffect(() => {
    loadCategories()
  }, [])

  useEffect(() => {
    loadDocuments()
  }, [loadDocuments])

  const handleTogglePublish = async (e, doc) => {
    e.stopPropagation()
    try {
      if (doc.is_published) {
        await knowledgeApi.unpublishDocument(doc.id)
        addToast('Đã chuyển tài liệu về trạng thái Bản nháp', 'info')
      } else {
        await knowledgeApi.publishDocument(doc.id)
        addToast('Đã xuất bản tài liệu cho tìm kiếm RAG', 'success')
      }
      loadDocuments()
    } catch (err) {
      addToast(err.message || 'Lỗi cập nhật trạng thái xuất bản', 'error')
    }
  }

  const handleReprocess = async (e, doc) => {
    e.stopPropagation()
    try {
      await knowledgeApi.reprocessDocument(doc.id)
      addToast('Đã gửi yêu cầu tính toán lại Vector Embeddings!', 'success')
      loadDocuments()
    } catch (err) {
      addToast(err.message || 'Lỗi xử lý tài liệu', 'error')
    }
  }

  const handleDelete = async (e, doc) => {
    e.stopPropagation()
    if (!window.confirm(`Bạn có chắc chắn muốn xóa tài liệu "${doc.title}"?`)) {
      return
    }

    try {
      await knowledgeApi.deleteDocument(doc.id)
      addToast('Đã xóa tài liệu khỏi cơ sở tri thức', 'success')
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id))
    } catch (err) {
      addToast(err.message || 'Lỗi khi xóa tài liệu', 'error')
    }
  }

  const handleOpenDetail = (doc) => {
    setSelectedDoc(doc)
    setIsDetailOpen(true)
  }

  const filteredDocs = documents.filter((doc) => {
    if (!searchTerm.trim()) return true
    const term = searchTerm.toLowerCase()
    return (
      doc.title.toLowerCase().includes(term) ||
      (doc.content && doc.content.toLowerCase().includes(term)) ||
      (doc.category_name && doc.category_name.toLowerCase().includes(term))
    )
  })

  return (
    <div className="view-container">
      {/* Header */}
      <div className="view-header">
        <div>
          <h1 className="view-title">Cơ sở tri thức RAG (Knowledge Base)</h1>
          <p className="view-subtitle">
            Quản lý tài liệu nguồn, trích xuất văn bản và phân đoạn vector pgvector phục vụ Chatbot AI
          </p>
        </div>
        <div className="header-actions">
          <button className="btn btn-outline" onClick={loadDocuments} disabled={loading} title="Làm mới">
            <Icon name="refresh" size={16} />
            <span>Làm mới</span>
          </button>
          <button className="btn btn-primary" onClick={() => setIsCreateOpen(true)}>
            <Icon name="plus" size={16} />
            <span>Thêm tài liệu</span>
          </button>
        </div>
      </div>

      {/* Filter and Search */}
      <div className="filter-card">
        <div className="search-box">
          <Icon name="search" size={18} className="search-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Tìm kiếm theo tiêu đề hoặc nội dung tài liệu..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="filter-group">
          <select
            className="filter-select"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            <option value="">Tất cả trạng thái xử lý</option>
            <option value="READY">Sẵn sàng (READY)</option>
            <option value="PROCESSING">Đang xử lý (PROCESSING)</option>
            <option value="PENDING">Chờ xử lý (PENDING)</option>
            <option value="FAILED">Thất bại (FAILED)</option>
          </select>

          <select
            className="filter-select"
            value={filterCat}
            onChange={(e) => setFilterCat(e.target.value)}
          >
            <option value="">Tất cả danh mục</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="table-card">
        {loading ? (
          <div className="loading-state">
            <span className="spinner"></span>
            <p>Đang tải tài liệu...</p>
          </div>
        ) : filteredDocs.length === 0 ? (
          <div className="empty-state">
            <Icon name="book" size={48} className="empty-icon" />
            <h3>Chưa có tài liệu nào</h3>
            <p>Thêm bài viết hướng dẫn hoặc tải lên tệp PDF/DOCX để AI có nguồn tri thức trả lời sinh viên.</p>
            <button className="btn btn-primary btn-sm" onClick={() => setIsCreateOpen(true)}>
              <Icon name="plus" size={16} />
              <span>Thêm tài liệu ngay</span>
            </button>
          </div>
        ) : (
          <div className="responsive-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Tài liệu</th>
                  <th>Danh mục</th>
                  <th>Số Chunks</th>
                  <th>Trạng thái AI</th>
                  <th>Xuất bản</th>
                  <th>Cập nhật</th>
                  <th>Hành động</th>
                </tr>
              </thead>
              <tbody>
                {filteredDocs.map((doc) => (
                  <tr key={doc.id} className="table-row-clickable" onClick={() => handleOpenDetail(doc)}>
                    <td>
                      <div className="doc-col">
                        <span className="doc-title-text">{doc.title}</span>
                        {doc.file_name && (
                          <span className="doc-file-tag">📎 {doc.file_name}</span>
                        )}
                      </div>
                    </td>
                    <td>
                      <span className="cat-badge-text">
                        {doc.category_name || 'Chung'}
                      </span>
                    </td>
                    <td>
                      <span className="chunk-pill">{doc.chunk_count || 0} chunks</span>
                    </td>
                    <td>
                      <DocStatusBadge status={doc.processing_status} />
                    </td>
                    <td>
                      <button
                        className={`toggle-publish-btn ${doc.is_published ? 'pub' : 'draft'}`}
                        onClick={(e) => handleTogglePublish(e, doc)}
                        title="Bật/tắt xuất bản"
                      >
                        {doc.is_published ? '🟢 Công khai' : '⚪ Bản nháp'}
                      </button>
                    </td>
                    <td className="text-muted text-xs whitespace-nowrap">
                      {new Date(doc.updated_at).toLocaleDateString('vi-VN')}
                    </td>
                    <td>
                      <div className="table-actions-row">
                        <button
                          className="btn-icon"
                          title="Tính toán lại Vector Embedding"
                          onClick={(e) => handleReprocess(e, doc)}
                        >
                          <Icon name="refresh" size={15} />
                        </button>
                        <button
                          className="btn-icon text-red"
                          title="Xóa tài liệu"
                          onClick={(e) => handleDelete(e, doc)}
                        >
                          <Icon name="trash" size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modals */}
      <CreateDocModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onCreated={() => loadDocuments()}
      />

      <DocDetailModal
        doc={selectedDoc}
        isOpen={isDetailOpen}
        onClose={() => {
          setIsDetailOpen(false)
          setSelectedDoc(null)
        }}
      />
    </div>
  )
}

