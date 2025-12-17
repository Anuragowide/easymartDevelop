import { MessageBubbleProps, ProductCard as ProductCardType, SearchResultsAction } from '@/lib/types';
import { ProductCard } from './ProductCard';
import { format } from 'date-fns';

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const time = format(new Date(message.timestamp), 'h:mm a');

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
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      </div>
    );
  };

  // Render product card action
  const renderProductCard = (product: ProductCardType) => {
    return (
      <div className="mt-3">
        <ProductCard product={product} />
      </div>
    );
  };

  return (
    <div className={`flex items-start gap-4 px-8 py-5 max-w-4xl mx-auto ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar with gradient */}
      <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center shadow-lg ${
        isUser 
          ? 'bg-gradient-to-br from-gray-600 to-gray-800' 
          : 'bg-gradient-to-br from-blue-500 via-purple-500 to-pink-500'
      }`}>
        {isUser ? (
          <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
          </svg>
        ) : (
          <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        )}
      </div>

      {/* Message Content */}
      <div className={`flex-1 ${isUser ? 'flex flex-col items-end' : ''}`}>
        <div className={`inline-block rounded-2xl px-6 py-3.5 max-w-2xl shadow-lg ${
          isUser 
            ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white' 
            : 'bg-gradient-to-br from-zinc-800 to-zinc-900 border border-zinc-700/50 text-white'
        }`}>
          <p className="text-[15px] leading-relaxed whitespace-pre-wrap break-words">{message.content}</p>
        </div>

        {/* Timestamp */}
        <div className={`mt-2 px-2 text-xs text-gray-500 ${isUser ? 'text-right' : ''}`}>
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
