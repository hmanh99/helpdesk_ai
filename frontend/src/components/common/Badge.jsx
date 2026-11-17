import React from 'react'

export function StatusBadge({ status }) {
  const statusConfig = {
    NEW: { label: 'Mới tạo', color: 'badge-blue' },
    TRIAGED: { label: 'Đã phân loại', color: 'badge-indigo' },
    ASSIGNED: { label: 'Đã phân công', color: 'badge-purple' },
    IN_PROGRESS: { label: 'Đang xử lý', color: 'badge-amber' },
    PENDING_USER: { label: 'Chờ phản hồi', color: 'badge-orange' },
    RESOLVED: { label: 'Đã giải quyết', color: 'badge-green' },
    CLOSED: { label: 'Đã đóng', color: 'badge-gray' },
    CANCELLED: { label: 'Đã hủy', color: 'badge-red' },
  }

  const config = statusConfig[status] || { label: status, color: 'badge-gray' }
  return <span className={`badge ${config.color}`}>{config.label}</span>
}

export function PriorityBadge({ priority }) {
  const priorityConfig = {
    LOW: { label: 'Thấp', color: 'badge-gray' },
    MEDIUM: { label: 'Trung bình', color: 'badge-blue' },
    HIGH: { label: 'Cao', color: 'badge-amber' },
    CRITICAL: { label: 'Khẩn cấp', color: 'badge-red' },
  }

  const config = priorityConfig[priority] || { label: priority, color: 'badge-gray' }
  return <span className={`badge ${config.color}`}>{config.label}</span>
}

export function RoleBadge({ role }) {
  const roleConfig = {
    STUDENT: { label: 'Sinh viên', color: 'badge-blue' },
    STAFF: { label: 'Cán bộ / GV', color: 'badge-cyan' },
    TECHNICIAN: { label: 'Kỹ thuật viên', color: 'badge-indigo' },
    DEPT_MANAGER: { label: 'Trưởng bộ phận', color: 'badge-purple' },
    ADMIN: { label: 'Quản trị viên', color: 'badge-emerald' },
  }

  const config = roleConfig[role] || { label: role, color: 'badge-gray' }
  return <span className={`badge ${config.color}`}>{config.label}</span>
}

export function DocStatusBadge({ status }) {
  const statusConfig = {
    PENDING: { label: 'Chờ xử lý', color: 'badge-gray' },
    PROCESSING: { label: 'Đang trích xuất', color: 'badge-amber' },
    READY: { label: 'Sẵn sàng RAG', color: 'badge-green' },
    FAILED: { label: 'Lỗi xử lý', color: 'badge-red' },
  }

  const config = statusConfig[status] || { label: status, color: 'badge-gray' }
  return <span className={`badge ${config.color}`}>{config.label}</span>
}

