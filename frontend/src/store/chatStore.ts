import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { chatApi, type ChatResponse } from '@/lib/api';
import { generateUUID } from '@/lib/utils';
import { Message } from '@/lib/types';

interface ConversationContext {
  topic: string;
  intent: string;
  confidence: number;
  preferences?: Record<string, any>;
}

interface ChatState {
  messages: Message[];
  sessionId: string;
  isLoading: boolean;
  isCartOpen: boolean;
  error: string | null;
  currentContext: ConversationContext | null;
  followupChips: string[];
  hasInitialized: boolean;

  // Actions
  sendMessage: (text: string) => Promise<void>;
  addMessage: (message: Message) => void;
  clearMessages: () => void;
  setError: (error: string | null) => void;
  setCartOpen: (open: boolean) => void;
  toggleCart: () => void;
  clearFollowupChips: () => void;
  initializeChat: () => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      messages: [],
      sessionId: generateUUID(),
      isLoading: false,
      isCartOpen: false,
      error: null,
      currentContext: null,
      followupChips: [],
      hasInitialized: false,

      setCartOpen: (open: boolean) => set({ isCartOpen: open }),
      toggleCart: () => set((state) => ({ isCartOpen: !state.isCartOpen })),
      clearFollowupChips: () => set({ followupChips: [] }),

      initializeChat: () => {
        const { messages, hasInitialized } = get();
        
        // Only initialize once per session and if no messages exist
        if (hasInitialized || messages.length > 0) return;
        
        const welcomeMessage: Message = {
          id: generateUUID(),
          role: 'assistant',
          content: "Welcome to EasyMart! 👋 I'm your AI shopping assistant. I can help you find furniture, answer questions about products, and manage your cart. What are you looking for today?",
          timestamp: new Date().toISOString(),
        };
        
        set({
          messages: [welcomeMessage],
          hasInitialized: true,
          followupChips: ["Show me office chairs", "Browse sofas", "I need a desk"],
        });
      },

      sendMessage: async (text: string) => {
        const { sessionId, messages } = get();

        // Add user message
        const userMessage: Message = {
          id: generateUUID(),
          role: 'user',
          content: text,
          timestamp: new Date().toISOString(),
        };

        set({
          messages: [...messages, userMessage],
          isLoading: true,
          error: null,
        });

        try {
          // Call API
          const response: ChatResponse = await chatApi.sendMessage(text, sessionId);

          // Check for session reset signal
          if (response.metadata?.reset_session) {
            get().clearMessages(); // Generates new session ID and clears history

            // Add the reset confirmation as the first message of the new session
            const resetMessage: Message = {
              id: generateUUID(),
              role: 'assistant',
              content: response.replyText,
              timestamp: new Date().toISOString(),
            };

            set({
              messages: [resetMessage],
              isLoading: false
            });
            return;
          }

          // Add assistant message
          const assistantMessage: Message = {
            id: generateUUID(),
            role: 'assistant',
            content: response.replyText,
            timestamp: new Date().toISOString(),
            actions: response.actions,
          };

          // Update context from metadata
          const context = response.metadata?.context ? {
            topic: response.metadata.context.topic,
            intent: response.metadata.context.intent,
            confidence: response.metadata.context.confidence,
            preferences: response.metadata.context.preferences
          } : null;

          // Get followup chips from response
          const followupChips = response.followupChips || [];

          set((state) => ({
            messages: [...state.messages, assistantMessage],
            isLoading: false,
            currentContext: context,
            followupChips: followupChips,
          }));
          
            // Always refresh cart after chat messages (in case items were added via chat)
            const { useCartStore } = await import('./cartStore');
            const cartStore = useCartStore.getState();
            
            // Process actions (e.g., search_results, add_to_cart, remove_from_cart, view_cart)
            if (response.actions && Array.isArray(response.actions)) {
              for (const action of response.actions) {
                if (action.type === 'add_to_cart' || action.type === 'remove_from_cart') {
                  // DON'T call cartStore.addToCart here because it was already added in the backend session
                  // Just refresh the local cart state to stay in sync
                  console.log(`[CHAT] Cart action detected: ${action.type}. Syncing cart...`);
                  await cartStore.getCart();
                } else if (action.type === 'clear_cart') {
                  console.log('[CHAT] Executing clear_cart');
                  await cartStore.clearCart();
                } else if (action.type === 'view_cart') {
                  console.log('[CHAT] Executing view_cart');
                  set({ isCartOpen: true });
                }
              }
            }

              // Always refresh cart after any assistant message to ensure UI is in sync
              // Even if no explicit action was returned, the assistant might have performed one
              // Increased timeout and added multiple syncs for robustness
              setTimeout(() => cartStore.getCart(), 300);
              setTimeout(() => cartStore.getCart(), 1500);
              setTimeout(() => cartStore.getCart(), 3000);



        } catch (error: any) {
          const errorMessage = error.response?.data?.message || error.message || 'Failed to send message';

          set({
            isLoading: false,
            error: errorMessage,
          });

          // Add error message to chat
          const errorMsg: Message = {
            id: generateUUID(),
            role: 'assistant',
            content: `Sorry, I encountered an error: ${errorMessage}`,
            timestamp: new Date().toISOString(),
          };

          set((state) => ({
            messages: [...state.messages, errorMsg],
          }));
        }
      },

      addMessage: (message: Message) => {
        set((state) => ({
          messages: [...state.messages, message],
        }));
      },

      clearMessages: () => {
        set({ messages: [], sessionId: generateUUID(), error: null, currentContext: null, hasInitialized: false, followupChips: [] });
      },

      setError: (error: string | null) => {
        set({ error });
      },
    }),
    {
      name: 'easymart-chat-storage',
      partialize: (state) => ({
        messages: state.messages,
        sessionId: state.sessionId,
        hasInitialized: state.hasInitialized,
      }),
    }
  )
);
