import axios, { AxiosInstance } from "axios";
import { config } from "../../config";
import { logger } from "../observability/logger";

export class ShopifyClient {
  private client: AxiosInstance;

  constructor() {
    if (!config.SHOPIFY_STORE_DOMAIN) {
      logger.error("Shopify store domain not configured");
      throw new Error("SHOPIFY_STORE_DOMAIN is required");
    }

    if (!config.SHOPIFY_ACCESS_TOKEN) {
      logger.error("Shopify access token not configured");
      throw new Error("SHOPIFY_ACCESS_TOKEN is required");
    }

    this.client = axios.create({
      baseURL: `https://${config.SHOPIFY_STORE_DOMAIN}/admin/api/${config.SHOPIFY_API_VERSION}`,
      headers: {
        "X-Shopify-Access-Token": config.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json",
      },
      timeout: 10000,
    });

    // Request interceptor for logging
    this.client.interceptors.request.use(
      (config) => {
        logger.info("Shopify API request", { 
          method: config.method, 
          url: config.url 
        });
        return config;
      },
      (error) => {
        logger.error("Shopify request error", { error: error.message });
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        logger.error("Shopify API error", {
          status: error.response?.status,
          message: error.response?.data?.errors || error.message,
        });
        return Promise.reject(error);
      }
    );
  }

  getClient(): AxiosInstance {
    return this.client;
  }
}

// Singleton instance
export const shopifyClient = new ShopifyClient().getClient();
