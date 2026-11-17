import React, { useState, useEffect } from 'react'
import { Modal } from '../common/Modal'
import { StatusBadge, PriorityBadge, RoleBadge } from '../common/Badge'
import { Icon } from '../common/Icons'
import { ticketsApi } from '../../api/tickets'
import { departmentsApi } from '../../api/departments'
import { useAuth } from '../../context/AuthContext'
import { EditTicketModal } from './EditTicketModal'

export function TicketDetailModal({ ticket, isOpen, onClose, onTicketUpdated, onTicketDeleted }) {
  const { user, addToast } = useAuth()
  const [currentTicket, setCurrentTicket] = useState(ticket)
  const [members, setMembers] = useState([])
  const [selectedMemberId, setSelectedMemberId] = useState('')
  const [actionNote, setActionNote] = useState('')
  const [newStatus, setNewStatus] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)

  // Comments state
  const [commentContent, setCommentContent] = useState('')
  const [isInternalComment, setIsInternalComment] = useState(false)
  const [isSubmittingComment, setIsSubmittingComment] = useState(false)

  useEffect(() => {
    if (isOpen && ticket?.id) {
      setCurrentTicket(ticket)
      setNewStatus(ticket.status || '')
      setSelectedMemberId('')
      setActionNote('')
      setCommentContent('')
      setIsInternalComment(false)

      // Fetch fresh details with full comments and updated status
      ticketsApi
        .getTicket(ticket.id)
        .then((fresh) => {
          setCurrentTicket(fresh)
          setNewStatus(fresh.status || '')
        })
        .catch((err) => {
          console.error('Error fetching ticket detail:', err)
        })

      // If user is ADMIN or DEPT_MANAGER and ticket has department, fetch department members
      if (
        user &&
        (user.role === 'ADMIN' || user.role === 'DEPT_MANAGER') &&
        ticket.department_id
      ) {
        departmentsApi
          .getDepartmentMembers(ticket.department_id)
          .then((data) => {
            setMembers(data || [])
          })
          .catch((err) => {
            console.error('Error fetching department members:', err)
          })
      }
    }
  }, [isOpen, ticket, user])

  if (!ticket || !currentTicket) return null

  const clf = currentTicket.classification
  const histories = currentTicket.histories || []
  const comments = currentTicket.comments || []

  const isStaffOrTech =
    user && ['ADMIN', 'DEPT_MANAGER', 'TECHNICIAN', 'STAFF'].includes(user.role)

  const isRequester =
    user && user.id && String(user.id) === String(currentTicket.requester_id)

  const canEditTicket = user && (user.role === 'ADMIN' || isRequester)
  const canDeleteTicket = user && (user.role === 'ADMIN' || isRequester)

  const canCancelTicket =
    user &&
    (user.role === 'ADMIN' ||
      isRequester ||
      ['DEPT_MANAGER', 'TECHNICIAN'].includes(user.role)) &&
    currentTicket.status !== 'CANCELLED' &&
    currentTicket.status !== 'RESOLVED'

  const canAccept =
    user &&
    ['ADMIN', 'DEPT_MANAGER', 'TECHNICIAN'].includes(user.role) &&
    (!currentTicket.department_id ||
      user.role === 'ADMIN' ||
      user.department_id === currentTicket.department_id)

  const canAssign =
    user &&
    (user.role === 'ADMIN' ||
      (user.role === 'DEPT_MANAGER' &&
        user.department_id === currentTicket.department_id))

  const canUpdateStatus =
    user &&
    (user.role === 'ADMIN' ||
      (user.role === 'DEPT_MANAGER' &&
        user.department_id === currentTicket.department_id) ||
      (user.role === 'TECHNICIAN' &&
        (currentTicket.assignee_id === user.id ||
          !currentTicket.department_id ||
          user.department_id === currentTicket.department_id)))

  // Quick Accept Ticket
  const handleAccept = async () => {
    setIsSubmitting(true)
    try {
      const updated = await ticketsApi.acceptTicket(
        currentTicket.id,
        actionNote.trim() || null
      )
      setCurrentTicket(updated)
      if (onTicketUpdated) onTicketUpdated(updated)
      setActionNote('')
      addToast(
        `Đã tiếp nhận xử lý phiếu #${currentTicket.id.substring(0, 8)} thành công!`,
        'success'
      )
    } catch (err) {
      addToast(err.message || 'Không thể tiếp nhận phiếu', 'error')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Manager/Admin Assign Ticket
  const handleAssign = async () => {
    if (!selectedMemberId) {
      addToast('Vui lòng chọn kỹ thuật viên để phân công', 'warning')
      return
    }
    setIsSubmitting(true)
    try {
      const updated = await ticketsApi.assignTicket(
        currentTicket.id,
        selectedMemberId,
        actionNote.trim() || null
      )
      setCurrentTicket(updated)
      if (onTicketUpdated) onTicketUpdated(updated)
      setActionNote('')
      addToast(
        `Đã phân công phiếu cho kỹ thuật viên thành công!`,
        'success'
      )
    } catch (err) {
      addToast(err.message || 'Không thể phân công', 'error')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Update Status
  const handleStatusUpdate = async () => {
    if (!newStatus || newStatus === currentTicket.status) {
      addToast('Vui lòng chọn trạng thái mới khác trạng thái hiện tại', 'warning')
      return
    }
    setIsSubmitting(true)
    try {
      const updated = await ticketsApi.updateTicketStatus(
        currentTicket.id,
        newStatus,
        actionNote.trim() || null
      )
      setCurrentTicket(updated)
      if (onTicketUpdated) onTicketUpdated(updated)
      setActionNote('')
      addToast('Cập nhật trạng thái phiếu thành công!', 'success')
    } catch (err) {
      addToast(err.message || 'Không thể cập nhật trạng thái', 'error')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Cancel Ticket
  const handleCancelTicket = async () => {
    const reason = window.prompt('Nhập lý do hủy phiếu hỗ trợ (tùy chọn):', '')
    if (reason === null) return

    setIsSubmitting(true)
    try {
      const updated = await ticketsApi.updateTicketStatus(
        currentTicket.id,
        'CANCELLED',
        reason.trim() || 'Người dùng đã hủy phiếu hỗ trợ'
      )
      setCurrentTicket(updated)
      if (onTicketUpdated) onTicketUpdated(updated)
      addToast('Đã hủy phiếu hỗ trợ thành công!', 'success')
    } catch (err) {
      addToast(err.message || 'Không thể hủy phiếu', 'error')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Delete Ticket
  const handleDeleteTicket = async () => {
    if (
      !window.confirm(
        `Bạn có chắc chắn muốn xóa vĩnh viễn phiếu #${currentTicket.id.substring(0, 8)} không? Thao tác này không thể hoàn tác.`
      )
    ) {
      return
    }

    setIsSubmitting(true)
    try {
      await ticketsApi.deleteTicket(currentTicket.id)
      addToast('Đã xóa phiếu hỗ trợ thành công!', 'success')
      if (onTicketDeleted) onTicketDeleted(currentTicket.id)
      onClose()
    } catch (err) {
      addToast(err.message || 'Không thể xóa phiếu', 'error')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Handle Ticket Edited
  const handleTicketEdited = (updated) => {
    setCurrentTicket(updated)
    if (onTicketUpdated) onTicketUpdated(updated)
  }

  // Add Comment / Guidance
  const handleAddComment = async (e) => {
    e.preventDefault()
    if (!commentContent.trim()) return

    setIsSubmittingComment(true)
    try {
      const newComment = await ticketsApi.addComment(currentTicket.id, {
        content: commentContent.trim(),
        is_internal: isInternalComment,
      })
      const updatedTicket = {
        ...currentTicket,
        comments: [...comments, newComment],
      }
      setCurrentTicket(updatedTicket)
      if (onTicketUpdated) onTicketUpdated(updatedTicket)
      setCommentContent('')
      setIsInternalComment(false)
      addToast(
        isInternalComment
          ? 'Đã lưu ghi chú nội bộ phòng ban'
          : 'Đã gửi phản hồi / hướng dẫn giải quyết!',
        'success'
      )
    } catch (err) {
      addToast(err.message || 'Không thể gửi phản hồi', 'error')
    } finally {
      setIsSubmittingComment(false)
    }
  }

  return (
    <>
      <Modal
        isOpen={isOpen}
        onClose={onClose}
        title={`Chi tiết Phiếu hỗ trợ #${currentTicket.id.substring(0, 8)}`}
        maxWidth="840px"
      >
        <div className="ticket-detail-view">
          {/* Ticket Header Card */}
          <div className="ticket-summary-card">
            <div className="ticket-summary-top">
              <h2 className="ticket-main-title">{currentTicket.title}</h2>
              <div className="ticket-badges">
                <StatusBadge status={currentTicket.status} />
                <PriorityBadge priority={currentTicket.priority} />
              </div>
            </div>

            <p className="ticket-main-desc">{currentTicket.description}</p>

            <div className="ticket-meta-grid">
              <div className="meta-item">
                <span className="meta-lbl">Người gửi yêu cầu:</span>
                <span className="meta-val font-medium">
                  {currentTicket.requester_name || 'Người dùng'}
                </span>
              </div>
              <div className="meta-item">
                <span className="meta-lbl">Kỹ thuật viên phụ trách:</span>
                <span className="meta-val font-semibold text-primary">
                  {currentTicket.assignee_name ? (
                    <span>👤 {currentTicket.assignee_name}</span>
                  ) : (
                    <span className="badge badge-amber">Chưa tiếp nhận</span>
                  )}
                </span>
              </div>
              <div className="meta-item">
                <span className="meta-lbl">Phòng ban xử lý:</span>
                <span className="meta-val font-medium">
                  🏢 {currentTicket.department_name || 'Đang chờ phân loại'}
                </span>
              </div>
              <div className="meta-item">
                <span className="meta-lbl">Danh mục dịch vụ:</span>
                <span className="meta-val">
                  {currentTicket.category_name || 'Chưa phân loại'}
                </span>
              </div>
              <div className="meta-item">
                <span className="meta-lbl">Kênh tiếp nhận:</span>
                <span className="meta-val">
                  {currentTicket.channel === 'CHATBOT' ? '🤖 Chatbot AI' : '🌐 Web Form'}
                </span>
              </div>
              <div className="meta-item">
                <span className="meta-lbl">Thời gian gửi:</span>
                <span className="meta-val">
                  {new Date(currentTicket.created_at).toLocaleString('vi-VN')}
                </span>
              </div>
              {currentTicket.resolved_at && (
                <div className="meta-item">
                  <span className="meta-lbl">Thời gian giải quyết:</span>
                  <span className="meta-val text-green font-medium">
                    {new Date(currentTicket.resolved_at).toLocaleString('vi-VN')}
                  </span>
                </div>
              )}
            </div>

            {/* Quick Actions (Edit, Cancel, Delete) */}
            {(canEditTicket || canCancelTicket || canDeleteTicket) && (
              <div
                style={{
                  display: 'flex',
                  gap: '8px',
                  flexWrap: 'wrap',
                  marginTop: '16px',
                  paddingTop: '12px',
                  borderTop: '1px solid #e2e8f0',
                  alignItems: 'center',
                }}
              >
                {canEditTicket && (
                  <button
                    type="button"
                    className="btn btn-sm btn-outline"
                    onClick={() => setIsEditModalOpen(true)}
                    title="Chỉnh sửa thông tin phiếu hỗ trợ"
                  >
                    <Icon name="edit" size={14} />
                    <span>Sửa phiếu</span>
                  </button>
                )}
                {canCancelTicket && (
                  <button
                    type="button"
                    className="btn btn-sm btn-outline"
                    style={{ color: '#dc2626', borderColor: '#fca5a5' }}
                    onClick={handleCancelTicket}
                    disabled={isSubmitting}
                    title="Hủy phiếu hỗ trợ này"
                  >
                    <Icon name="x" size={14} />
                    <span>Hủy phiếu</span>
                  </button>
                )}
                {canDeleteTicket && (
                  <button
                    type="button"
                    className="btn btn-sm btn-outline"
                    style={{ color: '#dc2626', borderColor: '#fca5a5' }}
                    onClick={handleDeleteTicket}
                    disabled={isSubmitting}
                    title="Xóa vĩnh viễn phiếu này"
                  >
                    <Icon name="trash" size={14} />
                    <span>Xóa phiếu</span>
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Department Acceptance & Handling Action Box (for staff/tech/manager/admin) */}
          {isStaffOrTech && (
            <div className="dept-workflow-box">
              <div className="dept-workflow-header">
                <div className="dept-workflow-title">
                  <Icon name="shield" size={18} />
                  <span>Bảng điều khiển Tiếp nhận & Xử lý (Phòng ban)</span>
                </div>
                {currentTicket.assignee_name ? (
                  <span className="badge badge-indigo">
                    Đã tiếp nhận: {currentTicket.assignee_name}
                  </span>
                ) : (
                  <span className="badge badge-amber">
                    ⚠️ Chưa có kỹ thuật viên tiếp nhận
                  </span>
                )}
              </div>

              <div className="dept-workflow-body">
                {/* 1. Quick Accept Button if ticket is not yet assigned */}
                {!currentTicket.assignee_id && canAccept && (
                  <div className="dept-action-block highlight-accept">
                    <div className="dept-action-desc">
                      <strong>Tiếp nhận yêu cầu từ sinh viên:</strong> Tiếp nhận phiếu này để chuyển trạng thái sang <em>Đang xử lý</em> và tự động gán vào danh sách công việc của bạn.
                    </div>
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={handleAccept}
                      disabled={isSubmitting}
                    >
                      <Icon name="check" size={16} />
                      <span>{isSubmitting ? 'Đang tiếp nhận...' : '✋ Tiếp nhận xử lý phiếu này'}</span>
                    </button>
                  </div>
                )}

                {/* 2. Manager/Admin Assign to Technician */}
                {canAssign && (
                  <div className="dept-action-block">
                    <label className="dept-action-label">
                      <Icon name="users" size={14} />
                      <span>Phân công kỹ thuật viên phụ trách:</span>
                    </label>
                    <div className="dept-action-inline">
                      <select
                        className="dept-select"
                        value={selectedMemberId}
                        onChange={(e) => setSelectedMemberId(e.target.value)}
                      >
                        <option value="">-- Chọn kỹ thuật viên phòng ban --</option>
                        {members.map((m) => (
                          <option key={m.id} value={m.id}>
                            {m.full_name} ({m.email}) - {m.role}
                          </option>
                        ))}
                      </select>
                      <button
                        type="button"
                        className="btn btn-outline"
                        onClick={handleAssign}
                        disabled={isSubmitting || !selectedMemberId}
                      >
                        <Icon name="check" size={14} />
                        <span>Phân công</span>
                      </button>
                    </div>
                  </div>
                )}

                {/* 3. Update Status */}
                {canUpdateStatus && (
                  <div className="dept-action-block">
                    <label className="dept-action-label">
                      <Icon name="refresh" size={14} />
                      <span>Cập nhật tiến trình & Trạng thái phiếu:</span>
                    </label>
                    <div className="dept-action-inline">
                      <select
                        className="dept-select"
                        value={newStatus}
                        onChange={(e) => setNewStatus(e.target.value)}
                      >
                        <option value="IN_PROGRESS">Đang xử lý (IN_PROGRESS)</option>
                        <option value="PENDING_USER">Chờ sinh viên phản hồi (PENDING_USER)</option>
                        <option value="RESOLVED">Đã giải quyết xong (RESOLVED)</option>
                        <option value="CANCELLED">Hủy phiếu (CANCELLED)</option>
                      </select>
                      <button
                        type="button"
                        className="btn btn-primary"
                        onClick={handleStatusUpdate}
                        disabled={isSubmitting || newStatus === currentTicket.status}
                      >
                        <Icon name="check" size={14} />
                        <span>Lưu trạng thái</span>
                      </button>
                    </div>
                  </div>
                )}

                {/* Optional note input for acceptance, assignment or status change */}
                {(canAccept || canAssign || canUpdateStatus) && (
                  <div className="dept-action-block">
                    <input
                      type="text"
                      className="dept-note-input"
                      placeholder="Ghi chú kèm theo tiến trình (tùy chọn)..."
                      value={actionNote}
                      onChange={(e) => setActionNote(e.target.value)}
                    />
                  </div>
                )}
              </div>
            </div>
          )}

          {/* AI Classification Details */}
          {clf && (
            <div className="ai-classification-card">
              <div className="ai-clf-header">
                <div className="ai-clf-title">
                  <Icon name="sparkles" size={18} />
                  <span>Kết quả Phân loại & Định tuyến AI (Gemini NLP)</span>
                </div>
                <span className="ai-score-pill">
                  Độ tin cậy: {(clf.confidence_score * 100).toFixed(1)}%
                </span>
              </div>

              <div className="ai-clf-body">
                <div className="ai-clf-item">
                  <span className="clf-lbl">Danh mục dự đoán:</span>
                  <span className="clf-val font-semibold">
                    {clf.predicted_category_name || 'Chưa xác định'}
                  </span>
                </div>
                <div className="ai-clf-item">
                  <span className="clf-lbl">Ưu tiên đề xuất:</span>
                  <span className="clf-val">
                    {clf.suggested_priority ? (
                      <PriorityBadge priority={clf.suggested_priority} />
                    ) : (
                      'Không đổi'
                    )}
                  </span>
                </div>
                <div className="ai-clf-item">
                  <span className="clf-lbl">Mô hình phân loại:</span>
                  <span className="clf-val text-muted text-xs">{clf.model_version}</span>
                </div>
              </div>
            </div>
          )}

          {/* Comments & Guidance Section */}
          <div className="ticket-comments-section">
            <h4 className="section-subtitle">
              <Icon name="message" size={16} />
              <span>Trao đổi & Hướng dẫn xử lý ({comments.length})</span>
            </h4>

            <div className="comments-thread">
              {comments.length === 0 ? (
                <div className="comments-empty-notice">
                  <p>Chưa có trao đổi nào trên phiếu hỗ trợ này.</p>
                  <span className="text-xs text-muted">
                    Cán bộ/Kỹ thuật viên hoặc người yêu cầu có thể gửi trao đổi, hướng dẫn chi tiết bên dưới.
                  </span>
                </div>
              ) : (
                <div className="comments-list">
                  {comments.map((c) => (
                    <div
                      key={c.id}
                      className={`comment-item ${
                        c.is_internal ? 'comment-item-internal' : ''
                      }`}
                    >
                      <div className="comment-header">
                        <div className="comment-author-badge">
                          <span className="comment-author-name">
                            {c.author_name || 'Người dùng'}
                          </span>
                          {c.author_role && <RoleBadge role={c.author_role} />}
                          {c.is_internal && (
                            <span className="badge badge-amber comment-internal-badge">
                              🔒 Ghi chú nội bộ phòng ban
                            </span>
                          )}
                        </div>
                        <span className="comment-timestamp">
                          {new Date(c.created_at).toLocaleString('vi-VN')}
                        </span>
                      </div>
                      <div className="comment-body">{c.content}</div>
                    </div>
                  ))}
                </div>
              )}

              {/* Comment Form */}
              <form onSubmit={handleAddComment} className="comment-form-card">
                <textarea
                  className="comment-textarea"
                  rows={3}
                  placeholder={
                    isStaffOrTech
                      ? 'Nhập nội dung phản hồi, hướng dẫn xử lý hoặc ghi chú tiến trình...'
                      : 'Nhập câu hỏi hoặc phản hồi bổ sung cho bộ phận hỗ trợ...'
                  }
                  value={commentContent}
                  onChange={(e) => setCommentContent(e.target.value)}
                  required
                />
                <div className="comment-form-footer">
                  {isStaffOrTech ? (
                    <label className="internal-checkbox-label">
                      <input
                        type="checkbox"
                        checked={isInternalComment}
                        onChange={(e) => setIsInternalComment(e.target.checked)}
                      />
                      <span>
                        🔒 Ghi chú nội bộ (Chỉ cán bộ/kỹ thuật viên thấy, ẩn với sinh viên)
                      </span>
                    </label>
                  ) : (
                    <div></div>
                  )}
                  <button
                    type="submit"
                    className="btn btn-primary btn-sm"
                    disabled={isSubmittingComment || !commentContent.trim()}
                  >
                    <Icon name="send" size={14} />
                    <span>{isSubmittingComment ? 'Đang gửi...' : 'Gửi phản hồi / hướng dẫn'}</span>
                  </button>
                </div>
              </form>
            </div>
          </div>

          {/* Ticket Timeline History */}
          <div className="ticket-history-section">
            <h4 className="section-subtitle">
              <Icon name="clock" size={16} />
              <span>Lịch sử tiến trình xử lý</span>
            </h4>

            {histories.length === 0 ? (
              <p className="text-muted text-sm">Chưa có lịch sử trạng thái ghi nhận.</p>
            ) : (
              <div className="timeline-list">
                {histories.map((h) => (
                  <div key={h.id} className="timeline-item">
                    <div className="timeline-point"></div>
                    <div className="timeline-content">
                      <div className="timeline-header">
                        <div className="timeline-status-transition">
                          {h.old_status && (
                            <>
                              <StatusBadge status={h.old_status} />
                              <Icon name="chevronRight" size={14} className="timeline-arrow" />
                            </>
                          )}
                          <StatusBadge status={h.new_status} />
                        </div>
                        <span className="timeline-time">
                          {new Date(h.changed_at).toLocaleString('vi-VN')}
                        </span>
                      </div>
                      {h.note && <div className="timeline-note">{h.note}</div>}
                      <div className="timeline-author">
                        Thực hiện bởi: <span className="font-medium">{h.changed_by_name || 'Hệ thống'}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Đóng
            </button>
          </div>
        </div>
      </Modal>

      {/* Edit Ticket Modal */}
      <EditTicketModal
        ticket={currentTicket}
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        onUpdated={handleTicketEdited}
      />
    </>
  )
}
