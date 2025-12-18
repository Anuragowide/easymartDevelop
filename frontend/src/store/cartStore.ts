import { create } from 'zustand';
import { cartApi, type CartItem, type CartResponse } from '@/lib/api';

interface CartStore {
  items: CartItem[];
  itemCount: number;
  total: number;
  isLoading: boolean;
  error: string | null;
  
  addToCart: (productId: string, quantity?: number) => Promise<void>;
  getCart: () => Promise<void>;
  clearError: () => void;
}

export const useCartStore = create<CartStore>((set, get) => ({
  items: [],
  itemCount: 0,
  total: 0,
  isLoading: false,
  error: null,

  addToCart: async (productId: string, quantity: number = 1) => {
    set({ isLoading: true, error: null });
    try {
      const response: CartResponse = await cartApi.addToCart(productId, quantity);
      
      if (response.success) {
        set({
          items: response.cart.items,
          itemCount: response.cart.item_count,
          total: response.cart.total,
          isLoading: false,
        });
      } else {
        throw new Error(response.error || 'Failed to add to cart');
      }
    } catch (error: any) {
      set({ error: error.message, isLoading: false });
      throw error;
    }
  },

  getCart: async () => {
    set({ isLoading: true, error: null });
    try {
      const response: CartResponse = await cartApi.getCart();
      
      if (response.success) {
        set({
          items: response.cart.items,
          itemCount: response.cart.item_count,
          total: response.cart.total,
          isLoading: false,
        });
      }
    } catch (error: any) {
      set({ error: error.message, isLoading: false });
    }
  },

  clearError: () => set({ error: null }),
}));
