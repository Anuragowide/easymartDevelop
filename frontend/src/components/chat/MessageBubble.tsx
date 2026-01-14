import { MessageBubbleProps, ProductCard as ProductCardType, SearchResultsAction } from '@/lib/types';
import { ProductCard } from './ProductCard';
import { ComparisonTable, parseComparisonFromMessage } from './ComparisonTable';
import { format } from 'date-fns';
import { useCartStore } from '@/store/cartStore';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const time = format(new Date(message.timestamp), 'h:mm a');
  const { addToCart } = useCartStore();

  const handleAddToCart = async (productId: string): Promise<void> => {
    try {
      await addToCart(productId);
      // Success is handled by ProductCard's "Added" state
    } catch (error) {
      console.error('Failed to add to cart:', error);
      // Re-throw so ProductCard can handle the error state
      throw error;
    }
  };

  // Render search results action
  const renderSearchResults = (action: SearchResultsAction) => {
    if (action.data.results.length === 0) {
      return (
        <div className="mt-3 p-4 bg-gray-50 rounded-lg border border-gray-200">
          <p className="text-gray-600">No products found matching "{action.data.query}"</p>
        </div>
      );
    }

    return (
      <div className="mt-3 space-y-3">
        {/* Remove "Found X products" label - cards speak for themselves */}
        <div className="grid grid-cols-1 gap-3">
          {action.data.results.map((product) => (
            <ProductCard 
              key={product.id} 
              product={product} 
              onAddToCart={handleAddToCart}
            />
          ))}
        </div>
      </div>
    );
  };

  // Render product card action
  const renderProductCard = (product: ProductCardType) => {
    return (
      <div className="mt-3">
        <ProductCard 
          product={product} 
          onAddToCart={handleAddToCart}
        />
      </div>
    );
  };

  return (
    <div className={`flex items-start gap-3 px-4 py-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold ${
        isUser 
          ? 'bg-gray-200 text-gray-700' 
          : 'bg-gradient-to-br from-red-500 to-red-600 text-white'
      }`}>
        {isUser ? 'U' : 'E'}
      </div>

      {/* Message Content */}
      <div className={`flex-1 ${isUser ? 'flex flex-col items-end' : ''}`}>
        <div className={`inline-block rounded-2xl px-4 py-2.5 max-w-[85%] ${
          isUser 
            ? 'bg-red-500 text-white rounded-br-sm' 
            : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm shadow-sm'
        }`}>
          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">{message.content}</p>
          ) : (
            <div className="text-sm leading-relaxed">
              {(() => {
                // Check if this is a comparison message
                const parsed = parseComparisonFromMessage(message.content);
                
                if (parsed.hasComparison && parsed.comparison) {
                  return (
                    <div>
                      {/* Header */}
                      <p className="font-semibold text-gray-900 mb-2">Comparison Summary:</p>
                      
                      {/* Render beautiful comparison table */}
                      <ComparisonTable
                        product1Name={parsed.comparison.product1Name}
                        product2Name={parsed.comparison.product2Name}
                        rows={parsed.comparison.rows}
                        recommendation={parsed.recommendation}
                      />
                    </div>
                  );
                }
                
                // Regular markdown rendering for non-comparison messages
                return (
                  <div className="prose prose-sm max-w-none prose-headings:mt-3 prose-headings:mb-2 prose-p:my-1 prose-ul:my-1 prose-li:my-0.5">
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm]}
                      components={{
                        p: ({ node, ...props }) => (
                          <p className="my-1 text-gray-800" {...props} />
                        ),
                        strong: ({ node, ...props }) => (
                          <strong className="font-semibold text-gray-900" {...props} />
                        ),
                        ul: ({ node, ...props }) => (
                          <ul className="list-disc list-inside my-2 space-y-1.5" {...props} />
                        ),
                        li: ({ node, ...props }) => (
                          <li className="text-sm text-gray-700" {...props} />
                        ),
                      }}
                    >
                      {message.content}
                    </ReactMarkdown>
                  </div>
                );
              })()}
            </div>
          )}
        </div>

        {/* Timestamp */}
        <div className={`mt-1 px-1 text-xs text-gray-400 ${isUser ? 'text-right' : ''}`}>
          {time}
        </div>

        {/* Actions (only for assistant messages) */}
        {!isUser && message.actions && message.actions.length > 0 && (
          <div className="w-full">
            {message.actions.map((action, idx) => {
              if (action.type === 'search_results') {
                return <div key={idx}>{renderSearchResults(action as SearchResultsAction)}</div>;
              }
              if (action.type === 'product_card') {
                return <div key={idx}>{renderProductCard(action.data)}</div>;
              }
              return null;
            })}
          </div>
        )}
      </div>
    </div>
  );
}
