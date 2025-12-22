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

    // Image domains for Shopify CDN
    images: {
        domains: [
            'cdn.shopify.com',
            'easymartdummy.myshopify.com',
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