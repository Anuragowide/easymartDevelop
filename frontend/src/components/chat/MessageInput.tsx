'use client';

import { MessageInputProps } from '@/lib/types';
import { useState, KeyboardEvent, useRef, useEffect } from 'react';

export function MessageInput({ onSend, isLoading, disabled = false }: MessageInputProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmedMessage = message.trim();
    if (trimmedMessage && !isLoading && !disabled) {
      onSend(trimmedMessage);
      setMessage('');
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Send on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`;
    }
  }, [message]);

  const isDisabled = disabled || isLoading;
  const canSend = message.trim().length > 0 && !isDisabled;

  return (
    <div className="relative px-8 py-6 bg-gradient-to-t from-black via-zinc-900 to-transparent">
      <div className="max-w-4xl mx-auto">
        {/* Main input container with gradient border */}
        <div className="relative group">
          {/* Animated gradient border */}
          <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 rounded-3xl opacity-20 group-hover:opacity-40 blur transition duration-300" />
          
          <div className="relative bg-gradient-to-br from-zinc-900 to-zinc-800 rounded-3xl border border-zinc-700/50">
            <div className="flex items-center gap-3 p-4">
              {/* Attach button */}
              <button
                className="flex-shrink-0 p-2.5 text-gray-400 hover:text-white hover:bg-zinc-700/50 rounded-xl transition-all duration-200"
                title="Attach file"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                </svg>
              </button>

              {/* Textarea */}
              <div className="flex-1">
                <textarea
                  ref={textareaRef}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={isLoading ? "AI is thinking..." : "Type your message here..."}
                  disabled={isDisabled}
                  rows={1}
                  className="w-full bg-transparent text-white placeholder-gray-500 resize-none focus:outline-none disabled:cursor-not-allowed text-base leading-relaxed"
                  style={{ maxHeight: '150px' }}
                />
              </div>

              {/* Send Button with gradient */}
              <button
                onClick={handleSend}
                disabled={!canSend}
                className={`flex-shrink-0 w-11 h-11 rounded-xl flex items-center justify-center transition-all duration-300 ${
                  canSend
                    ? 'bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 hover:shadow-lg hover:shadow-purple-500/50 text-white transform hover:scale-105'
                    : 'bg-zinc-800 text-zinc-600 cursor-not-allowed'
                }`}
                title="Send message"
              >
                {isLoading ? (
                  <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        </div>
        
        {/* Help text */}
        <div className="mt-3 text-center text-xs text-gray-500">
          Press <kbd className="px-2 py-0.5 bg-zinc-800 border border-zinc-700 rounded font-mono">Enter</kbd> to send • 
          <kbd className="px-2 py-0.5 bg-zinc-800 border border-zinc-700 rounded font-mono">Shift + Enter</kbd> for new line
        </div>
      </div>
    </div>
  );
}
