import { TypingIndicatorProps } from '@/lib/types';

export function TypingIndicator({ show }: TypingIndicatorProps) {
  if (!show) return null;

  return (
    <div className="flex items-start gap-3 px-4 py-3">
      <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-br from-red-500 to-red-600 rounded-full flex items-center justify-center text-xs font-semibold text-white">
        E
      </div>
      <div className="flex-1">
        <div className="inline-block bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-2.5 shadow-sm">
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
        </div>
        <div className="mt-1 px-1 text-xs text-gray-400">
          Assistant is typing...
        </div>
      </div>
    </div>
  );
}
