/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,

    // API proxy to Node.js backend
    async rewrites() {
        return [{
            source: '/api/:path*',
            destination: process.env.NEXT_PUBLIC_API_URL + '/api/:path*',
        }, ];
    },

    // Allow dev origins (fixes cross-origin warning)
    allowedDevOrigins: ['127.0.0.1', 'localhost'],

    // Image configuration for Shopify CDN (updated to remotePatterns)
    images: {
        remotePatterns: [{
                protocol: 'https',
                hostname: 'cdn.shopify.com',
                pathname: '/**',
            },
            {
                protocol: 'https',
                hostname: 'easymartdummy.myshopify.com',
                pathname: '/**',
            },
        ],
    },

    // Environment variables
    env: {
        NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001',
    },

    // Enable SWC minification
    swcMinify: true,

    // Experimental features
    experimental: {
        optimizeCss: true,
    },

    // Enable standalone output for Docker
    output: 'standalone',
};

module.exports = nextConfig;