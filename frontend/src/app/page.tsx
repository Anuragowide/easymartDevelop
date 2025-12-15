import Link from 'next/link';

export default function Home() {
  const menuItems = [
    {
      href: '/chat',
      icon: '💬',
      title: 'Chat Interface',
      description: 'Try the AI-powered shopping assistant',
      gradient: 'from-blue-500/10 to-purple-500/10'
    },
    {
      href: '/products',
      icon: '📦',
      title: 'Products',
      description: 'Browse all available products',
      gradient: 'from-purple-500/10 to-pink-500/10'
    },
    {
      href: '/admin',
      icon: '📊',
      title: 'Admin Dashboard',
      description: 'View analytics and manage settings',
      gradient: 'from-pink-500/10 to-orange-500/10'
    },
    {
      href: '/admin/widget-config',
      icon: '⚙️',
      title: 'Widget Config',
      description: 'Configure and embed the chat widget',
      gradient: 'from-orange-500/10 to-blue-500/10'
    }
  ];

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-black px-8 py-12">
      {/* Header */}
      <div className="text-center mb-16">
        <div className="inline-flex items-center gap-3 mb-6">
          <div className="text-6xl">🛒</div>
        </div>
        <h1 className="text-5xl md:text-6xl font-bold text-white mb-4 font-mono tracking-tight">
          EasyMart - AI Shopping Assistant
        </h1>
      </div>
      
      {/* Menu Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-5xl w-full">
        {menuItems.map((item, index) => (
          <Link 
            key={index}
            href={item.href} 
            className="group relative overflow-hidden rounded-2xl p-8 transition-all duration-300 hover:scale-[1.02] border border-white/10"
            style={{
              background: 'linear-gradient(135deg, rgba(30, 30, 40, 0.9) 0%, rgba(20, 20, 30, 0.8) 100%)'
            }}
          >
            {/* Gradient overlay on hover */}
            <div className={`absolute inset-0 bg-gradient-to-br ${item.gradient} opacity-0 group-hover:opacity-100 transition-opacity duration-300`} />
            
            <div className="relative z-10 flex items-start gap-4">
              <div className="text-5xl flex-shrink-0 group-hover:scale-110 transition-transform duration-300">
                {item.icon}
              </div>
              <div className="flex-1">
                <h2 className="text-2xl font-bold text-white mb-2 font-mono">
                  {item.title}
                </h2>
                <p className="text-gray-400 text-sm leading-relaxed">
                  {item.description}
                </p>
              </div>
              <svg className="w-6 h-6 text-gray-600 group-hover:text-white group-hover:translate-x-1 transition-all duration-300 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </div>
          </Link>
        ))}
      </div>

      {/* Footer */}
      <div className="mt-16 text-center">
        <p className="text-gray-500 text-sm font-mono mb-3">
          Backend API: <span className="text-gray-400">http://localhost:3001</span>
        </p>
        <p className="text-gray-600 text-xs font-mono">
          Node.js + Python + Elasticsearch + Next.js
        </p>
      </div>
    </main>
  );
}
