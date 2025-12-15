import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse, AxiosError } from "axios";
import { config } from "../config";
import { logger } from "../modules/observability/logger";

interface AssistantRequest {
  message: string;
  sessionId: string;
}

interface AssistantResponse {
  replyText: string;
  actions?: any[];
  context?: any;
}

class PythonAssistantClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: config.PYTHON_BASE_URL,
      timeout: 30000, // 30 seconds for LLM responses
      headers: {
        "Content-Type": "application/json",
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        logger.info("Python API request", { 
          url: config.url,
          baseURL: config.baseURL,
        });
        return config;
      },
      (error: AxiosError) => {
        logger.error("Python request setup error", { error: error.message });
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        logger.info("Python API response received", { 
          status: response.status,
        });
        return response;
      },
      (error: AxiosError) => {
        const errorData = error.response?.data as { message?: string } | undefined;
        logger.error("Python API error", {
          status: error.response?.status,
          message: errorData?.message || error.message,
          url: error.config?.url,
        });
        return Promise.reject(error);
      }
    );
  }

  /**
   * Send message to Python assistant
   */
  async sendMessage(request: AssistantRequest): Promise<AssistantResponse> {
    try {
      logger.info("Sending message to Python assistant", { 
        sessionId: request.sessionId,
        messageLength: request.message.length,
      });

      const response = await this.client.post<AssistantResponse>(
        "/assistant/message",
        request
      );

      logger.info("Assistant response received", { 
        sessionId: request.sessionId,
        hasActions: !!response.data.actions,
      });

      return response.data;
    } catch (error: any) {
      logger.error("Failed to get assistant response", {
        sessionId: request.sessionId,
        error: error.message,
        status: error.response?.status,
      });

      // Return fallback response if Python service is down
      if (error.code === "ECONNREFUSED" || error.code === "ETIMEDOUT") {
        logger.warn("Python service unavailable, returning fallback");
        return {
          replyText: "I'm temporarily unavailable. Please try again in a moment.",
        };
      }

      throw error;
    }
  }

  /**
   * Health check for Python service
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.client.get("/health", { timeout: 5000 });
      return response.status === 200;
    } catch (error) {
      logger.error("Python health check failed", { error });
      return false;
    }
  }
}

// Singleton instance
export const pythonAssistantClient = new PythonAssistantClient();
