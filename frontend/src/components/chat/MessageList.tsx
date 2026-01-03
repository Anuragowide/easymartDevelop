'use client';

import { useEffect, useRef, useState } from 'react';
import { Message } from '@/lib/types';
import { useCartStore } from '@/store/cartStore';

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
}

// Simple markdown parser for bold text and bullet points
function parseMarkdown(text: string): React.ReactNode {
  if (!text) return text;
  
  // Pre-process: fix malformed bold markers (*text** -> **text**)
  let cleanedText = text
    .replace(/(?<!\*)\*([^*\n]+)\*\*/g, '**$1**')  // *text** -> **text**
    .replace(/\*\*([^*\n]+)\*(?!\*)/g, '**$1**')   // **text* -> **text**
    .replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, '**$1**'); // *text* -> **text**
  
  // Split by lines to handle bullet points
  const lines = cleanedText.split('\n');
  
  return lines.map((line, lineIndex) => {
    // Check if line is a bullet point (•, -, or * followed by space)
    const bulletMatch = line.match(/^[\s]*[•\-]\s+(.*)$|^[\s]*\*\s+(.*)$/);
    const isBullet = bulletMatch !== null;
    const lineContent = isBullet ? (bulletMatch[1] || bulletMatch[2]) : line;
    
    // Parse bold text (**text**)
    const parts = lineContent.split(/(\*\*[^*]+\*\*)/g);
    
    const parsedContent = parts.map((part, partIndex) => {
      // Check for bold
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={partIndex} className="font-semibold">{part.slice(2, -2)}</strong>;
      }
      return part;
    });
    
    if (isBullet) {
      return (
        <div key={lineIndex} className="flex items-start gap-2 ml-2">
          <span className="text-red-500 mt-0.5">•</span>
          <span>{parsedContent}</span>
        </div>
      );
    }
    
    // Return line with line break (except for last line)
    return (
      <span key={lineIndex}>
        {parsedContent}
        {lineIndex < lines.length - 1 && <br />}
      </span>
    );
  });
}

export function MessageList({ messages, isLoading }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { addToCart, increaseQuantity, decreaseQuantity, getProductQuantity } = useCartStore();
  const [loadingProduct, setLoadingProduct] = useState<string | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleAddToCart = async (product: any) => {
    setLoadingProduct(product.id);
    try {
      await addToCart(product.id, 1);
    } catch (error: any) {
      alert(`❌ Failed to add to cart: ${error.message}`);
    } finally {
      setLoadingProduct(null);
    }
  };

  const handleIncrease = async (product: any) => {
    const currentQty = getProductQuantity(product.id);
    const stock = product.inventory_quantity || 0;
    
    // Check stock limit
    if (stock > 0 && currentQty >= stock) {
      alert(`⚠️ Only ${stock} in stock`);
      return;
    }

    setLoadingProduct(product.id);
    try {
      await increaseQuantity(product.id);
    } catch (error: any) {
      alert(`❌ Failed to increase quantity: ${error.message}`);
    } finally {
      setLoadingProduct(null);
    }
  };

  const handleDecrease = async (product: any) => {
    setLoadingProduct(product.id);
    try {
      await decreaseQuantity(product.id);
    } catch (error: any) {
      alert(`❌ Failed to decrease quantity: ${error.message}`);
    } finally {
      setLoadingProduct(null);
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
            <div className={`text-sm leading-relaxed whitespace-pre-wrap break-words ${
              message.role === 'user' ? 'font-medium' : ''
            }`}>
              {parseMarkdown(message.content)}
            </div>

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
                            
                            {/* Stock info */}
                            {product.inventory_quantity !== undefined && (
                              <p className="text-sm text-gray-500 mb-2">
                                {product.inventory_quantity > 0 
                                  ? `${product.inventory_quantity} in stock` 
                                  : 'Out of stock'}
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
                              
                              {/* Quantity Counter or Add to Cart Button */}
                              {(() => {
                                const quantity = getProductQuantity(product.id);
                                const isLoading = loadingProduct === product.id;
                                
                                if (quantity > 0) {
                                  // Show quantity counter
                                  return (
                                    <div className="flex-1 flex items-center justify-center gap-1 border-2 border-gray-300 rounded-lg p-1">
                                      <button
                                        onClick={() => handleDecrease(product)}
                                        disabled={isLoading}
                                        className="w-8 h-8 flex items-center justify-center text-gray-700 hover:bg-gray-100 rounded disabled:opacity-50 disabled:cursor-not-allowed font-bold text-lg"
                                      >
                                        −
                                      </button>
                                      <span className="w-10 text-center font-bold text-gray-900">
                                        {quantity}
                                      </span>
                                      <button
                                        onClick={() => handleIncrease(product)}
                                        disabled={isLoading}
                                        className="w-8 h-8 flex items-center justify-center text-gray-700 hover:bg-gray-100 rounded disabled:opacity-50 disabled:cursor-not-allowed font-bold text-lg"
                                      >
                                        +
                                      </button>
                                    </div>
                                  );
                                } else {
                                  // Show Add to Cart button
                                  return (
                                    <button
                                      onClick={() => handleAddToCart(product)}
                                      disabled={isLoading || product.inventory_quantity === 0}
                                      className="flex-1 text-center text-sm font-semibold text-red-600 bg-white border-2 border-red-600 px-4 py-2 rounded-lg hover:bg-red-50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                      {isLoading ? 'Adding...' : product.inventory_quantity === 0 ? 'Out of Stock' : 'Add to Cart'}
                                    </button>
                                  );
                                }
                              })()}
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
