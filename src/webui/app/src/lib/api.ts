/**
 * API Client for Climate Multilingual Chatbot
 * Integrates with FastAPI backend
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatRequest {
  query: string;
  language?: string;
  conversation_history?: ChatMessage[];
  stream?: boolean;
}

export interface CitationDict {
  title: string;
  url: string;
  content?: string;
  snippet?: string;
}

export interface ChatResponse {
  success: boolean;
  response: string;
  citations: CitationDict[];
  faithfulness_score: number;
  processing_time: number;
  language_used: string;
  model_used?: string;
  request_id: string;
}

export interface FeedbackRequest {
  message_id: string;
  feedback_type: 'thumbs_up' | 'thumbs_down';
  categories: string[];
  comment?: string;
  language_code?: string;
}

export interface FeedbackResponse {
  success: boolean;
  feedback_id: string;
  pii_detected: boolean;
  request_id: string;
}

export interface LanguageInfo {
  code: string;
  name: string;
}

export interface SupportedLanguagesResponse {
  command_a_languages: LanguageInfo[];
  nova_languages: LanguageInfo[];
  default_language: string;
  total_supported: number;
}

export interface ApiError {
  error: {
    code: string;
    type: string;
    message: string;
    retryable: boolean;
    request_id?: string;
  };
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const errorData: ApiError = await response.json();
      throw new Error(errorData.error.message || `HTTP ${response.status}`);
    }

    return response.json();
  }

  /**
   * Send a chat query to the API
   */
  async sendChatQuery(request: ChatRequest): Promise<ChatResponse> {
    return this.request<ChatResponse>('/api/v1/chat/query', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * Submit feedback for a message
   */
  async submitFeedback(request: FeedbackRequest): Promise<FeedbackResponse> {
    return this.request<FeedbackResponse>('/api/v1/feedback/submit', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * Get supported languages
   */
  async getSupportedLanguages(): Promise<SupportedLanguagesResponse> {
    return this.request<SupportedLanguagesResponse>('/api/v1/languages/supported');
  }

  /**
   * Get feedback categories
   */
  async getFeedbackCategories(): Promise<{
    thumbs_up: string[];
    thumbs_down: string[];
    description: Record<string, Record<string, string>>;
  }> {
    return this.request('/api/v1/feedback/categories');
  }

  /**
   * Create an EventSource for streaming chat responses
   */
  createStreamingConnection(request: ChatRequest): EventSource {
    const url = new URL(`${this.baseUrl}/api/v1/chat/stream`);
    
    // For GET request with query params, we'd need to serialize the request
    // But our API expects POST, so we'll need to implement this differently
    // For now, return a placeholder - we'll implement proper SSE later
    
    const eventSource = new EventSource(url.toString());
    return eventSource;
  }

  /**
   * Stream chat responses using fetch with ReadableStream
   */
  async streamChatQuery(
    request: ChatRequest,
    onProgress: (data: any) => void,
    onComplete: (response: ChatResponse) => void,
    onError: (error: Error) => void
  ): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

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
              
              if (data.type === 'complete') {
                onComplete(data);
              } else if (data.type === 'error') {
                onError(new Error(data.message));
              } else {
                onProgress(data);
              }
            } catch (e) {
              console.warn('Failed to parse SSE data:', line);
            }
          }
        }
      }
    } catch (error) {
      onError(error instanceof Error ? error : new Error('Stream failed'));
    }
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<{ status: string; timestamp: number }> {
    return this.request('/health');
  }
}

// Export singleton instance
export const apiClient = new ApiClient();