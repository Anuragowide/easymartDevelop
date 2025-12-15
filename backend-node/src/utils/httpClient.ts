import axios, { AxiosInstance, AxiosRequestConfig, InternalAxiosRequestConfig, AxiosResponse, AxiosError } from "axios";
import { logger } from "../modules/observability/logger";

/**
 * Create a configured Axios instance with interceptors
 */
export function createHttpClient(baseURL: string, config?: AxiosRequestConfig): AxiosInstance {
  const client = axios.create({
    baseURL,
    timeout: 10000,
    ...config,
  });

  // Request interceptor
  client.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      logger.info("HTTP request", { 
        method: config.method,
        url: config.url,
        baseURL: config.baseURL,
      });
      return config;
    },
    (error: AxiosError) => {
      logger.error("HTTP request error", { error: error.message });
      return Promise.reject(error);
    }
  );

  // Response interceptor
  client.interceptors.response.use(
    (response: AxiosResponse) => response,
    (error: AxiosError) => {
      logger.error("HTTP response error", {
        status: error.response?.status,
        message: error.message,
        url: error.config?.url,
      });
      return Promise.reject(error);
    }
  );

  return client;
}

/**
 * Retry logic for failed requests
 */
export async function retryRequest<T>(
  fn: () => Promise<T>,
  retries: number = 3,
  delay: number = 1000
): Promise<T> {
  try {
    return await fn();
  } catch (error) {
    if (retries === 0) {
      throw error;
    }

    logger.warn("Retrying request", { retriesLeft: retries, delay });
    await new Promise<void>((resolve) => setTimeout(resolve, delay));
    return retryRequest(fn, retries - 1, delay * 2);
  }
}
