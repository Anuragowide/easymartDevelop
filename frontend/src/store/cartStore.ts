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
          
          if (response.success && response.cart) {
            set({
              items: response.cart.items || [],
              itemCount: response.cart.item_count || 0,
              total: response.cart.total || 0,
              isLoading: false,
            });
          } else {
            throw new Error(response.error || 'Failed to add to cart');
          }
        } catch (error: any) {
          const errorMsg = error?.response?.data?.error || error.message || 'Failed to add to cart';
          set({ error: errorMsg, isLoading: false });
          throw new Error(errorMsg);
        }
      },

      increaseQuantity: async (productId: string) => {
        // Optimistic update - update UI immediately
        const currentState = get();
        const itemIndex = currentState.items.findIndex(
          (item) => item.id === productId || item.product_id === productId
        );
        
        if (itemIndex === -1) return;
        
        const currentQty = currentState.items[itemIndex].quantity;
        const newQty = currentQty + 1;
        
        const optimisticItems = [...currentState.items];
        optimisticItems[itemIndex] = {
          ...optimisticItems[itemIndex],
          quantity: newQty,
        };
        
        const optimisticTotal = optimisticItems.reduce(
          (sum, item) => sum + item.price * item.quantity,
          0
        );
        
        // Update UI immediately
        set({
          items: optimisticItems,
          itemCount: optimisticItems.reduce((sum, item) => sum + item.quantity, 0),
          total: optimisticTotal,
        });
        
        // Then sync with backend using 'set' action to avoid debounce
        try {
          const response: CartResponse = await cartApi.updateQuantity(productId, newQty);
          
          if (response.success && response.cart) {
            // Sync with actual backend state
            set({
              items: response.cart.items,
              itemCount: response.cart.item_count,
              total: response.cart.total,
            });
          } else {
            throw new Error(response.error || 'Failed to increase quantity');
          }
        } catch (error: any) {
          // Revert optimistic update on error
          set({ 
            items: currentState.items,
            itemCount: currentState.itemCount,
            total: currentState.total,
            error: error.message 
          });
          throw error;
        }
      },

          decreaseQuantity: async (productId: string) => {
            const currentQty = get().getProductQuantity(productId);
            if (currentQty <= 0) return;

            if (currentQty === 1) {
              return get().removeFromCart(productId);
            }

            // Optimistic update - update UI immediately
            const currentState = get();
            const itemIndex = currentState.items.findIndex(
              (item) => item.id === productId || item.product_id === productId
            );
            
            if (itemIndex === -1) return;
            
            const optimisticItems = [...currentState.items];
            optimisticItems[itemIndex] = {
              ...optimisticItems[itemIndex],
              quantity: optimisticItems[itemIndex].quantity - 1,
            };
            
            const optimisticTotal = optimisticItems.reduce(
              (sum, item) => sum + item.price * item.quantity,
              0
            );
            
            // Update UI immediately
            set({
              items: optimisticItems,
              itemCount: optimisticItems.reduce((sum, item) => sum + item.quantity, 0),
              total: optimisticTotal,
            });

            // Then sync with backend
            try {
              const newQuantity = currentQty - 1;
              const response: CartResponse = await cartApi.updateQuantity(productId, newQuantity);
              
              if (response.success && response.cart) {
                // Sync with actual backend state
                set({
                  items: response.cart.items,
                  itemCount: response.cart.item_count,
                  total: response.cart.total,
                });
              } else {
                throw new Error(response.error || 'Failed to decrease quantity');
              }
            } catch (error: any) {
              // Revert optimistic update on error
              set({ 
                items: currentState.items,
                itemCount: currentState.itemCount,
                total: currentState.total,
                error: error.message 
              });
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
