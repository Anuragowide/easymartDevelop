'use client';

import React, { useState, useEffect } from 'react';
import { ChatButton } from './ChatButton';
import { ChatHeader } from './ChatHeader';
import { ChatWindow } from './ChatWindow';

export const ChatWidget: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  // Close on escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };
    
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen]);

  // Prevent body scroll when chat is open on mobile
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  return (
    <>
      {/* Floating Chat Button */}
      {!isOpen && <ChatButton onClick={() => setIsOpen(true)} />}

      {/* Chat Modal */}
      <div className={`fixed inset-0 z-50 ${isOpen ? 'block' : 'hidden'}`}>
        {/* Backdrop (mobile only) */}
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setIsOpen(false)}
        />

        {/* Chat Container */}
        <div className="fixed bottom-0 right-0 z-50 md:bottom-6 md:right-6 w-full md:w-[500px] h-full md:h-[700px] md:max-h-[90vh] shadow-2xl md:rounded-2xl overflow-hidden animate-in slide-in-from-bottom-4 md:slide-in-from-right-4 duration-300">
          {/* Header */}
          <ChatHeader onClose={() => setIsOpen(false)} />

          {/* Chat Content */}
          <div className="h-[calc(100%-68px)] bg-white">
            <ChatWindow />
          </div>
        </div>
      </div>
    </>
  );
};
