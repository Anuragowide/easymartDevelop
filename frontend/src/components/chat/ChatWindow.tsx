'use client';

import { useEffect } from 'react';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { CartView } from './CartView';
import { AIWarningBanner } from './AIWarningBanner';
import { ContextIndicator } from './ContextIndicator';
import { ChatStartScreen } from './ChatStartScreen';
import { useChatStore } from '@/store/chatStore';

export function ChatWindow() {
  const { 
    messages, 
    isLoading, 
    sendMessage, 
    isCartOpen, 
    currentContext, 
    initializeChat,
    showStartScreen,
    startNewChat,
    continuePreviousChat
  } = useChatStore();

  // Initialize chat on mount
  useEffect(() => {
    initializeChat();
  }, [initializeChat]);

  const handleSendMessage = async (content: string) => {
    await sendMessage(content);
  };

  // Get last message preview for start screen
  const getLastMessagePreview = () => {
    const userMessages = messages.filter(m => m.role === 'user');
    if (userMessages.length > 0) {
      const lastMsg = userMessages[userMessages.length - 1].content;
      return lastMsg.length > 50 ? lastMsg.substring(0, 50) + '...' : lastMsg;
    }
    return 'No previous messages';
  };

  // Show start screen if there's a previous session
  if (showStartScreen && messages.some(m => m.role === 'user')) {
    return (
      <div className="h-full flex flex-col bg-gradient-to-b from-gray-50 to-white relative overflow-hidden">
        <AIWarningBanner />
        <ChatStartScreen
          onStartNew={startNewChat}
          onContinue={continuePreviousChat}
          previousMessageCount={messages.length}
          lastMessagePreview={getLastMessagePreview()}
        />
      </div>
    );
  }

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
