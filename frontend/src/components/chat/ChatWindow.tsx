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
    <div className="h-full flex flex-col max-w-5xl mx-auto bg-black relative overflow-hidden">
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
