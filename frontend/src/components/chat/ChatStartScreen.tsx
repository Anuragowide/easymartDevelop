'use client';

import { useChatStore } from '@/store/chatStore';
import { useCartStore } from '@/store/cartStore';

interface ChatStartScreenProps {
  onStartNew: () => void;
  onContinue: () => void;
  previousMessageCount: number;
  lastMessagePreview: string;
}

export function ChatStartScreen({ 
  onStartNew, 
  onContinue, 
  previousMessageCount,
  lastMessagePreview 
}: ChatStartScreenProps) {
  const cartItems = useCartStore((state) => state.items);
  const cartCount = cartItems.length;

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 py-8 bg-gradient-to-b from-gray-50 to-white">
      {/* Logo/Icon */}
      <div className="w-20 h-20 bg-gradient-to-br from-red-500 to-pink-500 rounded-full mb-6 flex items-center justify-center shadow-lg">
        <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      </div>

      {/* Welcome Text */}
      <h2 className="text-2xl font-bold bg-gradient-to-r from-red-600 to-pink-600 bg-clip-text text-transparent mb-2">
        Welcome Back! 👋
      </h2>
      <p className="text-gray-600 text-center mb-8 max-w-xs">
        How would you like to continue?
      </p>

      {/* Options */}
      <div className="w-full max-w-sm space-y-4">
        {/* Continue Previous Chat */}
        <button
          onClick={onContinue}
          className="w-full bg-white border-2 border-red-200 rounded-xl p-4 hover:border-red-400 hover:shadow-md transition-all text-left group"
        >
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0 group-hover:bg-red-200 transition-colors">
              <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-gray-900 mb-1">Continue Previous Chat</h3>
              <p className="text-sm text-gray-500 mb-2">
                {previousMessageCount} messages • {cartCount > 0 ? `${cartCount} items in cart` : 'No items in cart'}
              </p>
              <p className="text-xs text-gray-400 truncate italic">
                "{lastMessagePreview}"
              </p>
            </div>
            <svg className="w-5 h-5 text-gray-400 group-hover:text-red-500 transition-colors flex-shrink-0 mt-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </button>

        {/* Start New Chat */}
        <button
          onClick={onStartNew}
          className="w-full bg-gradient-to-r from-red-600 to-pink-600 text-white rounded-xl p-4 hover:from-red-700 hover:to-pink-700 hover:shadow-lg transition-all text-left group"
        >
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center flex-shrink-0">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
            </div>
            <div className="flex-1">
              <h3 className="font-semibold mb-1">Start Fresh</h3>
              <p className="text-sm text-white/80">
                Begin a new conversation
              </p>
            </div>
            <svg className="w-5 h-5 text-white/60 group-hover:text-white transition-colors flex-shrink-0 mt-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </button>
      </div>

      {/* Quick Actions */}
      <div className="mt-8 pt-6 border-t border-gray-200 w-full max-w-sm">
        <p className="text-xs text-gray-500 text-center mb-3">Quick start suggestions</p>
        <div className="flex flex-wrap gap-2 justify-center">
          {["Show me chairs", "Browse sofas", "View desks"].map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => {
                onStartNew();
                // Small delay to let the new chat initialize, then send message
                setTimeout(() => {
                  useChatStore.getState().sendMessage(suggestion);
                }, 100);
              }}
              className="px-3 py-1.5 bg-gray-100 hover:bg-red-100 text-gray-700 hover:text-red-700 rounded-full text-sm transition-colors"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
