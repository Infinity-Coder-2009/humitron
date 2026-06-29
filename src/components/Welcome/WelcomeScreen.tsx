import React, { useState } from 'react'
import { useConfig } from '../../context/ConfigContext'
import { useBackend } from '../../hooks/useBackend'
import { cn } from '../../utils/cn'
import { ArrowRight, Check, AlertCircle, Loader2, Terminal, Box, Brain, Sparkles } from 'lucide-react'
import { tauri } from '@tauri-apps/api'

const steps = [
  {
    id: 'ollama',
    title: 'Install Ollama',
    description: 'Ollama runs AI models locally on your machine. It\'s free, private, and fast.',
    icon: Terminal,
    check: async () => {
      try {
        const resp = await fetch('http://localhost:11434/api/tags')
        return resp.ok
      } catch {
        return false
      }
    },
    action: async () => {
      const url = navigator.platform.includes('Win') 
        ? 'https://ollama.ai/download/windows'
        : navigator.platform.includes('Mac') 
          ? 'https://ollama.ai/download/mac'
          : 'https://ollama.ai/download/linux'
      window.open(url, '_blank')
    },
  },
  {
    id: 'model',
    title: 'Pull a Model',
    description: 'Download a model to run locally. Llama 3.2 is a great all-rounder.',
    icon: Brain,
    check: async () => {
      try {
        const resp = await fetch('http://localhost:11434/api/tags')
        const data = await resp.json()
        return data.models?.some((m: any) => m.name.includes('llama3.2')) || false
      } catch {
        return false
      }
    },
    action: async () => {
      await fetch('http://localhost:11434/api/pull', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'llama3.2', stream: false }),
      })
    },
  },
  {
    id: 'workspace',
    title: 'Choose Workspace',
    description: 'Select a folder where Humitron can read and write files.',
    icon: Box,
    check: async () => true,
    action: async () => {
      try {
        const path = await tauri.invoke('pick_folder')
        if (path) {
          const { updateConfig } = await import('../../context/ConfigContext')
          updateConfig({ workspace: path })
        }
      } catch (e) {
        console.error('Failed to pick folder:', e)
      }
    },
  },
  {
    id: 'backend',
    title: 'Start Backend',
    description: 'The Python backend handles the agent logic and tool execution.',
    icon: Sparkles,
    check: async () => {
      try {
        const resp = await fetch('http://localhost:8000/health')
        return resp.ok
      } catch {
        return false
      }
    },
    action: async () => {
      // Backend starts automatically with Tauri sidecar
    },
  },
]

export function WelcomeScreen({ onComplete }: { onComplete: () => void }) {
  const { health } = useBackend()
  const [currentStep, setCurrentStep] = useState(0)
  const [stepStates, setStepStates] = useState<Record<string, 'pending' | 'checking' | 'complete' | 'error'>>({})
  const [completed, setCompleted] = useState(false)

  React.useEffect(() => {
    const checkAllSteps = async () => {
      for (let i = 0; i < steps.length; i++) {
        const step = steps[i]
        setStepStates(prev => ({ ...prev, [step.id]: 'checking' }))
        try {
          const result = await step.check()
          setStepStates(prev => ({ ...prev, [step.id]: result ? 'complete' : 'pending' }))
        } catch {
          setStepStates(prev => ({ ...prev, [step.id]: 'error' }))
        }
      }
      
      const allComplete = steps.every(s => stepStates[s.id] === 'complete')
      if (allComplete) setCompleted(true)
    }
    checkAllSteps()
  }, [])

  const handleStepAction = async (step: typeof steps[0]) => {
    setStepStates(prev => ({ ...prev, [step.id]: 'checking' }))
    try {
      await step.action()
      const result = await step.check()
      setStepStates(prev => ({ ...prev, [step.id]: result ? 'complete' : 'pending' }))
    } catch {
      setStepStates(prev => ({ ...prev, [step.id]: 'error' }))
    }
  }

  if (completed) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-dark-bg">
        <div className="card w-full max-w-md animate-slide-up text-center">
          <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-4">
            <Check className="w-8 h-8 text-green-500" />
          </div>
          <h2 className="text-2xl font-bold mb-2">You're all set!</h2>
          <p className="text-gray-400 mb-6">Humitron is ready to use. Start chatting with your local AI agent.</p>
          <button onClick={onComplete} className="btn-primary w-full">
            Launch Humitron
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    )
  }

  const step = steps[currentStep]
  const state = stepStates[step.id] || 'pending'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-dark-bg">
      <div className="card w-full max-w-2xl animate-slide-up">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-bold">Welcome to Humitron</h2>
            <p className="text-gray-400 text-sm">Let's get you set up in a few steps</p>
          </div>
          <div className="flex gap-1">
            {steps.map((s, i) => (
              <div key={s.id} className={cn(
                'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors',
                i < currentStep ? 'bg-primary-500 text-white' :
                i === currentStep ? 'bg-primary-500/30 text-primary-400 border border-primary-500' :
                'bg-dark-elevated text-gray-500'
              )}>
                {stepStates[s.id] === 'complete' ? <Check className="w-4 h-4" /> : i + 1}
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-start gap-4 p-4 bg-dark-elevated rounded-lg">
            <div className={cn('w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0',
              state === 'complete' ? 'bg-green-500/20 text-green-500' :
              state === 'checking' ? 'bg-primary-500/20 text-primary-500' :
              state === 'error' ? 'bg-red-500/20 text-red-500' :
              'bg-dark-border text-gray-500'
            )}>
              {state === 'checking' ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : state === 'complete' ? (
                <Check className="w-5 h-5" />
              ) : state === 'error' ? (
                <AlertCircle className="w-5 h-5" />
              ) : (
                <step.icon className="w-5 h-5" />
              )}
            </div>
            <div className="flex-1">
              <h3 className="font-semibold">{step.title}</h3>
              <p className="text-gray-400 text-sm mt-1">{step.description}</p>
              {state === 'pending' && (
                <button
                  onClick={() => handleStepAction(step)}
                  className="btn-primary mt-3 text-sm"
                  disabled={state === 'checking'}
                >
                  {state === 'checking' ? 'Checking...' : 'Set Up'}
                </button>
              )}
              {state === 'error' && (
                <button
                  onClick={() => handleStepAction(step)}
                  className="btn-secondary mt-3 text-sm"
                >
                  Retry
                </button>
              )}
              {state === 'complete' && (
                <span className="inline-flex items-center gap-1 text-green-500 text-sm mt-3">
                  <Check className="w-4 h-4" />
                  Ready!
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex justify-between mt-6 pt-4 border-t border-dark-border">
          <button 
            onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
            disabled={currentStep === 0}
            className="btn-secondary"
          >
            Back
          </button>
          <button
            onClick={() => setCurrentStep(Math.min(steps.length - 1, currentStep + 1))}
            disabled={currentStep === steps.length - 1 || state !== 'complete'}
            className="btn-primary"
          >
            Next
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}