import React from 'react'
import { useAuth } from '../../context/AuthContext'
import { Icon } from './Icons'

export function ToastContainer() {
  const { toasts, removeToast } = useAuth()

  if (!toasts || toasts.length === 0) return null

  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast toast-${toast.type}`}>
          <div className="toast-icon">
            {toast.type === 'success' && <Icon name="check" size={18} />}
            {toast.type === 'error' && <Icon name="alertCircle" size={18} />}
            {toast.type === 'info' && <Icon name="sparkles" size={18} />}
          </div>
          <div className="toast-message">{toast.message}</div>
          <button
            className="toast-close"
            onClick={() => removeToast(toast.id)}
            aria-label="Đóng thông báo"
          >
            <Icon name="x" size={16} />
          </button>
        </div>
      ))}
    </div>
  )
}

