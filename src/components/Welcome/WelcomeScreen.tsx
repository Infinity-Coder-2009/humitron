import { useState, useEffect } from 'react'
import { useBackend } from '../../hooks/useBackend'
import { useConfig } from '../../context/ConfigContext'
import { cn } from '../../utils/cn'
import { ArrowRightIcon, CheckIcon, AlertIcon, Loader2, Brain, SkipIcon } from '../Icons/ProviderIcons'
import { invoke } from '@tauri-apps/api/core'

interface WelcomeStep {
  id: string
  title: string
  description: string
  check: () => Promise<boolean>
  action: () => Promise<void>
  skippable: boolean
}

const steps: WelcomeStep[] = [
  {
    id: 'ollama',
    title: 'Ollama Installation',
    description: 'Check if Ollama is installed and running',
    skippable: false,
    check: async () => {
      try {
        const resp = await fetch('http://localhost:11434/api/tags')
        return resp.ok
      } catch {
        return false
      }
    },
    action: async () => {
      await invoke('install_ollama')
    }
  },
  {
    id: 'model',
    title: 'Model Download',
    description: 'Pull a default model (llama3.2)',
    skippable: true,
    check: async () => {
      try {
        const resp = await fetch('http://localhost:11434/api/tags')
        if (resp.ok) {
          const data = await resp.json()
          return data.models?.some((m: any) => m.name.includes('llama3.2')) || false
        }
        return false
      } catch {
        return false
      }
    },
    action: async () => {
      await invoke('pull_model', { name: 'llama3.2' })
    }
  },
  {
    id: 'workspace',
    title: 'Workspace Selection',
    description: 'Choose a workspace directory for file operations',
    skippable: true,
    check: async () => true,
    action: async () => {
      const path = await invoke('pick_folder')
      if (path) {
        const { updateConfig } = await import('../../context/ConfigContext')
        updateConfig({ workspace: path as string })
      }
    }
  }
]

export function WelcomeScreen({ onComplete }: { onComplete: () => void }) {
  const { health } = useBackend()
  const { config, updateConfig } = useConfig()
  const [currentStep, setCurrentStep] = useState(0)
  const [stepStates, setStepStates] = useState<Record<string, 'pending' | 'checking' | 'complete' | 'error' | 'skipped'>>({})
  const [completed, setCompleted] = useState(false)

  useEffect(() => {
    const checkAllSteps = async () => {
      for (let i = 0; i < steps.length; i++) {
        const step = steps[i]
        if (!step.skippable) {
          setStepStates(prev => ({ ...prev, [step.id]: 'checking' }))
          try {
            const result = await step.check()
            setStepStates(prev => ({ ...prev, [step.id]: result ? 'complete' : 'pending' }))
          } catch {
            setStepStates(prev => ({ ...prev, [step.id]: 'error' }))
          }
        } else {
          setStepStates(prev => ({ ...prev, [step.id]: 'pending' }))
        }
      }
      
      const requiredComplete = steps.filter(s => !s.skippable).every(s => stepStates[s.id] === 'complete')
      if (requiredComplete) setCompleted(true)
    }
    checkAllSteps()
  }, [])

  const handleStepAction = async (step: WelcomeStep) => {
    setStepStates(prev => ({ ...prev, [step.id]: 'checking' }))
    try {
      await step.action()
      const result = await step.check()
      setStepStates(prev => ({ ...prev, [step.id]: result ? 'complete' : 'pending' }))
    } catch {
      setStepStates(prev => ({ ...prev, [step.id]: 'error' }))
    }
  }

  const handleSkip = (stepId: string) => {
    setStepStates(prev => ({ ...prev, [stepId]: 'skipped' }))
    setCurrentStep(prev => Math.min(prev + 1, steps.length - 1))
  }

  if (completed) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-dark-bg">
        <div className="card w-full max-w-md animate-slide-up text-center">
          <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-4">
            <CheckIcon className="w-8 h-8 text-green-500" />
          </div>
          <h2 className="text-2xl font-bold mb-2">You're all set!</h2>
          <p className="text-gray-400 mb-6">Humitron is ready to use. Configure your AI providers in Settings to start chatting.</p>
          <button onClick={onComplete} className="btn-primary w-full">
            Launch Humitron
            <ArrowRightIcon className="w-4 h-4" />
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
                {stepStates[s.id] === 'complete' ? <CheckIcon className="w-4 h-4" /> : 
                 stepStates[s.id] === 'skipped' ? <SkipIcon className="w-4 h-4 text-gray-400" /> : i + 1}
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
              state === 'skipped' ? 'bg-gray-600/20 text-gray-400' :
              'bg-dark-border text-gray-500'
            )}>
              {state === 'checking' ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : state === 'complete' ? (
                <CheckIcon className="w-5 h-5" />
              ) : state === 'error' ? (
                <AlertIcon className="w-5 h-5" />
              ) : state === 'skipped' ? (
                <SkipIcon className="w-5 h-5" />
              ) : (
                <Brain className="w-5 h-5" />
              )}
            </div>
            <div className="flex-1">
              <h3 className="font-semibold">{step.title}</h3>
              <p className="text-gray-400 text-sm mt-1">{step.description}</p>
              {state === 'pending' && !step.skippable && (
                <button
                  onClick={() => handleStepAction(step)}
                  className="btn-primary mt-3 text-sm"
                  disabled={state === 'checking'}
                >
                  {state === 'checking' ? 'Checking...' : 'Set Up'}
                </button>
              )}
              {state === 'pending' && step.skippable && (
                <div className="flex gap-2 mt-3">
                  <button
                    onClick={() => handleStepAction(step)}
                    className="btn-primary text-sm"
                    disabled={state === 'checking'}
                  >
                    {state === 'checking' ? 'Checking...' : 'Set Up'}
                  </button>
                  <button
                    onClick={() => handleSkip(step.id)}
                    className="btn-secondary text-sm"
                  >
                    Skip for now
                  </button>
                </div>
              )}
              {state === 'error' && (
                <button
                  onClick={() => handleStepAction(step)}
                  className="btn-secondary mt-3 text-sm"
                >
                  Retry
                </button>
              )}
              {state === 'skipped' && (
                <span className="inline-flex items-center gap-1 text-gray-400 text-sm mt-3">
                  <SkipIcon className="w-4 h-4" />
                  Skipped
                </span>
              )}
              {state === 'complete' && (
                <span className="inline-flex items-center gap-1 text-green-500 text-sm mt-3">
                  <CheckIcon className="w-4 h-4" />
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
            disabled={currentStep === steps.length - 1 || (state !== 'complete' && state !== 'skipped')}
            className="btn-primary"
          >
            {currentStep === steps.length - 1 ? 'Finish' : 'Next'}
            <ArrowRightIcon className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}