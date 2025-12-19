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
        console.log('🔍 [DECREASE] Current quantity:', currentQty, 'for product:', productId);
        console.log('🔍 [DECREASE] Current items:', get().items);
        
        if (currentQty <= 0) return;

        set({ isLoading: true, error: null });
        try {
          // If quantity is 1, remove from cart (set to 0)
          const newQuantity = currentQty - 1;
          console.log('📤 [DECREASE] Sending to API - newQuantity:', newQuantity);
          
          const response: CartResponse = await cartApi.updateQuantity(productId, newQuantity);
          console.log('📥 [DECREASE] Full response:', JSON.stringify(response, null, 2));
          
          if (response.success) {
            // Normalize items to ensure both id and product_id fields exist
            const normalizedItems = response.cart.items.map(item => ({
              ...item,
              id: item.id || item.product_id || '',
              product_id: item.product_id || item.id || ''
            }));
            
            console.log('✅ [DECREASE] Normalized items:', normalizedItems);
            console.log('✅ [DECREASE] Setting state with', normalizedItems.length, 'items');
            
            set({
              items: normalizedItems,
              itemCount: response.cart.item_count,
              total: response.cart.total,
              isLoading: false,
            });
            
            const verifyQty = get().getProductQuantity(productId);
            const verifyItems = get().items;
            console.log('🔍 [DECREASE] Verify - items:', verifyItems);
            console.log('🔍 [DECREASE] Verify - quantity:', verifyQty);
          } else {
            console.error('❌ [DECREASE] API returned error:', response.error);
            throw new Error(response.error || 'Failed to decrease quantity');
          }
        } catch (error: any) {
          console.error('❌ [DECREASE] Exception:', error);
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
        const item = get().items.find((item) => item.product_id === productId || item.id === productId);
        return item?.quantity || 0;
      },
    }),
    {
      name: 'easymart-cart-storage',
      storage: createJSONStorage(() => localStorage),
    }
  )
);
