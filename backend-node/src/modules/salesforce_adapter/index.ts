/**
 * Salesforce Adapter - Public API
 * Standalone module for Salesforce B2B Commerce integration
 */

import { SalesforceClient } from "./client";
import { ProductService } from "./products";
import { CartService } from "./cart";
import { SalesforceConfig } from "./types";

export interface SalesforceAdapter {
  products: ProductService;
  cart: CartService;
  client: SalesforceClient;
}

export function createSalesforceAdapter(options: {
  config: SalesforceConfig;
}): SalesforceAdapter {
  const client = new SalesforceClient(options.config);

  return {
    products: new ProductService(client),
    cart: new CartService(client),
    client,
  };
}

// Re-export types
export * from "./types";
export type { Product } from "./products";
export type { Cart, CartItem } from "./cart";