/**
 * Shared TypeScript Types for EasyMart Node Backend
 * These types align with the Python backend API contracts
 */

// ============================================================================
// Assistant API Types (Node ↔ Python)
// ============================================================================

/**
 * Request to Python Assistant API
 * POST /assistant/message
 */
export interface AssistantRequest {
  message: string;
  sessionId: string;
  context?: AssistantContext;
}

/**
 * Response from Python Assistant API
 */
export interface AssistantResponse {
  replyText: string;
  actions?: AssistantAction[];
  context?: AssistantContext;
  sessionId: string;
}

/**
 * Context passed between requests to maintain conversation state
 */
export interface AssistantContext {
  conversationHistory?: ConversationTurn[];
  userPreferences?: Record<string, any>;
  lastIntent?: string;
  metadata?: Record<string, any>;
}

/**
 * Single conversation turn
 */
export interface ConversationTurn {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

/**
 * Actions that the assistant can trigger
 */
export type AssistantAction =
  | ProductCardAction
  | AddToCartAction
  | SearchResultsAction
  | SpecAnswerAction;

/**
 * Display product card action
 */
export interface ProductCardAction {
  type: "product_card";
  data: ProductCard;
}

/**
 * Add to cart action
 */
export interface AddToCartAction {
  type: "add_to_cart";
  data: {
    productId: string;
    variantId: string;
    quantity: number;
  };
}

/**
 * Search results action
 */
export interface SearchResultsAction {
  type: "search_results";
  data: {
    query: string;
    results: ProductCard[];
    totalCount: number;
  };
}

/**
 * Spec-based answer action
 */
export interface SpecAnswerAction {
  type: "spec_answer";
  data: {
    question: string;
    answer: string;
    sourceProducts?: string[];
  };
}

// ============================================================================
// Product Types (Shopify & Widget)
// ============================================================================

/**
 * Product card displayed in chat widget
 */
export interface ProductCard {
  id: string;
  title: string;
  description?: string;
  price: string;
  image: string;
  url: string;
  variants?: ProductVariant[];
  inStock?: boolean;
}

/**
 * Product variant
 */
export interface ProductVariant {
  id: string;
  title: string;
  price: string;
  available: boolean;
  sku?: string;
}

// ============================================================================
// Shopify Types
// ============================================================================

/**
 * Shopify product (from Admin API)
 */
export interface ShopifyProduct {
  id: number;
  title: string;
  body_html: string;
  vendor: string;
  product_type: string;
  handle: string;
  status: string;
  variants: ShopifyVariant[];
  images: ShopifyImage[];
  options: ShopifyOption[];
}

/**
 * Shopify variant
 */
export interface ShopifyVariant {
  id: number;
  product_id: number;
  title: string;
  price: string;
  sku: string;
  position: number;
  inventory_quantity: number;
  available: boolean;
}

/**
 * Shopify image
 */
export interface ShopifyImage {
  id: number;
  product_id: number;
  src: string;
  alt?: string;
  position: number;
}

/**
 * Shopify product option (size, color, etc.)
 */
export interface ShopifyOption {
  id: number;
  product_id: number;
  name: string;
  position: number;
  values: string[];
}

/**
 * Shopify cart
 */
export interface ShopifyCart {
  token: string;
  note?: string;
  attributes?: Record<string, string>;
  total_price: number;
  total_discount: number;
  total_weight: number;
  item_count: number;
  items: ShopifyCartItem[];
  currency: string;
}

/**
 * Shopify cart item
 */
export interface ShopifyCartItem {
  id: number;
  variant_id: number;
  product_id: number;
  title: string;
  quantity: number;
  price: string;
  line_price: string;
  image?: string;
  handle: string;
}

// ============================================================================
// Session Types
// ============================================================================

/**
 * Session data stored for each user
 */
export interface SessionData {
  sessionId: string;
  userId?: string;
  createdAt: string;
  lastActivity: string;
  conversationHistory: ConversationTurn[];
  cart?: ShopifyCart;
  preferences?: UserPreferences;
}

/**
 * User preferences
 */
export interface UserPreferences {
  language?: string;
  currency?: string;
  categories?: string[];
  priceRange?: {
    min: number;
    max: number;
  };
}

// ============================================================================
// Error Types
// ============================================================================

/**
 * Standard error response
 */
export interface ErrorResponse {
  error: string;
  message: string;
  statusCode: number;
  details?: any;
}

/**
 * API error
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode: number = 500,
    public details?: any
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ============================================================================
// Health Check Types
// ============================================================================

/**
 * Health check response
 */
export interface HealthCheckResponse {
  status: "ok" | "degraded" | "error";
  service: string;
  environment?: string;
  timestamp: string;
  pythonBackend?: string;
  shopifyConfigured?: boolean;
  uptime?: number;
}

// ============================================================================
// Widget Types
// ============================================================================

/**
 * Widget configuration
 */
export interface WidgetConfig {
  backendUrl: string;
  theme?: "light" | "dark";
  position?: "bottom-right" | "bottom-left";
  primaryColor?: string;
  headerText?: string;
}

/**
 * Widget message
 */
export interface WidgetMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  timestamp: string;
  actions?: AssistantAction[];
}
