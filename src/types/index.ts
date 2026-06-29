export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'tool' | 'system';
  content: string;
  timestamp: Date;
  toolCalls?: ToolCall[];
  toolResult?: ToolResult;
  thinking?: string;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
  status: 'pending' | 'running' | 'completed' | 'failed';
  result?: any;
  error?: string;
  startTime: Date;
  endTime?: Date;
}

export interface ToolResult {
  success: boolean;
  output: string;
  error?: string;
}

export interface Session {
  id: string;
  name: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
  model: string;
  workspace: string;
}

export interface Config {
  model: string;
  temperature: number;
  maxSteps: number;
  workspace: string;
  ollamaUrl: string;
  cloudProvider?: 'openai' | 'anthropic' | 'openrouter';
  cloudApiKey?: string;
  theme: 'dark' | 'light' | 'system';
  enableMcp: boolean;
}

export interface OllamaModel {
  name: string;
  size: number;
  modifiedAt: string;
  details?: {
    format: string;
    family: string;
    parameterSize: string;
    quantizationLevel: string;
  };
}

export interface HealthStatus {
  ollamaRunning: boolean;
  models: OllamaModel[];
  backendRunning: boolean;
  error?: string;
}

export interface CostInfo {
  totalTokens: number;
  inputTokens: number;
  outputTokens: number;
  estimatedCost: number;
  model: string;
}