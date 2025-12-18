'use client';

import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { useChatStore } from '@/store/chatStore';

export function ChatWindow() {
  const { messages, isLoading, sendMessage } = useChatStore();

  const handleSendMessage = async (content: string) => {
    await sendMessage(content);
  };

  return (
    <div className="h-full flex flex-col bg-gradient-to-b from-gray-50 to-white">
      {/* Messages */}
      <MessageList messages={messages} isLoading={isLoading} />

      {/* Input */}
      <MessageInput 
        onSend={handleSendMessage} 
        isLoading={isLoading} 
      />
    </div>
  );
}
