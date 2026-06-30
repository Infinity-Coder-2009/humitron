import { useEffect, useState } from 'react';
import { useSessions } from './context/SessionContext';
import { useConfig } from './context/ConfigContext';
import { useBackend } from './hooks/useBackend';
import { useChat } from './hooks/useChat';
import { useProviders } from './hooks/useProviders';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { ChatWindow } from './components/Chat';
import { ChatInput } from './components/Chat';
import { CostMeter } from './components/CostMeter';
import { SettingsPanel } from './components/Settings';
import { WelcomeScreen } from './components/Welcome';
import { ProvidersPage } from './components/Providers';
import { invoke } from '@tauri-apps/api/core';
import { Routes, Route, Navigate } from 'react-router-dom';

function App() {
  const { sessions, currentSession, createSession } = useSessions();
  const { config } = useConfig();
  const { health } = useBackend();
  const { getActiveProvider } = useProviders();
  const [showSettings, setShowSettings] = useState(false);
  const [showWelcome, setShowWelcome] = useState(false);
  const [backendStarted, setBackendStarted] = useState(false);

  const { streaming, currentMessageId, cost, sendMessage, stopStreaming } = useChat({
    sessionId: currentSession?.id || '',
    config: {
      model: config.model,
      temperature: config.temperature,
      maxSteps: config.maxSteps,
      workspace: config.workspace,
    },
    onMessageAdd: () => {},
    onMessageUpdate: () => {},
    onToolCallUpdate: () => {},
  });

  useEffect(() => {
    if (sessions.length === 0) {
      createSession('Welcome');
    }
  }, [sessions.length, createSession]);

  useEffect(() => {
    const firstRun = !localStorage.getItem('humitron-first-run-complete');
    if (firstRun) {
      setShowWelcome(true);
    }
  }, []);

  useEffect(() => {
    if (!backendStarted) {
      invoke('start_sidecar', { workspace: config.workspace })
        .then(() => setBackendStarted(true))
        .catch(console.error);
    }
  }, [backendStarted, config.workspace]);

  const handleSendMessage = (text: string) => {
    if (currentSession) {
      sendMessage(text);
    }
  };

  const completeWelcome = () => {
    localStorage.setItem('humitron-first-run-complete', 'true');
    setShowWelcome(false);
  };

  const activeProvider = getActiveProvider();

  if (showWelcome) {
    return <WelcomeScreen onComplete={completeWelcome} />;
  }

  return (
    <div className="flex h-screen bg-dark-bg">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <div className="flex-1 flex flex-col relative">
          <Routes>
            <Route path="/settings" element={<ProvidersPage />} />
            <Route path="/" element={
              <>
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
              </>
            } />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </div>
      <SettingsPanel isOpen={showSettings} onClose={() => setShowSettings(false)} />
    </div>
  );
}

export default App;