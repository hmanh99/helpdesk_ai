import React, { useState, useEffect, useRef, useMemo } from 'react'
import { chatApi } from '../../api/chat'
import { useAuth } from '../../context/AuthContext'
import { Icon } from '../common/Icons'
import { PriorityBadge } from '../common/Badge'

export function ChatView({ onNavigateToTicket }) {
  const { addToast } = useAuth()
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [loadingSessions, setLoadingSessions] = useState(false)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [sending, setSending] = useState(false)
  const [createdTickets, setCreatedTickets] = useState({})
  const [expandedSources, setExpandedSources] = useState({})

  // Session search & management states
  const [sessionSearch, setSessionSearch] = useState('')
  const [editingSessionId, setEditingSessionId] = useState(null)
  const [editTitle, setEditTitle] = useState('')
  const [sessionToDelete, setSessionToDelete] = useState(null)
  const [isDeleting, setIsDeleting] = useState(false)

  // Header rename modal state
  const [isHeaderRenameOpen, setIsHeaderRenameOpen] = useState(false)
  const [headerRenameTitle, setHeaderRenameTitle] = useState('')

  const messagesEndRef = useRef(null)
  const renameInputRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  // Fetch chat sessions
  const loadSessions = async () => {
    setLoadingSessions(true)
    try {
      const data = await chatApi.listSessions()
      setSessions(data || [])
      if (data && data.length > 0 && !activeSessionId) {
        setActiveSessionId(data[0].id)
      } else if (!data || data.length === 0) {
        handleNewSession()
      }
    } catch (err) {
      addToast(err.message || 'Không thể tải danh sách phiên chat', 'error')
    } finally {
      setLoadingSessions(false)
    }
  }

  useEffect(() => {
    loadSessions()
  }, [])

  // Focus input when editing starts
  useEffect(() => {
    if (editingSessionId && renameInputRef.current) {
      renameInputRef.current.focus()
      renameInputRef.current.select()
    }
  }, [editingSessionId])

  // Load active session messages
  useEffect(() => {
    if (!activeSessionId) return

    const loadSessionDetail = async () => {
      setLoadingMessages(true)
      try {
        const detail = await chatApi.getSession(activeSessionId)
        setMessages(detail.messages || [])
      } catch (err) {
        addToast(err.message || 'Không thể tải nội dung phiên chat', 'error')
      } finally {
        setLoadingMessages(false)
      }
    }

    loadSessionDetail()
  }, [activeSessionId])

  useEffect(() => {
    scrollToBottom()
  }, [messages, sending])

  // Create new chat session
  const handleNewSession = async () => {
    try {
      const newSession = await chatApi.createSession()
      setSessions((prev) => [newSession, ...prev])
      setActiveSessionId(newSession.id)
      setMessages([])
    } catch (err) {
      addToast(err.message || 'Không thể tạo phiên chat mới', 'error')
    }
  }

  // Rename session handlers
  const handleStartRename = (e, sess) => {
    e.stopPropagation()
    setEditingSessionId(sess.id)
    setEditTitle(sess.title || `Phiên #${sess.id.substring(0, 6)}`)
  }

  const handleSaveRename = async (sessionId) => {
    const trimmed = editTitle.trim()
    if (!trimmed) {
      addToast('Tên đoạn chat không được để trống', 'warning')
      return
    }
    try {
      const updated = await chatApi.updateSession(sessionId, trimmed)
      setSessions((prev) =>
        prev.map((s) => (s.id === sessionId ? { ...s, title: updated.title || trimmed } : s))
      )
      setEditingSessionId(null)
      addToast('Đã đổi tên đoạn chat thành công', 'success')
    } catch (err) {
      addToast(err.message || 'Lỗi khi đổi tên đoạn chat', 'error')
    }
  }

  const handleCancelRename = () => {
    setEditingSessionId(null)
    setEditTitle('')
  }

  // Header quick rename
  const handleOpenHeaderRename = () => {
    const current = sessions.find((s) => s.id === activeSessionId)
    setHeaderRenameTitle(current?.title || (current ? `Phiên #${current.id.substring(0, 6)}` : ''))
    setIsHeaderRenameOpen(true)
  }

  const handleSaveHeaderRename = async (e) => {
    e.preventDefault()
    if (!activeSessionId) return
    const trimmed = headerRenameTitle.trim()
    if (!trimmed) {
      addToast('Tên đoạn chat không được để trống', 'warning')
      return
    }
    try {
      const updated = await chatApi.updateSession(activeSessionId, trimmed)
      setSessions((prev) =>
        prev.map((s) => (s.id === activeSessionId ? { ...s, title: updated.title || trimmed } : s))
      )
      setIsHeaderRenameOpen(false)
      addToast('Đã đổi tên đoạn chat thành công', 'success')
    } catch (err) {
      addToast(err.message || 'Lỗi khi đổi tên đoạn chat', 'error')
    }
  }

  // Delete session handler
  const handleRequestDelete = (e, sess) => {
    e.stopPropagation()
    setSessionToDelete(sess)
  }

  const handleConfirmDelete = async () => {
    if (!sessionToDelete) return
    setIsDeleting(true)
    const targetId = sessionToDelete.id
    try {
      await chatApi.deleteSession(targetId)
      const remaining = sessions.filter((s) => s.id !== targetId)
      setSessions(remaining)
      setSessionToDelete(null)
      addToast('Đã xóa đoạn chat thành công', 'success')

      if (activeSessionId === targetId) {
        if (remaining.length > 0) {
          setActiveSessionId(remaining[0].id)
        } else {
          handleNewSession()
        }
      }
    } catch (err) {
      addToast(err.message || 'Không thể xóa đoạn chat', 'error')
    } finally {
      setIsDeleting(false)
    }
  }

  // Send message
  const handleSendMessage = async (e) => {
    e?.preventDefault()
    const content = inputMessage.trim()
    if (!content || sending) return

    let currentSessionId = activeSessionId
    if (!currentSessionId) {
      try {
        const newSession = await chatApi.createSession()
        setSessions((prev) => [newSession, ...prev])
        setActiveSessionId(newSession.id)
        currentSessionId = newSession.id
      } catch {
        addToast('Lỗi khi khởi tạo phiên chat', 'error')
        return
      }
    }

    // Optimistically append user message
    const tempUserMsg = {
      id: 'temp-' + Date.now(),
      sender: 'USER',
      content,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, tempUserMsg])
    setInputMessage('')
    setSending(true)

    // Auto-update local session title if it was default
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id === currentSessionId && !s.title) {
          return { ...s, title: content.substring(0, 50) }
        }
        return s
      })
    )

    try {
      const replyData = await chatApi.sendMessage(currentSessionId, content)
      setMessages((prev) => {
        const filtered = prev.filter((m) => m.id !== tempUserMsg.id)
        return [...filtered, tempUserMsg, replyData.message]
      })

      if (replyData.suggest_ticket && replyData.ticket_draft) {
        addToast('AI đã tạo bản nháp Ticket hỗ trợ cho bạn', 'info')
      }
    } catch (err) {
      addToast(err.message || 'Lỗi gửi tin nhắn đến chatbot', 'error')
    } finally {
      setSending(false)
    }
  }

  // Confirm ticket creation from session
  const handleConfirmTicket = async (draft) => {
    if (!activeSessionId) return
    try {
      const ticket = await chatApi.confirmTicket(activeSessionId, draft)
      setCreatedTickets((prev) => ({ ...prev, [activeSessionId]: ticket }))
      addToast(`Đã tạo Ticket #${ticket.id.substring(0, 8)} thành công!`, 'success')
      setSessions((prev) =>
        prev.map((s) => (s.id === activeSessionId ? { ...s, ticket_id: ticket.id } : s))
      )
    } catch (err) {
      addToast(err.message || 'Không thể tạo ticket từ phiên chat', 'error')
    }
  }

  const toggleSource = (msgId) => {
    setExpandedSources((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }))
  }

  const handleCopyText = (text) => {
    navigator.clipboard.writeText(text)
    addToast('Đã sao chép nội dung vào bộ nhớ tạm', 'success')
  }

  const quickPrompts = [
    'Làm sao để kết nối mạng Wi-Fi sinh viên?',
    'Cách reset mật khẩu cổng thông tin đào tạo?',
    'Thủ tục cấp lại thẻ sinh viên bị mất?',
    'Thời gian nộp học phí học kỳ hiện tại là khi nào?',
  ]

  // Filtered sessions based on search
  const filteredSessions = useMemo(() => {
    if (!sessionSearch.trim()) return sessions
    const q = sessionSearch.trim().toLowerCase()
    return sessions.filter((s) => {
      const name = (s.title || `Phiên #${s.id.substring(0, 6)}`).toLowerCase()
      return name.includes(q)
    })
  }, [sessions, sessionSearch])

  const activeSession = sessions.find((s) => s.id === activeSessionId)
  const activeTitle = activeSession?.title || (activeSession ? `Phiên #${activeSession.id.substring(0, 6)}` : 'Đoạn chat mới')

  return (
    <div className="chat-layout">
      {/* Sessions Sidebar */}
      <aside className="chat-sessions-pane">
        <div className="chat-pane-header">
          <button className="btn btn-primary btn-block new-chat-btn" onClick={handleNewSession}>
            <Icon name="plus" size={16} />
            <span>Đoạn chat mới</span>
          </button>
        </div>

        {/* Search Session Bar */}
        <div className="chat-search-wrap">
          <div className="chat-search-box">
            <Icon name="search" size={14} className="search-icon" />
            <input
              type="text"
              className="chat-search-input"
              placeholder="Tìm kiếm đoạn chat..."
              value={sessionSearch}
              onChange={(e) => setSessionSearch(e.target.value)}
            />
            {sessionSearch && (
              <button
                type="button"
                className="clear-search-btn"
                onClick={() => setSessionSearch('')}
              >
                <Icon name="x" size={12} />
              </button>
            )}
          </div>
        </div>

        {/* Sessions List */}
        <div className="sessions-list">
          {loadingSessions ? (
            <div className="loading-state">
              <span className="spinner"></span>
            </div>
          ) : filteredSessions.length === 0 ? (
            <div className="empty-state-sm">
              {sessionSearch ? 'Không tìm thấy đoạn chat phù hợp' : 'Chưa có đoạn chat nào'}
            </div>
          ) : (
            filteredSessions.map((sess) => {
              const isActive = sess.id === activeSessionId
              const isEditing = sess.id === editingSessionId
              const timeStr = new Date(sess.started_at).toLocaleDateString('vi-VN', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })
              const displayTitle = sess.title || `Phiên #${sess.id.substring(0, 6)}`

              return (
                <div
                  key={sess.id}
                  className={`session-item ${isActive ? 'active' : ''}`}
                  onClick={() => {
                    if (!isEditing) setActiveSessionId(sess.id)
                  }}
                >
                  <div className="session-icon">
                    <Icon name="message" size={16} />
                  </div>

                  <div className="session-info">
                    {isEditing ? (
                      <div className="session-inline-edit" onClick={(e) => e.stopPropagation()}>
                        <input
                          ref={renameInputRef}
                          type="text"
                          className="session-edit-input"
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleSaveRename(sess.id)
                            if (e.key === 'Escape') handleCancelRename()
                          }}
                        />
                        <button
                          type="button"
                          className="action-icon-btn save-btn"
                          title="Lưu (Enter)"
                          onClick={() => handleSaveRename(sess.id)}
                        >
                          <Icon name="check" size={14} />
                        </button>
                        <button
                          type="button"
                          className="action-icon-btn cancel-btn"
                          title="Hủy (Esc)"
                          onClick={handleCancelRename}
                        >
                          <Icon name="x" size={14} />
                        </button>
                      </div>
                    ) : (
                      <>
                        <div className="session-title" title={displayTitle}>
                          {displayTitle}
                        </div>
                        <div className="session-meta">
                          <span>{timeStr}</span>
                          {sess.ticket_id && (
                            <span className="badge-tag" title="Đã chuyển thành Ticket">
                              Ticket
                            </span>
                          )}
                        </div>
                      </>
                    )}
                  </div>

                  {/* Actions (Rename & Delete) */}
                  {!isEditing && (
                    <div className="session-item-actions">
                      <button
                        type="button"
                        className="session-action-btn"
                        title="Đổi tên đoạn chat"
                        onClick={(e) => handleStartRename(e, sess)}
                      >
                        <Icon name="edit" size={13} />
                      </button>
                      <button
                        type="button"
                        className="session-action-btn delete"
                        title="Xóa đoạn chat"
                        onClick={(e) => handleRequestDelete(e, sess)}
                      >
                        <Icon name="trash" size={13} />
                      </button>
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
      </aside>

      {/* Main Chat Conversation View */}
      <div className="chat-main-pane">
        {/* Chat Header */}
        <div className="chat-header-bar">
          <div className="chat-header-title">
            <div className="bot-avatar">
              <Icon name="bot" size={20} />
            </div>
            <div className="chat-header-info">
              <div className="chat-title-row">
                <h3 className="active-session-name" title={activeTitle}>
                  {activeTitle}
                </h3>
                {activeSession && (
                  <button
                    type="button"
                    className="title-rename-btn"
                    onClick={handleOpenHeaderRename}
                    title="Đổi tên đoạn chat hiện tại"
                  >
                    <Icon name="edit" size={13} />
                  </button>
                )}
              </div>
              <p className="online-text">
                <span className="status-dot online"></span> Trợ lý ảo Helpdesk AI • Cơ sở tri thức NEU RAG
              </p>
            </div>
          </div>
        </div>

        {/* Messages Stream */}
        <div className="chat-messages-container">
          {loadingMessages ? (
            <div className="loading-state">
              <span className="spinner"></span>
              <p>Đang tải hội thoại...</p>
            </div>
          ) : messages.length === 0 ? (
            <div className="chat-welcome">
              <div className="welcome-icon">
                <Icon name="sparkles" size={40} />
              </div>
              <h2>Xin chào! Bạn cần hỗ trợ gì hôm nay?</h2>
              <p>
                Trợ lý ảo thông minh NEU tra cứu cơ sở tri thức chính xác hoặc hướng dẫn bạn gửi phiếu yêu cầu trực tiếp đến các phòng ban phụ trách.
              </p>

              <div className="quick-prompts-grid">
                {quickPrompts.map((prompt, idx) => (
                  <button
                    key={idx}
                    className="prompt-card"
                    onClick={() => {
                      setInputMessage(prompt)
                    }}
                  >
                    <span>{prompt}</span>
                    <Icon name="chevronRight" size={14} />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="messages-stream">
              {messages.map((msg) => {
                const isUser = msg.sender === 'USER'
                const hasSources = msg.sources && msg.sources.length > 0
                const isExpanded = expandedSources[msg.id]
                const draft = msg.ticket_draft

                return (
                  <div
                    key={msg.id}
                    className={`chat-bubble-row ${isUser ? 'user-row' : 'bot-row'}`}
                  >
                    {!isUser && (
                      <div className="bubble-avatar bot">
                        <Icon name="bot" size={18} />
                      </div>
                    )}

                    <div className="bubble-content-wrap">
                      <div className={`chat-bubble ${isUser ? 'user-bubble' : 'bot-bubble'}`}>
                        <div className="bubble-text">{msg.content}</div>

                        {/* Copy button for bot response */}
                        {!isUser && (
                          <div className="bubble-actions-toolbar">
                            <button
                              type="button"
                              className="copy-bubble-btn"
                              title="Sao chép nội dung"
                              onClick={() => handleCopyText(msg.content)}
                            >
                              <Icon name="copy" size={13} />
                              <span>Sao chép</span>
                            </button>
                          </div>
                        )}

                        {/* RAG Sources Accordion */}
                        {hasSources && (
                          <div className="rag-sources-box">
                            <button
                              type="button"
                              className="rag-sources-header"
                              onClick={() => toggleSource(msg.id)}
                            >
                              <Icon name="book" size={14} />
                              <span>Trích dẫn từ {msg.sources.length} tài liệu cơ sở tri thức</span>
                              <Icon
                                name="chevronRight"
                                size={14}
                                className={`chevron ${isExpanded ? 'rotate-90' : ''}`}
                              />
                            </button>

                            {isExpanded && (
                              <div className="rag-sources-list">
                                {msg.sources.map((src, sIdx) => (
                                  <div key={sIdx} className="rag-source-item">
                                    <div className="src-title">
                                      <span>{src.title}</span>
                                      <span className="src-score">
                                        Độ khớp: {Math.round(src.relevance_score * 100)}%
                                      </span>
                                    </div>
                                    {src.source_url && (
                                      <a
                                        href={src.source_url}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="src-link"
                                      >
                                        <Icon name="externalLink" size={12} />
                                        <span>Xem tài liệu gốc</span>
                                      </a>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Ticket Draft Suggestion Box */}
                        {draft && !isUser && (
                          <div className="ticket-draft-card">
                            <div className="draft-header">
                              <div className="draft-badge">
                                <Icon name="ticket" size={16} />
                                <span>Bản nháp Phiếu hỗ trợ (Ticket)</span>
                              </div>
                              {draft.suggested_priority && (
                                <PriorityBadge priority={draft.suggested_priority} />
                              )}
                            </div>

                            <div className="draft-content">
                              <div className="draft-field">
                                <span className="field-lbl">Tiêu đề:</span>
                                <span className="field-val font-semibold">{draft.title}</span>
                              </div>
                              <div className="draft-field">
                                <span className="field-lbl">Mô tả:</span>
                                <span className="field-val">{draft.description}</span>
                              </div>
                              {draft.predicted_category_name && (
                                <div className="draft-field">
                                  <span className="field-lbl">Phòng ban / Danh mục:</span>
                                  <span className="field-val">{draft.predicted_category_name}</span>
                                </div>
                              )}
                            </div>

                            <div className="draft-actions">
                              {createdTickets[activeSessionId] ? (
                                <div className="ticket-created-banner">
                                  <Icon name="check" size={16} />
                                  <span>Ticket đã tạo thành công!</span>
                                  <button
                                    type="button"
                                    className="btn btn-sm btn-link"
                                    onClick={() => onNavigateToTicket(createdTickets[activeSessionId].id)}
                                  >
                                    Xem chi tiết Ticket #{createdTickets[activeSessionId].id.substring(0, 8)}
                                  </button>
                                </div>
                              ) : (
                                <button
                                  type="button"
                                  className="btn btn-primary btn-sm"
                                  onClick={() => handleConfirmTicket(draft)}
                                >
                                  <Icon name="ticket" size={16} />
                                  <span>Xác nhận tạo Phiếu hỗ trợ ngay</span>
                                </button>
                              )}
                            </div>
                          </div>
                        )}
                      </div>

                      <div className="bubble-timestamp">
                        {new Date(msg.created_at).toLocaleTimeString('vi-VN', {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </div>
                    </div>

                    {isUser && (
                      <div className="bubble-avatar user">
                        <Icon name="user" size={18} />
                      </div>
                    )}
                  </div>
                )
              })}

              {sending && (
                <div className="chat-bubble-row bot-row">
                  <div className="bubble-avatar bot">
                    <Icon name="bot" size={18} />
                  </div>
                  <div className="chat-bubble bot-bubble typing-bubble">
                    <div className="typing-dots">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                    <span className="typing-text">AI đang phân tích và tra cứu cơ sở tri thức...</span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Chat Input Bar */}
        <div className="chat-input-bar">
          <form onSubmit={handleSendMessage} className="chat-form">
            <textarea
              className="chat-textarea"
              rows="1"
              placeholder="Nhập câu hỏi hoặc yêu cầu cần hỗ trợ... (Enter để gửi, Shift+Enter xuống dòng)"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSendMessage()
                }
              }}
              disabled={sending}
            />
            <button
              type="submit"
              className="btn btn-primary send-btn"
              disabled={!inputMessage.trim() || sending}
              aria-label="Gửi tin nhắn"
            >
              <Icon name="send" size={18} />
            </button>
          </form>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {sessionToDelete && (
        <div className="modal-backdrop" onClick={() => setSessionToDelete(null)}>
          <div className="modal-dialog modal-sm" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-wrap">
                <div className="modal-icon-badge danger">
                  <Icon name="trash" size={18} />
                </div>
                <h3>Xóa đoạn chat này?</h3>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setSessionToDelete(null)}
              >
                <Icon name="x" size={18} />
              </button>
            </div>
            <div className="modal-body">
              <p className="confirm-text">
                Bạn có chắc chắn muốn xóa đoạn chat <strong>"{sessionToDelete.title || `Phiên #${sessionToDelete.id.substring(0, 6)}`}"</strong>?
              </p>
              <p className="confirm-subtext">
                Toàn bộ tin nhắn và lịch sử tư vấn trong đoạn chat này sẽ bị xóa vĩnh viễn và không thể khôi phục.
              </p>
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => setSessionToDelete(null)}
                disabled={isDeleting}
              >
                Hủy bỏ
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={handleConfirmDelete}
                disabled={isDeleting}
              >
                {isDeleting ? 'Đang xóa...' : 'Xóa vĩnh viễn'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header Quick Rename Modal */}
      {isHeaderRenameOpen && (
        <div className="modal-backdrop" onClick={() => setIsHeaderRenameOpen(false)}>
          <div className="modal-dialog modal-sm" onClick={(e) => e.stopPropagation()}>
            <form onSubmit={handleSaveHeaderRename}>
              <div className="modal-header">
                <div className="modal-title-wrap">
                  <div className="modal-icon-badge">
                    <Icon name="edit" size={18} />
                  </div>
                  <h3>Đổi tên đoạn chat</h3>
                </div>
                <button
                  type="button"
                  className="modal-close-btn"
                  onClick={() => setIsHeaderRenameOpen(false)}
                >
                  <Icon name="x" size={18} />
                </button>
              </div>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Tên mới cho đoạn chat</label>
                  <input
                    type="text"
                    className="form-input"
                    value={headerRenameTitle}
                    onChange={(e) => setHeaderRenameTitle(e.target.value)}
                    placeholder="Ví dụ: Hỏi đáp học phí, Kết nối wifi..."
                    autoFocus
                    required
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => setIsHeaderRenameOpen(false)}
                >
                  Hủy
                </button>
                <button type="submit" className="btn btn-primary">
                  Lưu thay đổi
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
