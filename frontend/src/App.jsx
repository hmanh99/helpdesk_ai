import React, { useState } from 'react'
import { AuthProvider, useAuth } from './context/AuthContext'
import { Navbar } from './components/common/Navbar'
import { Sidebar } from './components/common/Sidebar'
import { ToastContainer } from './components/common/Toast'
import { AuthPage } from './components/auth/AuthPage'
import { ChatView } from './components/chat/ChatView'
import { TicketsView } from './components/tickets/TicketsView'
import { KnowledgeView } from './components/knowledge/KnowledgeView'
import { DepartmentsView } from './components/departments/DepartmentsView'
import { UsersView } from './components/users/UsersView'
import { ProfileView } from './components/profile/ProfileView'
import { Icon } from './components/common/Icons'
import './index.css'
import './App.css'

function MainContent() {
  const { user, loading } = useAuth()
  const [activeTab, setActiveTab] = useState('chat')
  const [targetTicketId, setTargetTicketId] = useState(null)

  if (loading) {
    return (
      <div className="app-loader">
        <div className="loader-box">
          <div className="loader-icon-wrap">
            <Icon name="bot" size={36} />
          </div>
          <h2>Helpdesk AI</h2>
          <div className="loading-state">
            <span className="spinner"></span>
            <p>Đang chuẩn bị hệ thống...</p>
          </div>
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <>
        <AuthPage />
        <ToastContainer />
      </>
    )
  }

  const handleNavigateToTicket = (ticketId) => {
    setTargetTicketId(ticketId)
    setActiveTab('tickets')
  }

  return (
    <div className="app-layout">
      <Navbar activeTab={activeTab} onSelectTab={setActiveTab} />
      <div className="app-body">
        <Sidebar activeTab={activeTab} onSelectTab={setActiveTab} />
        <main className="main-content">
          {activeTab === 'chat' && (
            <ChatView onNavigateToTicket={handleNavigateToTicket} />
          )}
          {activeTab === 'tickets' && (
            <TicketsView
              key={targetTicketId || 'tickets-default'}
              initialTicketId={targetTicketId}
            />
          )}
          {activeTab === 'knowledge' && <KnowledgeView />}
          {activeTab === 'departments' && <DepartmentsView />}
          {activeTab === 'users' && <UsersView />}
          {activeTab === 'profile' && <ProfileView />}
        </main>
      </div>
      <ToastContainer />
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <MainContent />
    </AuthProvider>
  )
}
