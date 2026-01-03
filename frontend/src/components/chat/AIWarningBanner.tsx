'use client';

import { useState } from 'react';
import { Info, X } from 'lucide-react';

export function AIWarningBanner() {
  const [isVisible, setIsVisible] = useState(true);

  const handleDismiss = () => {
    setIsVisible(false);
  };

  if (!isVisible) return null;

  return (
    <div className="bg-gray-100 border-b border-gray-200 px-4 py-3 flex items-center justify-between">
      <div className="flex items-center gap-3 flex-1">
        <Info className="w-5 h-5 text-gray-600 flex-shrink-0" />
        <p className="text-sm text-gray-700">
Disclaimer: AI-generated responses may be incorrect. Confirm pricing, dimensions, and availability before ordering.        </p>
      </div>
      <button
        onClick={handleDismiss}
        className="ml-4 p-1 hover:bg-gray-200 rounded transition-colors flex-shrink-0"
        aria-label="Dismiss warning"
      >
        <X className="w-5 h-5 text-gray-600" />
      </button>
    </div>
  );
}
