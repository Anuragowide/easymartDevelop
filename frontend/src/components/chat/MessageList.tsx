'use client';

import { useEffect, useRef, useState } from 'react';
import { Message } from '@/lib/types';
import { useCartStore } from '@/store/cartStore';

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
}

export function MessageList({ messages, isLoading }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { addToCart } = useCartStore();
  const [addingToCart, setAddingToCart] = useState<string | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleAddToCart = async (product: any) => {
    setAddingToCart(product.id);
    try {
      await addToCart(product.id, 1);
      // Simple success feedback
      alert(`✅ ${product.title} added to cart!`);
    } catch (error: any) {
      alert(`❌ Failed to add to cart: ${error.message}`);
    } finally {
      setAddingToCart(null);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
      {/* Welcome Message - Removed "Try asking me:" section */}
      {messages.length === 0 && (
        <div className="flex flex-col items-center justify-center h-full text-center px-4">
          <div className="w-24 h-24 bg-gradient-to-br from-red-500 to-pink-500 rounded-full mb-6 flex items-center justify-center shadow-lg">
            <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </div>
          <h3 className="text-3xl font-bold bg-gradient-to-r from-red-600 to-pink-600 bg-clip-text text-transparent mb-3">
            Welcome to EasyMart! 👋
          </h3>
          <p className="text-gray-700 text-lg max-w-md leading-relaxed">
            I'm your AI shopping assistant. I can help you find furniture, answer questions, and manage your cart.
          </p>
        </div>
      )}

      {/* Messages */}
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`max-w-[85%] rounded-2xl px-4 py-3 ${
              message.role === 'user'
                ? 'bg-gradient-to-r from-red-600 to-pink-600 text-white shadow-lg'
                : 'bg-white border-2 border-red-100 text-gray-800 shadow-md'
            }`}
          >
            {/* Message Content */}
            <p className={`text-sm leading-relaxed whitespace-pre-wrap break-words ${
              message.role === 'user' ? 'font-medium' : ''
            }`}>
              {message.content}
            </p>

            {/* Product Cards */}
            {message.actions && message.actions.length > 0 && (
              <div className="mt-4 space-y-3">
                {message.actions.map((action, idx) => {
                  // Handle search_results action type
                  if (action.type === 'search_results' && action.data?.results) {
                    return action.data.results.map((product: any, pIdx: number) => (
                      <div
                        key={`${idx}-${pIdx}-${product.id}`}
                        className="bg-white rounded-xl p-4 border border-gray-200 hover:shadow-lg transition-all"
                      >
                        <div className="flex gap-4">
                          {product.image && (
                            <div className="flex-shrink-0">
                              <img
                                src={product.image}
                                alt={product.title}
                                className="w-24 h-24 object-cover rounded-lg"
                              />
                            </div>
                          )}
                          <div className="flex-1 min-w-0 flex flex-col">
                            <h4 className="font-semibold text-gray-900 text-base mb-2 line-clamp-2">
                              {product.title}
                            </h4>
                            {product.price && (
                              <p className="text-red-600 font-bold text-xl mb-3">
                                USD ${typeof product.price === 'number' ? product.price.toFixed(2) : product.price}
                              </p>
                            )}
                            <div className="flex gap-2 mt-auto">
                              {product.url && (
                                <a
                                  href={product.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="flex-1 text-center text-sm font-semibold text-white bg-gradient-to-r from-red-600 to-pink-600 px-4 py-2 rounded-lg hover:from-red-700 hover:to-pink-700 transition-all"
                                >
                                  View Details
                                </a>
                              )}
                              <button
                                onClick={() => handleAddToCart(product)}
                                disabled={addingToCart === product.id}
                                className={`flex-1 text-center text-sm font-semibold text-red-600 bg-white border-2 border-red-600 px-4 py-2 rounded-lg hover:bg-red-50 transition-all ${
                                  addingToCart === product.id ? 'opacity-50 cursor-wait' : ''
                                }`}
                              >
                                {addingToCart === product.id ? 'Adding...' : 'Add to Cart'}
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                    ));
                  }
                  return null;
                })}
              </div>
            )}

            {/* Timestamp */}
            <p className={`text-xs mt-2 ${
              message.role === 'user' ? 'text-pink-100' : 'text-gray-500'
            }`}>
              {new Date(message.timestamp).toLocaleTimeString([], { 
                hour: '2-digit', 
                minute: '2-digit' 
              })}
            </p>
          </div>
        </div>
      ))}

      {/* Loading Indicator */}
      {isLoading && (
        <div className="flex justify-start">
          <div className="bg-white border-2 border-red-100 rounded-2xl px-5 py-4 shadow-md">
            <div className="flex items-center gap-3">
              <div className="flex gap-1">
                <span className="w-2.5 h-2.5 bg-red-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                <span className="w-2.5 h-2.5 bg-pink-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                <span className="w-2.5 h-2.5 bg-red-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
              </div>
              <span className="text-sm text-gray-700 font-medium">Thinking...</span>
            </div>
          </div>
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
}
