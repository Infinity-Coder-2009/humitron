import { useState, useCallback, useRef } from 'react'
import { apiClient } from '../api/client'
import { Message, ToolCall, CostInfo } from '../types'
import { generateId } from '../utils/helpers'

interface UseChatOptions {
  sessionId: string;
  config: { model: string; temperature: number; maxSteps: number; workspace: string };
  onMessageAdd: (message: Omit<Message, 'id' | 'timestamp'>) => void;
  onMessageUpdate: (messageId: string, updates: Partial<Message>) => void;
  onToolCallUpdate: (messageId: string, toolCallId: string, updates: Partial<ToolCall>) => void;
}

export function useChat({
  sessionId,
  config,
  onMessageAdd,
  onMessageUpdate,
  onToolCallUpdate,
}: UseChatOptions) {
  const [streaming, setStreaming] = useState(false)
  const [currentMessageId, setCurrentMessageId] = useState<string | null>(null)
  const [cost, setCost] = useState<CostInfo>({
    totalTokens: 0,
    inputTokens: 0,
    outputTokens: 0,
    estimatedCost: 0,
    model: config.model,
  })
  const abortControllerRef = useRef<AbortController | null>(null)

  const sendMessage = useCallback(async (prompt: string) => {
    if (streaming) return

    setStreaming(true)
    abortControllerRef.current = new AbortController()

    // Add user message
    onMessageAdd({
      role: 'user',
      content: prompt,
    })

    // Create assistant message placeholder
    const assistantMessageId = generateId()
    setCurrentMessageId(assistantMessageId)
    onMessageAdd({
      role: 'assistant',
      content: '',
      toolCalls: [],
    })

    try {
      for await (const chunk of apiClient.streamChat(prompt, sessionId, config)) {
        if (abortControllerRef.current?.signal.aborted) break

        switch (chunk.type) {
          case 'thinking':
            onMessageUpdate(assistantMessageId, { thinking: chunk.data.thinking })
            break
          
          case 'tool_call':
            const toolCall: ToolCall = {
              id: generateId(),
              name: chunk.data.name,
              arguments: chunk.data.arguments,
              status: 'running',
              startTime: new Date(),
            }
            onMessageUpdate(assistantMessageId, { 
              toolCalls: [toolCall] 
            })
            break
          
          case 'tool_result':
            onToolCallUpdate(assistantMessageId, chunk.data.tool_call_id, {
              status: chunk.data.success ? 'completed' : 'failed',
              result: chunk.data.result,
              error: chunk.data.error,
              endTime: new Date(),
            })
            break
          
          case 'content':
            onMessageUpdate(assistantMessageId, { 
              content: chunk.data.content 
            })
            break
          
          case 'done':
            if (chunk.data.cost) {
              setCost(prev => ({
                ...prev,
                totalTokens: prev.totalTokens + chunk.data.cost.total_tokens,
                inputTokens: prev.inputTokens + chunk.data.cost.input_tokens,
                outputTokens: prev.outputTokens + chunk.data.cost.output_tokens,
                estimatedCost: prev.estimatedCost + chunk.data.cost.estimated_cost,
              }))
            }
            setCurrentMessageId(null)
            break
          
          case 'error':
            onMessageUpdate(assistantMessageId, { 
              content: `Error: ${chunk.data.message}` 
            })
            break
        }
      }
    } catch (error) {
      onMessageUpdate(assistantMessageId, { 
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}` 
      })
    } finally {
      setStreaming(false)
      abortControllerRef.current = null
    }
  }, [sessionId, config, streaming, onMessageAdd, onMessageUpdate, onToolCallUpdate])

  const stopStreaming = useCallback(() => {
    abortControllerRef.current?.abort()
    setStreaming(false)
  }, [])

  return { streaming, currentMessageId, cost, sendMessage, stopStreaming }
}