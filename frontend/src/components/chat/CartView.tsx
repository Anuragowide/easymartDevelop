'use client';

import React from 'react';
import { useCartStore } from '@/store/cartStore';
import { useChatStore } from '@/store/chatStore';
import Image from 'next/image';

export function CartView() {
  const { items, total, decreaseQuantity, increaseQuantity, removeFromCart, isLoading } = useCartStore();
  const { setCartOpen } = useChatStore();

  if (items.length === 0) {
    return (
      <div className="absolute inset-0 bg-white z-20 flex flex-col items-center justify-center p-6 text-center">
        <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mb-4">
          <svg className="w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-gray-900">Your cart is empty</h3>
        <p className="text-gray-500 mt-2 mb-6">Looks like you haven't added anything yet.</p>
        <button
          onClick={() => setCartOpen(false)}
          className="px-6 py-2 bg-red-600 text-white rounded-full font-medium hover:bg-red-700 transition-colors"
        >
          Continue Shopping
        </button>
      </div>
    );
  }

  return (
    <div className="absolute inset-0 bg-white z-20 flex flex-col">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-bold text-gray-900">Shopping Cart</h3>
          <button 
            onClick={() => setCartOpen(false)}
            className="text-gray-400 hover:text-gray-600"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {items.map((item) => (
          <div key={item.id} className="flex gap-4 p-3 bg-gray-50 rounded-xl border border-gray-100 group">
            <div className="w-16 h-16 bg-white rounded-lg overflow-hidden flex-shrink-0 relative border border-gray-200">
              {item.image ? (
                <Image src={item.image} alt={item.title} fill className="object-cover" sizes="64px" />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-gray-300">
                  <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 24 24"><path d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                </div>
              )}
            </div>
            
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-semibold text-gray-900 truncate">{item.title}</h4>
              <p className="text-xs text-red-600 font-bold mt-1">${item.price}</p>
              
              <div className="flex items-center gap-3 mt-2">
                <div className="flex items-center border border-gray-200 rounded-lg bg-white overflow-hidden h-7">
                  <button
                    onClick={() => decreaseQuantity(item.id || item.product_id!)}
                    disabled={isLoading}
                    className="px-2 hover:bg-gray-100 text-gray-600 disabled:opacity-50"
                  >
                    -
                  </button>
                  <span className="px-2 text-xs font-medium w-8 text-center">{item.quantity}</span>
                  <button
                    onClick={() => increaseQuantity(item.id || item.product_id!)}
                    disabled={isLoading}
                    className="px-2 hover:bg-gray-100 text-gray-600 disabled:opacity-50"
                  >
                    +
                  </button>
                </div>
                
                  <button
                    onClick={() => removeFromCart(item.id || item.product_id!)}
                    className="text-xs text-gray-400 hover:text-red-600 transition-colors"
                  >
                    Remove
                  </button>

              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="p-4 border-t border-gray-100 bg-white space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-gray-500 font-medium">Total</span>
          <span className="text-xl font-bold text-gray-900">${total.toFixed(2)}</span>
        </div>
        <button
          className="w-full py-3 bg-gradient-to-r from-red-600 to-pink-600 text-white rounded-xl font-bold hover:shadow-lg transition-all active:scale-[0.98]"
          onClick={() => {
            alert('Checkout functionality will be available soon!');
          }}
        >
          Proceed to Checkout
        </button>
        <button
          onClick={() => setCartOpen(false)}
          className="w-full text-sm text-gray-500 font-medium hover:text-gray-700 transition-colors py-1"
        >
          Back to Chat
        </button>
      </div>
    </div>
  );
}
