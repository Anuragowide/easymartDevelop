'use client';

import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { CartView } from './CartView';
import { AIWarningBanner } from './AIWarningBanner';
import { useChatStore } from '@/store/chatStore';

export function ChatWindow() {
  const { messages, isLoading, sendMessage, isCartOpen } = useChatStore();

  const handleSendMessage = async (content: string) => {
    await sendMessage(content);
  };

  return (
    <div className="h-full flex flex-col bg-gradient-to-b from-gray-50 to-white relative overflow-hidden">
      {/* AI Warning Banner */}
      <AIWarningBanner />
      
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
