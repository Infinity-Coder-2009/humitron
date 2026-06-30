import { useState } from 'react';
import { useConfig } from '../../context/ConfigContext';
import { useBackend } from '../../hooks/useBackend';
import { cn } from '../../utils/cn';
import { X, Save, FolderOpen, Key, Brain, SlidersHorizontal, ProviderIcon } from '../Icons/ProviderIcons';
import { invoke } from '@tauri-apps/api/core';

export function SettingsPanel({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const { config, updateConfig } = useConfig();
  const { health } = useBackend();
  const [testWorkspace, setTestWorkspace] = useState(config.workspace);
  const [apiKey, setApiKey] = useState(config.cloudApiKey || '');
  const [showApiKey, setShowApiKey] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    updateConfig({ 
      workspace: testWorkspace,
      cloudApiKey: apiKey || undefined,
    });
    try {
      await invoke('update_config', { config: { workspace: testWorkspace } });
    } catch (e) {
      console.error('Failed to save config to backend:', e);
    }
    setSaving(false);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />
      <div className="relative card w-full max-w-2xl max-h-[90vh] overflow-y-auto animate-slide-up">
        <div className="flex items-center justify-between mb-6 pb-4 border-b border-dark-border sticky top-0 bg-dark-surface z-10 py-4">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <SlidersHorizontal className="w-5 h-5" />
            Settings
          </h2>
          <button onClick={onClose} className="btn-ghost p-2">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-6 pr-4">
          <section>
            <h3 className="font-medium text-gray-300 mb-4 flex items-center gap-2">
              <Brain className="w-5 h-5 text-primary-500" />
              Model Configuration
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Default Model</label>
                <select
                  value={config.model}
                  onChange={e => updateConfig({ model: e.target.value })}
                  className="input"
                >
                  <optgroup label="Local (Ollama)">
                    <option value="llama3.2">Llama 3.2</option>
                    <option value="mistral">Mistral</option>
                    <option value="phi4">Phi-4</option>
                    <option value="codellama">Code Llama</option>
                    <option value="llama3.1">Llama 3.1</option>
                  </optgroup>
                  <optgroup label="Cloud (Requires API Key)">
                    <option value="gpt-4">GPT-4</option>
                    <option value="gpt-4-turbo">GPT-4 Turbo</option>
                    <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                    <option value="claude-3-opus">Claude 3 Opus</option>
                    <option value="claude-3-sonnet">Claude 3 Sonnet</option>
                    <option value="claude-3-haiku">Claude 3 Haiku</option>
                  </optgroup>
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  {['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo', 'claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku'].includes(config.model) 
                    ? 'Cloud model - requires API key in AI Providers settings' 
                    : 'Local model - runs via Ollama (free)'}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Temperature</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="range"
                      min="0"
                      max="2"
                      step="0.1"
                      value={config.temperature}
                      onChange={e => updateConfig({ temperature: parseFloat(e.target.value) })}
                      className="flex-1 h-2 bg-dark-elevated rounded-lg appearance-none accent-primary-500"
                    />
                    <span className="font-mono text-sm w-10">{config.temperature.toFixed(1)}</span>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Max Steps</label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={config.maxSteps}
                    onChange={e => updateConfig({ maxSteps: parseInt(e.target.value) })}
                    className="input"
                  />
                </div>
              </div>
            </div>
          </section>

          <section>
            <h3 className="font-medium text-gray-300 mb-4 flex items-center gap-2">
              <FolderOpen className="w-5 h-5 text-primary-500" />
              Workspace
            </h3>
            <div className="space-y-2">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={testWorkspace}
                  onChange={e => setTestWorkspace(e.target.value)}
                  className="input flex-1"
                  placeholder="Workspace path"
                />
                <button
                  onClick={async () => {
                    try {
                      const path = await invoke('pick_folder');
                      if (path) setTestWorkspace(path);
                    } catch (e) {
                      console.error('Failed to pick folder:', e);
                    }
                  }}
                  className="btn-secondary"
                >
                  <FolderOpen className="w-4 h-4" />
                  Browse
                </button>
              </div>
              <p className="text-xs text-gray-500">The agent can only read/write files within this directory</p>
            </div>
          </section>

          <section>
            <h3 className="font-medium text-gray-300 mb-4">Ollama Status</h3>
            <div className="card">
              <div className="flex items-center gap-3">
                <div className={cn('w-3 h-3 rounded-full', health.ollamaRunning ? 'bg-green-500' : 'bg-red-500')} />
                <div>
                  <p className="font-medium">{health.ollamaRunning ? 'Running' : 'Not Running'}</p>
                  <p className="text-sm text-gray-500">
                    {health.ollamaRunning 
                      ? `${health.models.length} model(s) available` 
                      : 'Install Ollama from ollama.ai for local models'}
                  </p>
                </div>
              </div>
              {health.models.length > 0 && (
                <div className="mt-3 space-y-1">
                  {health.models.map((model: any) => (
                    <div key={model.name} className="flex items-center justify-between text-sm">
                      <span className="font-mono">{model.name}</span>
                      <span className="text-gray-500">
                        {(model.size / 1024 / 1024 / 1024).toFixed(1)} GB
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>
        </div>

        <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-dark-border sticky bottom-0 bg-dark-surface z-10 py-4">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={handleSave} className="btn-primary" disabled={saving}>
            {saving ? 'Saving...' : 'Save Settings'}
            <Save className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}