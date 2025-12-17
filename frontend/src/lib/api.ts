import axios, { AxiosInstance, AxiosError } from 'axios';
import { MessageAction } from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001';

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000, // 60 seconds for LLM + embedding generation
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add any auth tokens here if needed
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const errorData = error.response?.data as { message?: string } | undefined;
    console.error('API Error:', {
      status: error.response?.status,
      message: errorData?.message || error.message,
      url: error.config?.url,
    });
    return Promise.reject(error);
  }
);

// ============================================================================
// Chat API
// ============================================================================

export interface ChatMessage {
  message: string;
  sessionId: string;
}

export interface ChatResponse {
  replyText: string;
  actions?: MessageAction[];
  sessionId: string;
}

export const chatApi = {
  sendMessage: async (message: string, sessionId: string): Promise<ChatResponse> => {
    const response = await apiClient.post<ChatResponse>('/api/chat', {
      message,
      sessionId,
    });
    return response.data;
  },
};

// ============================================================================
// Health API
// ============================================================================

export interface HealthResponse {
  status: string;
  service: string;
  timestamp: string;
  pythonBackend?: string;
  shopifyConfigured?: boolean;
}

export const healthApi = {
  check: async (): Promise<HealthResponse> => {
    const response = await apiClient.get<HealthResponse>('/health');
    return response.data;
  },
};

// ============================================================================
// Products API (future)
// ============================================================================

export interface Product {
  id: string;
  title: string;
  description?: string;
  price: string;
  image: string;
  url: string;
  inStock?: boolean;
}

export const productsApi = {
  // Will be implemented when backend endpoints are ready
  search: async (query: string): Promise<Product[]> => {
    // Placeholder - backend endpoint to be created
    return [];
  },
  
  getById: async (id: string): Promise<Product | null> => {
    // Placeholder - backend endpoint to be created
    return null;
  },
};

// ============================================================================
// Analytics API (future)
// ============================================================================

export interface AnalyticsMetrics {
  totalChats: number;
  activeUsers: number;
  avgResponseTime: number;
  conversionRate: number;
}

export const analyticsApi = {
  getMetrics: async (): Promise<AnalyticsMetrics> => {
    // Placeholder - backend endpoint to be created
    return {
      totalChats: 0,
      activeUsers: 0,
      avgResponseTime: 0,
      conversionRate: 0,
    };
  },
};

// Export default client
export default apiClient;
