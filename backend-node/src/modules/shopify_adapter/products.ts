import { shopifyClient } from "./client";
import { logger } from "../observability/logger";

export interface ShopifyProduct {
  id: number;
  title: string;
  body_html: string;
  vendor: string;
  product_type: string;
  handle: string;
  status: string;
  variants: any[];
  images: any[];
  options: any[];
}

/**
 * Get product details by ID
 */
export async function getProductDetails(productId: string): Promise<ShopifyProduct | null> {
  try {
    logger.info("Fetching product details", { productId });
    
    const { data } = await shopifyClient.get(`/products/${productId}.json`);
    return data.product;
  } catch (error: any) {
    logger.error("Failed to get product details", { 
      productId, 
      error: error.message 
    });
    
    if (error.response?.status === 404) {
      return null;
    }
    
    throw error;
  }
}

/**
 * Search products by query
 */
export async function searchProducts(
  query: string, 
  limit: number = 10
): Promise<ShopifyProduct[]> {
  try {
    logger.info("Searching products", { query, limit });
    
    const { data } = await shopifyClient.get(`/products.json`, {
      params: { 
        title: query,
        limit: Math.min(limit, 250), // Shopify limit
      },
    });
    
    return data.products || [];
  } catch (error: any) {
    logger.error("Failed to search products", { 
      query, 
      error: error.message 
    });
    throw error;
  }
}

/**
 * Get all products (with pagination)
 */
export async function getAllProducts(
  limit: number = 50,
  sinceId?: number
): Promise<ShopifyProduct[]> {
  try {
    const params: any = { limit: Math.min(limit, 250) };
    if (sinceId) {
      params.since_id = sinceId;
    }
    
    const { data } = await shopifyClient.get(`/products.json`, { params });
    return data.products || [];
  } catch (error: any) {
    logger.error("Failed to get all products", { error: error.message });
    throw error;
  }
}

/**
 * Get product by handle (URL-friendly identifier)
 */
export async function getProductByHandle(handle: string): Promise<ShopifyProduct | null> {
  try {
    const { data } = await shopifyClient.get(`/products.json`, {
      params: { handle },
    });
    
    return data.products?.[0] || null;
  } catch (error: any) {
    logger.error("Failed to get product by handle", { 
      handle, 
      error: error.message 
    });
    throw error;
  }
}
