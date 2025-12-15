import { shopifyClient } from "./client";
import { logger } from "../observability/logger";

export interface CartItem {
  variant_id: number;
  quantity: number;
  properties?: Record<string, string>;
}

export interface Cart {
  token: string;
  note?: string;
  attributes?: Record<string, string>;
  original_total_price: number;
  total_price: number;
  total_discount: number;
  total_weight: number;
  item_count: number;
  items: CartItem[];
  requires_shipping: boolean;
  currency: string;
}

/**
 * Add item to cart
 * Note: Shopify cart operations typically use Storefront API or Ajax API
 * This is a simplified version - you may need to use Storefront API for production
 */
export async function addToCart(
  sessionId: string, 
  variantId: number, 
  quantity: number = 1,
  properties?: Record<string, string>
): Promise<any> {
  try {
    logger.info("Adding to cart", { sessionId, variantId, quantity });
    
    // Using Shopify's Ajax API endpoint
    // Note: In production, you might use Storefront API with proper authentication
    const response = await shopifyClient.post(`/cart/add.js`, {
      id: variantId,
      quantity,
      properties,
    });
    
    return response.data;
  } catch (error: any) {
    logger.error("Failed to add to cart", { 
      sessionId, 
      variantId, 
      error: error.message 
    });
    throw error;
  }
}

/**
 * Update cart item quantity
 */
export async function updateCartItem(
  sessionId: string,
  variantId: number,
  quantity: number
): Promise<any> {
  try {
    logger.info("Updating cart item", { sessionId, variantId, quantity });
    
    const response = await shopifyClient.post(`/cart/change.js`, {
      id: variantId,
      quantity,
    });
    
    return response.data;
  } catch (error: any) {
    logger.error("Failed to update cart item", { 
      sessionId, 
      variantId, 
      error: error.message 
    });
    throw error;
  }
}

/**
 * Get current cart
 */
export async function getCart(sessionId: string): Promise<Cart | null> {
  try {
    logger.info("Fetching cart", { sessionId });
    
    const { data } = await shopifyClient.get(`/cart.js`);
    return data;
  } catch (error: any) {
    logger.error("Failed to get cart", { 
      sessionId, 
      error: error.message 
    });
    
    if (error.response?.status === 404) {
      return null;
    }
    
    throw error;
  }
}

/**
 * Clear cart
 */
export async function clearCart(sessionId: string): Promise<any> {
  try {
    logger.info("Clearing cart", { sessionId });
    
    const response = await shopifyClient.post(`/cart/clear.js`);
    return response.data;
  } catch (error: any) {
    logger.error("Failed to clear cart", { 
      sessionId, 
      error: error.message 
    });
    throw error;
  }
}

/**
 * Remove item from cart
 */
export async function removeFromCart(
  sessionId: string,
  variantId: number
): Promise<any> {
  try {
    logger.info("Removing from cart", { sessionId, variantId });
    
    // Set quantity to 0 to remove
    return await updateCartItem(sessionId, variantId, 0);
  } catch (error: any) {
    logger.error("Failed to remove from cart", { 
      sessionId, 
      variantId, 
      error: error.message 
    });
    throw error;
  }
}
