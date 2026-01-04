// ============================================================================
// Message Types
// ============================================================================

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  actions?: MessageAction[];
}

export interface MessageAction {
  type: 'search_results' | 'product_card' | 'add_to_cart' | 'remove_from_cart' | 'clear_cart' | 'view_cart' | 'spec_answer';
  data: any;
}

// ============================================================================
// Product Types
// ============================================================================

export interface ProductCard {
  id: string;
  title: string;
  description?: string;
  price: string;
  image: string;
  url: string;
  inStock?: boolean;
  variants?: ProductVariant[];
}

export interface ProductVariant {
  id: string;
  title: string;
  price: string;
  available: boolean;
  sku?: string;
}

export interface SearchResultsAction {
  type: 'search_results';
  data: {
    query: string;
    results: ProductCard[];
    totalCount: number;
  };
}

export interface ProductCardAction {
  type: 'product_card';
  data: ProductCard;
}

// ============================================================================
// Chat Types
// ============================================================================

export interface ChatSession {
  id: string;
  messages: Message[];
  createdAt: string;
  updatedAt: string;
}

export interface ChatState {
  messages: Message[];
  sessionId: string;
  isLoading: boolean;
  error: string | null;
}

// ============================================================================
// API Response Types
// ============================================================================

export interface ChatResponse {
  replyText: string;
  actions?: MessageAction[];
  sessionId: string;
  followupChips?: string[];
  metadata?: Record<string, any>;
}

export interface ApiError {
  error: string;
  message: string;
  statusCode?: number;
  details?: any;
}

// ============================================================================
// Component Props Types
// ============================================================================

export interface MessageBubbleProps {
  message: Message;
}

export interface ProductCardProps {
  product: ProductCard;
  onAddToCart?: (productId: string) => void;
}

export interface MessageInputProps {
  onSend: (message: string) => void;
  isLoading: boolean;
  disabled?: boolean;
}

export interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
}

export interface TypingIndicatorProps {
  show: boolean;
}

export interface WelcomeMessageProps {
  userName?: string;
}
