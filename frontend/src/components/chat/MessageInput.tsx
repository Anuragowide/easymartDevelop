'use client';

import { MessageInputProps } from '@/lib/types';
import { useState, KeyboardEvent } from 'react';
import { useChatStore } from '@/store/chatStore';

interface ExtendedMessageInputProps extends MessageInputProps {
  followupChips?: string[];
}

export function MessageInput({ onSend, isLoading, disabled = false }: ExtendedMessageInputProps) {
  const [input, setInput] = useState('');
  const { followupChips, isStarterChips, clearFollowupChips } = useChatStore();

  const enableFollowupChips = process.env.NEXT_PUBLIC_ENABLE_FOLLOWUP_CHIPS !== 'false';
  const shouldShowChips = isStarterChips || enableFollowupChips;

  const handleSend = () => {
    if (input.trim() && !isLoading) {
      clearFollowupChips(); // Clear chips when user sends a message
      onSend(input.trim());
      setInput('');
    }
  };

  const handleChipClick = (chip: string) => {
    if (!isLoading) {
      clearFollowupChips(); // Clear chips when chip is clicked
      onSend(chip);
    }
  };

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isDisabled = disabled || isLoading;

  return (
    <div className="border-t border-gray-100/50 bg-gradient-to-t from-white via-white to-transparent px-4 py-3">
      {/* Floating Follow-up Chips - Compact & Transparent */}
      {shouldShowChips && followupChips && followupChips.length > 0 && !isLoading && (
        <div className="flex flex-wrap gap-1.5 mb-2 animate-fadeIn">
          {followupChips.map((chip, index) => (
            <button
              key={index}
              onClick={() => handleChipClick(chip)}
              disabled={isDisabled}
              className="px-2.5 py-1 text-xs font-medium 
                         bg-white/70 backdrop-blur-sm
                         text-gray-600 border border-gray-200/60 rounded-full
                         hover:bg-red-50/80 hover:text-red-600 hover:border-red-200/80
                         transition-all duration-200 
                         disabled:opacity-50 disabled:cursor-not-allowed
                         active:scale-95 shadow-sm hover:shadow"
              style={{ 
                animation: `fadeSlideUp 0.3s ease-out ${index * 0.05}s both`
              }}
            >
              {chip}
            </button>
          ))}
        </div>
      )}

      {/* Input Area - Slightly more compact */}
      <div className="flex items-end gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={isLoading ? "AI is thinking..." : "Type your message here..."}
          disabled={isDisabled}
          rows={1}
          className="flex-1 resize-none rounded-2xl border border-gray-200 px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 focus:border-red-400 focus:ring-2 focus:ring-red-100 focus:outline-none disabled:bg-gray-50 disabled:text-gray-400 transition-all bg-gray-50/50"
          style={{ maxHeight: '100px' }}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || isLoading}
          className="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-r from-red-500 to-pink-500 text-white disabled:from-gray-300 disabled:to-gray-400 disabled:cursor-not-allowed hover:shadow-lg transform hover:scale-105 transition-all duration-200 flex items-center justify-center"
          aria-label="Send message"
        >
          {isLoading ? (
            <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
          ) : (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          )}
        </button>
      </div>
    </div>
  );
}
