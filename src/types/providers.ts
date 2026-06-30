export interface AIProvider {
  id: string;
  name: string;
  baseUrl: string;
  apiKey: string;
  modelId: string;
  enabled: boolean;
  type: 'openai' | 'anthropic' | 'gemini' | 'openrouter' | 'ollama' | 'custom';
  icon?: string;
  lastTested?: string;
  testStatus?: 'success' | 'error' | 'pending';
  testMessage?: string;
}

export interface ProviderConfig {
  providers: AIProvider[];
  activeProviderId: string | null;
}

export const DEFAULT_PROVIDERS: Omit<AIProvider, 'id' | 'enabled' | 'apiKey' | 'lastTested' | 'testStatus' | 'testMessage'>[] = [
  {
    name: 'OpenAI',
    baseUrl: 'https://api.openai.com/v1',
    modelId: 'gpt-4o-mini',
    type: 'openai',
  },
  {
    name: 'Claude',
    baseUrl: 'https://api.anthropic.com/v1',
    modelId: 'claude-3-haiku-20240307',
    type: 'anthropic',
  },
  {
    name: 'Gemini',
    baseUrl: 'https://generativelanguage.googleapis.com/v1beta',
    modelId: 'gemini-1.5-flash',
    type: 'gemini',
  },
  {
    name: 'OpenRouter',
    baseUrl: 'https://openrouter.ai/api/v1',
    modelId: 'meta-llama/llama-3.1-8b-instruct',
    type: 'openrouter',
  },
];

export const PROVIDER_ICONS: Record<string, string> = {
  openai: 'openai',
  anthropic: 'anthropic',
  gemini: 'gemini',
  openrouter: 'openrouter',
  ollama: 'ollama',
  custom: 'custom',
};