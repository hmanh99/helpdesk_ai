import React, { useState, useEffect } from 'react'
import { knowledgeApi } from '../../api/knowledge'
import { useAuth } from '../../context/AuthContext'
import { Modal } from '../common/Modal'
import { DocStatusBadge } from '../common/Badge'
import { Icon } from '../common/Icons'

export function DocDetailModal({ doc, isOpen, onClose }) {
  const { addToast } = useAuth()
  const [chunks, setChunks] = useState([])
  const [loadingChunks, setLoadingChunks] = useState(false)
  const [activeTab, setActiveTab] = useState('content') // 'content' | 'chunks'

  useEffect(() => {
    if (isOpen && doc?.id) {
      setLoadingChunks(true)
      knowledgeApi
        .getChunks(doc.id)
        .then((data) => setChunks(data))
        .catch(() => {
          setChunks([])
        })
        .finally(() => setLoadingChunks(false))
    }
  }, [isOpen, doc])

  if (!doc) return null

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Chi tiết tài liệu tri thức`}
      maxWidth="800px"
    >
      <div className="doc-detail-view">
        <div className="doc-detail-header">
          <div>
            <h2 className="doc-modal-title">{doc.title}</h2>
            <div className="doc-modal-meta">
              <DocStatusBadge status={doc.processing_status} />
              <span className={`publish-tag ${doc.is_published ? 'published' : 'draft'}`}>
                {doc.is_published ? '🟢 Đã xuất bản' : '🟡 Bản nháp'}
              </span>
              {doc.category_name && (
                <span className="doc-cat-tag">📂 {doc.category_name}</span>
              )}
            </div>
          </div>
        </div>

        {/* Tab switch */}
        <div className="tab-buttons mb-3">
          <button
            type="button"
            className={`tab-btn ${activeTab === 'content' ? 'active' : ''}`}
            onClick={() => setActiveTab('content')}
          >
            <Icon name="fileText" size={16} />
            <span>Nội dung tài liệu</span>
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === 'chunks' ? 'active' : ''}`}
            onClick={() => setActiveTab('chunks')}
          >
            <Icon name="sparkles" size={16} />
            <span>Phân đoạn Vector Chunks ({chunks.length})</span>
          </button>
        </div>

        {activeTab === 'content' ? (
          <div className="doc-content-body">
            {doc.source_url && (
              <div className="doc-source-bar">
                <span>Nguồn liên kết:</span>
                <a href={doc.source_url} target="_blank" rel="noreferrer">
                  {doc.source_url}
                  <Icon name="externalLink" size={12} />
                </a>
              </div>
            )}
            <div className="doc-text-display">{doc.content}</div>
          </div>
        ) : (
          <div className="doc-chunks-body">
            {loadingChunks ? (
              <div className="loading-state">
                <span className="spinner"></span>
                <p>Đang tải danh sách chunk vectors...</p>
              </div>
            ) : chunks.length === 0 ? (
              <div className="empty-state-sm">
                Chưa có phân đoạn nào (hoặc tài liệu chưa hoàn tất xử lý embedding).
              </div>
            ) : (
              <div className="chunks-list">
                {chunks.map((chk, idx) => (
                  <div key={chk.id || idx} className="chunk-card">
                    <div className="chunk-header">
                      <span className="chunk-index">Chunk #{chk.chunk_index + 1}</span>
                      {chk.token_count !== null && (
                        <span className="chunk-tokens">~{chk.token_count} tokens</span>
                      )}
                    </div>
                    <div className="chunk-text">{chk.content}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Đóng
          </button>
        </div>
      </div>
    </Modal>
  )
}

