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
      timeout: 60000, // 60 seconds for LLM + embedding generation
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

      // Transform request to match Python API format
      const pythonRequest = {
        message: request.message,
        session_id: request.sessionId,
      };

      const response = await this.client.post<any>(
        "/assistant/message",
        pythonRequest
      );

      logger.info("Assistant response received", { 
        sessionId: request.sessionId,
        hasActions: !!response.data.suggested_actions,
      });

      // Transform Python response to match Node backend format
      // Also transform product fields: name→title, image_url→image, add url
      const transformedProducts = (response.data.products || []).map((product: any) => ({
        id: product.id,
        title: product.name,           // name → title
        price: product.price,
        image: product.image_url,       // image_url → image
        url: product.url || `/products/${product.id}`,  // add url field
        description: product.description,
      }));

      // Transform actions from strings/objects to proper action objects
      const transformedActions = (response.data.suggested_actions || []).map((action: string | any) => {
        // Handle object actions (like add_to_cart)
        if (typeof action === 'object' && action.type) {
          return action;  // Return as-is
        }
        
        // Handle string actions
        if (typeof action !== 'string') {
          return null;
        }
        
        // If action is "search_results", create search_results action with products
        if (action === "search_results") {
          return {
            type: "search_results",
            data: {
              results: transformedProducts,
              totalCount: transformedProducts.length,
              query: ""  // Could extract from context if needed
            }
          };
        }
        
        // Other string actions are just button labels (not rendered as actions currently)
        return null;
      }).filter(Boolean);  // Remove null actions

      const transformedResponse: AssistantResponse = {
        replyText: response.data.message,
        actions: transformedActions,  // Use transformed actions
        context: {
          sessionId: response.data.session_id,
          intent: response.data.intent,
          products: transformedProducts,  // keep for context
        },
      };

      return transformedResponse;
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

  /**
   * Generic request method for custom endpoints
   */
  async request<T = any>(method: string, endpoint: string, data?: any): Promise<{ data: T }> {
    try {
      const response = await this.client.request<T>({
        method,
        url: endpoint,
        data,
      });
      return { data: response.data };
    } catch (error) {
      logger.error(`Python ${method} ${endpoint} failed`, { error });
      throw error;
    }
  }
}

// Singleton instance
export const pythonAssistantClient = new PythonAssistantClient();
