import React from 'react';
import { useConfig } from '../../context/ConfigContext';
import { useBackend } from '../../hooks/useBackend';
import { useProviders } from '../../hooks/useProviders';
import { cn } from '../../utils/cn';
import { Brain, CheckCircle, SettingsIcon } from '../Icons/ProviderIcons';
import { useNavigate } from 'react-router-dom';

export function Header() {
  const { config, updateConfig } = useConfig();
  const { health, checkHealth, pullModel } = useBackend();
  const { getActiveProvider } = useProviders();
  const navigate = useNavigate();
  const [showModelSelect, setShowModelSelect] = React.useState(false);
  const [pullingModel, setPullingModel] = React.useState<string | null>(null);
  const [showSettings, setShowSettings] = React.useState(false);

  const activeProvider = getActiveProvider();

  const handleModelChange = async (model: string) => {
    updateConfig({ model });
    setShowModelSelect(false);
  }

  const handlePullModel = async (model: string) => {
    setPullingModel(model);
    await pullModel(model);
    setPullingModel(null);
  }

  return (
    <header className="h-16 bg-dark-surface border-b border-dark-border flex items-center justify-between px-4">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-primary-500" />
          <span className="font-semibold text-lg">Humitron</span>
        </div>
        
        {/* Active Provider Display */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-dark-elevated rounded-lg border border-dark-border">
          {activeProvider ? (
            <>
              <span className="text-xs text-gray-400">Using:</span>
              <span className="font-mono text-sm text-primary-400">
                {activeProvider.name} ({activeProvider.modelId})
              </span>
              <span className={cn('w-2 h-2 rounded-full', activeProvider.enabled ? 'bg-green-500' : 'bg-red-500')} />
            </>
          ) : (
            <span className="text-xs text-gray-500">No provider selected</span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        {/* Ollama Status */}
        <div className="hidden md:flex items-center gap-2">
          <div className={cn('w-2 h-2 rounded-full', health.ollamaRunning ? 'bg-green-500' : 'bg-gray-600')} />
          <span className="text-sm text-gray-400">Ollama</span>
          {!health.ollamaRunning && health.models.length === 0 && (
            <button
              onClick={() => handlePullModel('llama3.2')}
              disabled={pullingModel === 'llama3.2'}
              className="btn-ghost p-1.5 text-xs"
            >
              {pullingModel === 'llama3.2' ? 'Pulling...' : 'Pull Llama 3.2'}
            </button>
          )}
        </div>

        {/* Backend Status */}
        <div className="hidden md:flex items-center gap-2">
          <div className={cn('w-2 h-2 rounded-full', health.backendRunning ? 'bg-green-500' : 'bg-red-500')} />
          <span className="text-sm text-gray-400">Backend</span>
        </div>

        {/* Settings Button */}
        <button
          onClick={() => setShowSettings(true)}
          className="btn-ghost p-2"
          aria-label="Open settings"
        >
          <SettingsIcon className="w-5 h-5" />
        </button>
      </div>

      {showSettings && (
        <div className="fixed inset-0 z-50" onClick={() => setShowSettings(false)}>
          <div className="absolute right-4 top-16 w-64 card animate-slide-down">
            <button 
              onClick={() => navigate('/settings')}
              className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-dark-elevated rounded"
            >
              <SettingsIcon className="w-5 h-5" />
              <span>AI Providers</span>
            </button>
            <button 
              onClick={() => setShowSettings(false)}
              className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-dark-elevated rounded"
            >
              <span>General Settings</span>
            </button>
          </div>
        </div>
      )}
    </header>
  );
}