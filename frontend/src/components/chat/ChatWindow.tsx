'use client';

import { useEffect } from 'react';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { CartView } from './CartView';
import { AIWarningBanner } from './AIWarningBanner';
import { ContextIndicator } from './ContextIndicator';
import { useChatStore } from '@/store/chatStore';

export function ChatWindow() {
  const { messages, isLoading, sendMessage, isCartOpen, currentContext, initializeChat } = useChatStore();

  // Initialize chat with welcome message on mount
  useEffect(() => {
    initializeChat();
  }, [initializeChat]);

  const handleSendMessage = async (content: string) => {
    await sendMessage(content);
  };

  return (
    <div className="h-full flex flex-col bg-gradient-to-b from-gray-50 to-white relative overflow-hidden">
      {/* AI Warning Banner */}
      <AIWarningBanner />
      
      {/* Context Indicator */}
      {currentContext && (
        <ContextIndicator
          topic={currentContext.topic}
          confidence={currentContext.confidence}
          intent={currentContext.intent}
          preferences={currentContext.preferences}
        />
      )}
      
      {/* Messages */}
      <MessageList messages={messages} isLoading={isLoading} />

      {/* Cart View Overlay */}
      {isCartOpen && <CartView />}

      {/* Input */}
      {!isCartOpen && (
        <MessageInput 
          onSend={handleSendMessage} 
          isLoading={isLoading} 
        />
      )}
    </div>
  );
}
