import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { cartApi, type CartItem, type CartResponse } from '@/lib/api';

interface CartStore {
  items: CartItem[];
  itemCount: number;
  total: number;
  isLoading: boolean;
  error: string | null;
  
    // Actions
    addToCart: (productId: string, quantity?: number) => Promise<void>;
    increaseQuantity: (productId: string) => Promise<void>;
    decreaseQuantity: (productId: string) => Promise<void>;
    removeFromCart: (productId: string) => Promise<void>;
    clearCart: () => Promise<void>;
    getCart: () => Promise<void>;
    clearError: () => void;

  
  // Helpers
  getProductQuantity: (productId: string) => number;
}

export const useCartStore = create<CartStore>()(
  persist(
    (set, get) => ({
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

      increaseQuantity: async (productId: string) => {
        set({ isLoading: true, error: null });
        try {
          const response: CartResponse = await cartApi.addToCart(productId, 1);
          
          if (response.success) {
            set({
              items: response.cart.items,
              itemCount: response.cart.item_count,
              total: response.cart.total,
              isLoading: false,
            });
          } else {
            throw new Error(response.error || 'Failed to increase quantity');
          }
        } catch (error: any) {
          set({ error: error.message, isLoading: false });
          throw error;
        }
      },

          decreaseQuantity: async (productId: string) => {
            const currentQty = get().getProductQuantity(productId);
            if (currentQty <= 0) return;

            if (currentQty === 1) {
              return get().removeFromCart(productId);
            }

            set({ isLoading: true, error: null });
            try {
              const newQuantity = currentQty - 1;
              const response: CartResponse = await cartApi.updateQuantity(productId, newQuantity);
              
              if (response.success) {
                set({
                  items: response.cart.items,
                  itemCount: response.cart.item_count,
                  total: response.cart.total,
                  isLoading: false,
                });
              } else {
                throw new Error(response.error || 'Failed to decrease quantity');
              }
            } catch (error: any) {
              set({ error: error.message, isLoading: false });
              throw error;
            }
          },

            removeFromCart: async (productId: string) => {
              set({ isLoading: true, error: null });
              try {
                const response: CartResponse = await cartApi.removeFromCart(productId);
                
                if (response.success) {
                  set({
                    items: response.cart.items,
                    itemCount: response.cart.item_count,
                    total: response.cart.total,
                    isLoading: false,
                  });
                } else {
                  throw new Error(response.error || 'Failed to remove from cart');
                }
              } catch (error: any) {
                set({ error: error.message, isLoading: false });
                throw error;
              }
            },

            clearCart: async () => {
              set({ isLoading: true, error: null });
              try {
                const response: CartResponse = await cartApi.clearCart();
                
                if (response.success) {
                  set({
                    items: [],
                    itemCount: 0,
                    total: 0,
                    isLoading: false,
                  });
                } else {
                  throw new Error(response.error || 'Failed to clear cart');
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

        getProductQuantity: (productId: string): number => {
          if (!productId) return 0;
          const items = get().items;
          const item = items.find((item) => 
            String(item.product_id) === String(productId) || 
            String(item.id) === String(productId)
          );
          return item?.quantity || 0;
        },

    }),
    {
      name: 'easymart-cart-storage',
      storage: createJSONStorage(() => localStorage),
    }
  )
);
