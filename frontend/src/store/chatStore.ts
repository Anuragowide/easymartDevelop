import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { chatApi, type ChatResponse } from '@/lib/api';
import { generateUUID } from '@/lib/utils';
import { Message } from '@/lib/types';

interface ChatState {
  messages: Message[];
  sessionId: string;
  isLoading: boolean;
  isCartOpen: boolean;
  error: string | null;

  // Actions
  sendMessage: (text: string) => Promise<void>;
  addMessage: (message: Message) => void;
  clearMessages: () => void;
  setError: (error: string | null) => void;
  setCartOpen: (open: boolean) => void;
  toggleCart: () => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      messages: [],
      sessionId: generateUUID(),
      isLoading: false,
      isCartOpen: false,
      error: null,

      setCartOpen: (open: boolean) => set({ isCartOpen: open }),
      toggleCart: () => set((state) => ({ isCartOpen: !state.isCartOpen })),

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

          set((state) => ({
            messages: [...state.messages, assistantMessage],
            isLoading: false,
          }));
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
        set({ messages: [], sessionId: generateUUID(), error: null });
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
      }),
    }
  )
);
