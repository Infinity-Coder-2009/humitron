import axios, { AxiosInstance } from 'axios';
import { Message, HealthStatus, OllamaModel } from '../types';

class ApiClient {
  private client: AxiosInstance;

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.client = axios.create({
      baseURL: baseUrl,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  setBaseUrl(url: string) {
    this.client.defaults.baseURL = url;
  }

  async healthCheck(): Promise<HealthStatus> {
    try {
      const response = await this.client.get('/health');
      return response.data;
    } catch (error) {
      return {
        ollamaRunning: false,
        models: [],
        backendRunning: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  async getModels(): Promise<OllamaModel[]> {
    try {
      const response = await this.client.get('/models');
      return response.data.models || [];
    } catch {
      return [];
    }
  }

  async pullModel(name: string): Promise<string> {
    const response = await this.client.post('/models/pull', { name });
    return response.data.message;
  }

  async *streamChat(
    prompt: string,
    sessionId: string,
    config: { model: string; temperature: number; maxSteps: number; workspace: string }
  ): AsyncGenerator<{ type: 'thinking' | 'tool_call' | 'tool_result' | 'content' | 'done' | 'error'; data: any }> {
    try {
      const response = await this.client.post('/chat', {
        prompt,
        session_id: sessionId,
        ...config,
      }, {
        responseType: 'stream',
      });

      const reader = response.data.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              yield data;
            } catch (e) {
              console.error('Failed to parse SSE:', e);
            }
          }
        }
      }
    } catch (error) {
      yield { type: 'error', data: { message: error instanceof Error ? error.message : 'Unknown error' } };
    }
  }

  async getSessions(): Promise<{ id: string; name: string; created_at: string; updated_at: string }[]> {
    try {
      const response = await this.client.get('/sessions');
      return response.data.sessions || [];
    } catch {
      return [];
    }
  }

  async createSession(name: string, config: Partial<{ model: string; workspace: string }>): Promise<string> {
    const response = await this.client.post('/sessions', { name, ...config });
    return response.data.session_id;
  }

  async deleteSession(id: string): Promise<void> {
    await this.client.delete(`/sessions/${id}`);
  }

  async getSessionMessages(sessionId: string): Promise<Message[]> {
    try {
      const response = await this.client.get(`/sessions/${sessionId}/messages`);
      return response.data.messages || [];
    } catch {
      return [];
    }
  }

  async updateConfig(config: Partial<{ model: string; temperature: number; max_steps: number; workspace: string }>): Promise<void> {
    await this.client.post('/config', config);
  }
}

export const apiClient = new ApiClient();

export function setApiBaseUrl(url: string) {
  apiClient.setBaseUrl(url);
}