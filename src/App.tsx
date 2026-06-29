import React, { useEffect, useState } from 'react'
import { useSessions } from './context/SessionContext'
import { useConfig } from './context/ConfigContext'
import { useBackend } from './hooks/useBackend'
import { useChat } from './hooks/useChat'
import { Sidebar } from './components/Sidebar'
import { Header } from './components/Header'
import { ChatWindow } from './components/Chat'
import { ChatInput } from './components/Chat'
import { CostMeter } from './components/CostMeter'
import { SettingsPanel } from './components/Settings'
import { WelcomeScreen } from './components/Welcome'
import { tauri } from '@tauri-apps/api'
import { cn } from './utils/cn'

function App() {
  const { sessions, currentSession, createSession } = useSessions()
  const { config, updateConfig } = useConfig()
  const { health, loading: healthLoading } = useBackend()
  const [showSettings, setShowSettings] = useState(false)
  const [showWelcome, setShowWelcome] = useState(false)
  const [backendStarted, setBackendStarted] = useState(false)

  const { streaming, currentMessageId, cost, sendMessage, stopStreaming } = useChat({
    sessionId: currentSession?.id || '',
    config: {
      model: config.model,
      temperature: config.temperature,
      maxSteps: config.maxSteps,
      workspace: config.workspace,
    },
    onMessageAdd: (message) => {
      if (currentSession) {
        // Message added via session context
      }
    },
    onMessageUpdate: (messageId, updates) => {
      // Handled by session context
    },
    onToolCallUpdate: (messageId, toolCallId, updates) => {
      // Handled by session context
    },
  })

  // Auto-create first session
  useEffect(() => {
    if (sessions.length === 0) {
      createSession('Welcome')
    }
  }, [sessions.length, createSession])

  // Check if first run
  useEffect(() => {
    const firstRun = !localStorage.getItem('humitron-first-run-complete')
    if (firstRun) {
      setShowWelcome(true)
    }
  }, [])

  // Start backend sidecar
  useEffect(() => {
    if (!backendStarted) {
      tauri.invoke('start_sidecar', { workspace: config.workspace })
        .then(() => setBackendStarted(true))
        .catch(console.error)
    }
  }, [backendStarted, config.workspace])

  const handleSendMessage = (text: string) => {
    if (currentSession) {
      sendMessage(text)
    }
  }

  const completeWelcome = () => {
    localStorage.setItem('humitron-first-run-complete', 'true')
    setShowWelcome(false)
  }

  if (showWelcome) {
    return <WelcomeScreen onComplete={completeWelcome} />
  }

  return (
    <div className="flex h-screen bg-dark-bg">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <div className="flex-1 flex flex-col relative">
          {currentSession && (
            <>
              <ChatWindow
                messages={currentSession.messages}
                streaming={streaming}
                currentMessageId={currentMessageId}
                onScrollToBottom={() => {}}
              />
              <ChatInput
                onSend={handleSendMessage}
                streaming={streaming}
                onStop={stopStreaming}
                disabled={!currentSession || streaming}
              />
            </>
          )}
          {!currentSession && (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center text-gray-500">
                <p className="text-lg mb-2">No active session</p>
                <p className="text-sm">Create a new session from the sidebar to start chatting</p>
              </div>
            </div>
          )}
          
          {cost.totalTokens > 0 && (
            <CostMeter cost={cost} />
          )}
        </div>
      </div>
      <SettingsPanel isOpen={showSettings} onClose={() => setShowSettings(false)} />
    </div>
  )
}

export default App