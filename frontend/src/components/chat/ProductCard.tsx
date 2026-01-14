'use client';

import { ProductCardProps } from '@/lib/types';
import Image from 'next/image';
import { useState } from 'react';

export function ProductCard({ product, onAddToCart }: ProductCardProps) {
  const [isAdding, setIsAdding] = useState(false);
  const [added, setAdded] = useState(false);
  const [error, setError] = useState(false);

  const handleAddToCart = async () => {
    if (onAddToCart && !isAdding) {
      setIsAdding(true);
      setError(false);
      try {
        await onAddToCart(product.id);
        setAdded(true);
        // Reset "added" state after 2 seconds
        setTimeout(() => setAdded(false), 2000);
      } catch (err) {
        console.error('Failed to add to cart:', err);
        setError(true);
        // Reset error state after 3 seconds
        setTimeout(() => setError(false), 3000);
      } finally {
        setIsAdding(false);
      }
    }
  };

  // Extract price number for display - handle both string and number types
  const priceValue = typeof product.price === 'string' 
    ? product.price.replace(/[^0-9.]/g, '') 
    : String(product.price);

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition-shadow duration-200">
      <div className="flex gap-4 p-4">
        {/* Product Image */}
        <div className="flex-shrink-0 w-24 h-24 bg-gray-100 rounded-lg overflow-hidden relative">
          {product.image ? (
            <Image
              src={product.image}
              alt={product.title}
              fill
              className="object-cover"
              sizes="96px"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
          )}
        </div>

        {/* Product Info */}
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-semibold text-gray-900 truncate mb-1">
            {product.title}
          </h3>
          
          {product.description && (
            <p className="text-sm text-gray-600 line-clamp-2 mb-2">
              {product.description}
            </p>
          )}

          <div className="flex items-center justify-between gap-3">
            <div className="flex items-baseline gap-1">
              <span className="text-xl font-bold text-primary-600">
                ${priceValue}
              </span>
              {product.inStock !== undefined && (
                <span className={`text-xs font-medium ${
                  product.inStock ? 'text-green-600' : 'text-red-600'
                }`}>
                  {product.inStock ? 'In Stock' : 'Out of Stock'}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="px-4 pb-4 flex gap-2">
        <a
          href={product.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium rounded-lg transition-colors duration-200 text-center"
        >
          View Details
        </a>
        {onAddToCart && product.inStock !== false && (
          <button
            onClick={handleAddToCart}
            disabled={isAdding}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 flex items-center justify-center min-w-[110px] ${
              error
                ? 'bg-red-500 text-white border-2 border-red-500'
                : added 
                  ? 'bg-green-500 text-white border-2 border-green-500' 
                  : isAdding 
                    ? 'bg-gray-100 text-gray-400 border-2 border-gray-300 cursor-not-allowed'
                    : 'bg-white border-2 border-primary-600 text-primary-600 hover:bg-primary-50 active:bg-primary-100'
            }`}
          >
            {isAdding ? (
              <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            ) : error ? (
              <>
                <svg className="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                Error
              </>
            ) : added ? (
              <>
                <svg className="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Added
              </>
            ) : (
              <>
                <svg className="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                Add to Cart
              </>
            )}
          </button>
        )}
      </div>

      {/* Variants (if available) */}
      {product.variants && product.variants.length > 0 && (
        <div className="px-4 pb-4 border-t border-gray-100 pt-3">
          <p className="text-xs text-gray-500 font-medium mb-2">Available variants:</p>
          <div className="flex flex-wrap gap-2">
            {product.variants.slice(0, 3).map((variant) => (
              <span
                key={variant.id}
                className="inline-flex items-center px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded"
              >
                {variant.title}
              </span>
            ))}
            {product.variants.length > 3 && (
              <span className="inline-flex items-center px-2 py-1 text-gray-500 text-xs">
                +{product.variants.length - 3} more
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
