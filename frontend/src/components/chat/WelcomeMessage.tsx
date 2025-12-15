import { WelcomeMessageProps } from '@/lib/types';

export function WelcomeMessage({ userName }: WelcomeMessageProps) {
  const suggestions = [
    { icon: '🎧', title: "Show me wireless headphones", subtitle: "under $100" },
    { icon: '💻', title: "Best laptop for students", subtitle: "with recommendations" },
    { icon: '🎁', title: "I'm looking for a gift", subtitle: "get suggestions" },
    { icon: '📱', title: "Compare smartphones", subtitle: "iPhone vs Samsung" }
  ];

  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] px-8 py-12">
      {/* Premium greeting with gradient */}
      <div className="text-center mb-16 relative">
        {/* Glow effect */}
        <div className="absolute inset-0 blur-3xl opacity-30">
          <div className="w-64 h-64 mx-auto bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 rounded-full" />
        </div>
        
        <div className="relative z-10">
          <h1 className="text-6xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 mb-4">
            Hello there!
          </h1>
          <p className="text-2xl text-gray-300 font-light">
            How can I help you today?
          </p>
        </div>
      </div>

      {/* Premium suggestion cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl w-full">
        {suggestions.map((suggestion, index) => (
          <button
            key={index}
            className="group relative overflow-hidden rounded-2xl p-6 text-left transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl"
            style={{
              background: 'linear-gradient(135deg, rgba(30, 30, 40, 0.9) 0%, rgba(20, 20, 30, 0.8) 100%)',
              border: '1px solid rgba(255, 255, 255, 0.1)'
            }}
          >
            {/* Gradient overlay on hover */}
            <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 via-purple-500/10 to-pink-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            
            <div className="relative z-10 flex items-start gap-4">
              <div className="text-4xl flex-shrink-0 group-hover:scale-110 transition-transform duration-300">
                {suggestion.icon}
              </div>
              <div className="flex-1">
                <div className="text-base font-semibold text-white mb-1 group-hover:text-blue-300 transition-colors">
                  {suggestion.title}
                </div>
                <div className="text-sm text-gray-400">
                  {suggestion.subtitle}
                </div>
              </div>
              <svg className="w-5 h-5 text-gray-600 group-hover:text-blue-400 group-hover:translate-x-1 transition-all duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </div>
          </button>
        ))}
      </div>

      {/* Feature hints */}
      <div className="mt-12 flex items-center gap-6 text-sm text-gray-500">
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
          <span>AI-Powered</span>
        </div>
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
            <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
          </svg>
          <span>24/7 Available</span>
        </div>
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
          <span>Trusted Shopping</span>
        </div>
      </div>
    </div>
  );
}
