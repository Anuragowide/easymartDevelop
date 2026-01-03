'use client';

interface ContextIndicatorProps {
  topic: string;
  confidence: number;
  intent?: string;
  preferences?: Record<string, any>;
}

export function ContextIndicator({ topic, confidence, intent, preferences }: ContextIndicatorProps) {
  // Don't show for general/low confidence
  if (topic === 'general' || confidence < 0.4) {
    return null;
  }

  const getTopicIcon = (topic: string) => {
    const icons: Record<string, string> = {
      products: '🛍️',
      cart: '🛒',
      orders: '📦',
      payment: '💳',
      shipping: '🚚',
      returns: '↩️',
      support: '💬',
      recommendations: '⭐',
    };
    return icons[topic] || '📋';
  };

  const getTopicColor = (topic: string) => {
    const colors: Record<string, string> = {
      products: 'bg-blue-50 text-blue-700 border-blue-200',
      cart: 'bg-green-50 text-green-700 border-green-200',
      orders: 'bg-purple-50 text-purple-700 border-purple-200',
      payment: 'bg-yellow-50 text-yellow-700 border-yellow-200',
      shipping: 'bg-indigo-50 text-indigo-700 border-indigo-200',
      returns: 'bg-orange-50 text-orange-700 border-orange-200',
      support: 'bg-red-50 text-red-700 border-red-200',
      recommendations: 'bg-pink-50 text-pink-700 border-pink-200',
    };
    return colors[topic] || 'bg-gray-50 text-gray-700 border-gray-200';
  };

  const formatTopic = (topic: string) => {
    return topic.charAt(0).toUpperCase() + topic.slice(1);
  };

  return (
    <div className={`px-4 py-2 border-b ${getTopicColor(topic)} flex items-center justify-between text-xs`}>
      <div className="flex items-center gap-2">
        <span>{getTopicIcon(topic)}</span>
        <span className="font-medium">{formatTopic(topic)}</span>
        {intent && intent !== 'statement' && (
          <span className="opacity-70">• {intent.replace('_', ' ')}</span>
        )}
      </div>
      <div className="flex items-center gap-3">
        {preferences && Object.keys(preferences).length > 0 && (
          <div className="flex items-center gap-1 text-xs opacity-70">
            <span>💡</span>
            {Object.entries(preferences).slice(0, 2).map(([key, value]) => (
              <span key={key} className="px-1.5 py-0.5 rounded bg-white bg-opacity-50">
                {key}: {value}
              </span>
            ))}
          </div>
        )}
        <span className="opacity-60">{Math.round(confidence * 100)}% match</span>
      </div>
    </div>
  );
}
