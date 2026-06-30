import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react'
import { Session, Message, ToolCall } from '../types'
import { generateId } from '../utils/helpers'

interface SessionContextType {
  sessions: Session[];
  currentSession: Session | null;
  createSession: (name?: string) => Session;
  deleteSession: (id: string) => void;
  renameSession: (id: string, name: string) => void;
  setCurrentSession: (id: string) => void;
  addMessage: (sessionId: string, message: Omit<Message, 'id' | 'timestamp'>) => void;
  updateMessage: (sessionId: string, messageId: string, updates: Partial<Message>) => void;
  updateToolCall: (sessionId: string, messageId: string, toolCallId: string, updates: Partial<ToolCall>) => void;
}

const SessionContext = createContext<SessionContextType | undefined>(undefined)

const STORAGE_KEY = 'humitron-sessions'

export function SessionProvider({ children }: { children: ReactNode }) {
  const [sessions, setSessions] = useState<Session[]>(() => {
    if (typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem(STORAGE_KEY)
        if (stored) {
          const parsed = JSON.parse(stored)
          return parsed.map((s: any) => ({
            ...s,
            createdAt: new Date(s.createdAt),
            updatedAt: new Date(s.updatedAt),
            messages: s.messages.map((m: any) => ({
              ...m,
              timestamp: new Date(m.timestamp),
              toolCalls: m.toolCalls?.map((tc: any) => ({
                ...tc,
                startTime: new Date(tc.startTime),
                endTime: tc.endTime ? new Date(tc.endTime) : undefined,
              })) || [],
            })),
          }))
        }
      } catch (e) {
        console.error('Failed to load sessions:', e)
      }
    }
    return []
  })
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)

  const currentSession = sessions.find(s => s.id === currentSessionId) || null

  useEffect(() => {
    if (sessions.length > 0 && !currentSessionId) {
      setCurrentSessionId(sessions[0].id)
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
  }, [sessions, currentSessionId])

  const createSession = useCallback((name?: string) => {
    const config = JSON.parse(localStorage.getItem('humitron-config') || '{}')
    const newSession: Session = {
      id: generateId(),
      name: name || `Chat ${sessions.length + 1}`,
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date(),
      model: config.model || 'llama3.2',
      workspace: config.workspace || '.',
    }
    setSessions(prev => [...prev, newSession])
    setCurrentSessionId(newSession.id)
    return newSession
  }, [sessions.length])

  const deleteSession = useCallback((id: string) => {
    setSessions(prev => {
      const filtered = prev.filter(s => s.id !== id)
      if (currentSessionId === id) {
        setCurrentSessionId(filtered[0]?.id || null)
      }
      return filtered
    })
  }, [currentSessionId])

  const renameSession = useCallback((id: string, name: string) => {
    setSessions(prev => prev.map(s => s.id === id ? { ...s, name, updatedAt: new Date() } : s))
  }, [])

  const setCurrentSession = useCallback((id: string) => {
    setCurrentSessionId(id)
  }, [])

  const addMessage = useCallback((sessionId: string, message: Omit<Message, 'id' | 'timestamp'>) => {
    const newMessage: Message = {
      ...message,
      id: generateId(),
      timestamp: new Date(),
    }
    setSessions(prev => prev.map(s => 
      s.id === sessionId 
        ? { ...s, messages: [...s.messages, newMessage], updatedAt: new Date() }
        : s
    ))
  }, [])

  const updateMessage = useCallback((sessionId: string, messageId: string, updates: Partial<Message>) => {
    setSessions(prev => prev.map(s => 
      s.id === sessionId 
        ? { ...s, messages: s.messages.map(m => m.id === messageId ? { ...m, ...updates } : m), updatedAt: new Date() }
        : s
    ))
  }, [])

  const updateToolCall = useCallback((sessionId: string, messageId: string, toolCallId: string, updates: Partial<ToolCall>) => {
    setSessions(prev => prev.map(s => 
      s.id === sessionId 
        ? { 
            ...s, 
            messages: s.messages.map(m => 
              m.id === messageId 
                ? { 
                    ...m, 
                    toolCalls: m.toolCalls?.map(tc => 
                      tc.id === toolCallId ? { ...tc, ...updates } : tc
                    ) || [] 
                  } 
                : m
            ), 
            updatedAt: new Date() 
          }
        : s
    ))
  }, [])

  return (
    <SessionContext.Provider value={{
      sessions,
      currentSession,
      createSession,
      deleteSession,
      renameSession,
      setCurrentSession,
      addMessage,
      updateMessage,
      updateToolCall,
    }}>
      {children}
    </SessionContext.Provider>
  )
}

export function useSessions() {
  const context = useContext(SessionContext)
  if (!context) {
    throw new Error('useSessions must be used within a SessionProvider')
  }
  return context
}