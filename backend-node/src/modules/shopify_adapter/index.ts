// Shopify Adapter - Public API
// Provides a clean interface for interacting with Shopify

export { shopifyClient } from "./client";

export {
  getProductDetails,
  searchProducts,
  getAllProducts,
  getProductByHandle,
  type ShopifyProduct,
} from "./products";

export {
  addToCart,
  updateCartItem,
  getCart,
  clearCart,
  removeFromCart,
  type CartItem,
  type Cart,
} from "./cart";
