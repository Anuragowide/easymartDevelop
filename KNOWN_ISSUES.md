# Known Issues - EasyMart Assistant

## Issue #1: LLM Lists Products in Message Text (Duplicate Information)

**Status:** 🟡 Deferred  
**Priority:** Medium  
**Date Identified:** December 17, 2025  
**Branch:** `integration/backend-python`

### Description

The LLM generates product listings in the message text even though product cards are displayed below. This creates duplicate information and makes responses verbose.

### Current Behavior

**Query:** "Show me office chairs"

**LLM Response:**
```
I found five office chairs that might work for you! 
Let me know if you'd like more information about any of them.

1. Artiss Wooden Office Chair with Grey and Green fabric
2. Artiss Office Chair Gaming Chair with Computer Mesh
3. Artiss Wooden & PU Leather Office Desk Chair
4. Artiss Executive Office Chair with Racing Style
5. Artiss Gaming Office Chair with High Back
```

Then the same 5 products appear as product cards below.

### Expected Behavior

**LLM Response:**
```
I found 5 great office chairs for you!
```

Then 5 product cards appear below (without duplication).

### Root Cause

1. System prompt instructs LLM to "not list products" but LLM has access to full product data from tool results
2. LLM naturally wants to be helpful and show what it found
3. Current prompt engineering is insufficient to prevent this behavior

### Proposed Solutions

#### Option A: Strict Post-Processing (Quick Fix)
- Strip numbered lists and product names from LLM message using regex
- **Pros:** Quick to implement, guaranteed to work
- **Cons:** Hacky, might remove legitimate lists in other contexts

#### Option B: Hide Product Data from Final LLM Call (Best)
- Modify `handler.py` to send only summary to second LLM call
- Send: `"Found 5 products matching query"` instead of full product JSON
- LLM can't list products it doesn't see
- **Pros:** Clean, reliable, prevents issue at source
- **Cons:** Requires handler logic changes

#### Option C: Stronger Prompt Engineering
- Add more explicit examples and constraints to system prompt
- Use few-shot learning with correct examples
- **Pros:** No code changes needed
- **Cons:** May not be reliable with all LLM models

### Recommended Solution

**Option B** - Hide product data from final LLM call. Most reliable approach.

### Implementation Steps

1. **Modify `backend-python/app/modules/assistant/handler.py`:**
   ```python
   # Instead of sending full product data to second LLM call:
   tool_message = {
       "role": "tool",
       "content": json.dumps({
           "status": "success",
           "product_count": len(products),
           "message": f"Found {len(products)} products matching the query"
       }),
       "name": tool_name
   }
   ```

2. **Store full products in session** (already done)

3. **Return products from session** to API response (already done)

4. **Test queries:**
   - "Show me office chairs"
   - "I need comfortable furniture"
   - "Tell me about the first one" (context-aware follow-up)

### Files Affected

- `backend-python/app/modules/assistant/handler.py` (lines 255-275)
- `backend-python/app/modules/assistant/prompts.py` (system prompt section)

### Testing Checklist

- [ ] Product search returns clean intro message
- [ ] Product cards display correctly
- [ ] No duplicate product information
- [ ] Context-aware follow-ups still work ("tell me about first one")
- [ ] Spec queries work ("what are the dimensions?")
- [ ] Out-of-scope handled correctly ("show me cars")

### Related Issues

None

### Notes

- Current implementation works functionally
- This is a UX polish issue, not a critical bug
- Product cards are rendering correctly
- LLM responses are natural and friendly
- Consider implementing Option B when time permits for cleaner user experience

---

## Issue #2: Shopify Cart Integration Required

**Status:** 🔴 Not Started  
**Priority:** High  
**Date Identified:** December 19, 2025  
**Assigned To:** TBD

### Description

Current cart system stores items in Python session (temporary, local). Need to integrate with Shopify's real cart system so users can checkout directly on Shopify store.

### Current Behavior

1. User adds product to cart → Stored in Python backend session
2. Cart items only visible in chat widget
3. Cart lost when session expires
4. No way to proceed to Shopify checkout

### Expected Behavior

1. User adds product to cart → Create/update Shopify cart via Storefront API
2. Cart synced with Shopify's actual cart system
3. Cart persists across sessions via Shopify
4. "Checkout" button redirects to Shopify checkout with all items
5. Cart accessible from both chat widget and Shopify store

### Requirements

#### Backend Requirements
- [ ] Integrate Shopify Storefront API (GraphQL)
- [ ] Implement `cartCreate` mutation for new carts
- [ ] Implement `cartLinesAdd` mutation for adding items
- [ ] Implement `cartLinesUpdate` mutation for quantity changes
- [ ] Implement `cartLinesRemove` mutation for removing items
- [ ] Implement `cart` query to fetch existing cart
- [ ] Store Shopify cart ID in session/localStorage
- [ ] Return Shopify checkout URL to frontend
- [ ] Handle Shopify API errors gracefully

#### Frontend Requirements
- [ ] Update `cartApi.addToCart()` to use Shopify cart endpoint
- [ ] Update `cartApi.updateQuantity()` to sync with Shopify
- [ ] Add "Checkout" button with Shopify checkout URL redirect
- [ ] Replace localStorage cart with Shopify cart ID
- [ ] Fetch Shopify cart on widget load
- [ ] Display Shopify cart items in widget
- [ ] Handle loading states during Shopify API calls

### Implementation Plan

#### Phase 1: Backend Setup
1. Add Shopify Storefront API credentials to `.env`
2. Create `backend-python/app/modules/shopify/cart.py` for cart operations
3. Implement GraphQL mutations/queries for cart operations
4. Add `/api/shopify/cart/add` endpoint
5. Add `/api/shopify/cart/update` endpoint
6. Add `/api/shopify/cart/remove` endpoint
7. Add `/api/shopify/cart` GET endpoint
8. Add `/api/shopify/checkout-url` endpoint

#### Phase 2: Frontend Integration
1. Update `frontend/src/lib/api.ts` cart functions
2. Add Shopify cart ID storage in localStorage
3. Update `cartStore.ts` to use Shopify endpoints
4. Add checkout button to cart UI
5. Implement redirect to Shopify checkout

#### Phase 3: Testing
1. Test cart creation with single item
2. Test adding multiple items
3. Test quantity updates (+/-)
4. Test item removal
5. Test cart persistence across sessions
6. Test checkout redirect flow
7. Test error handling

### Shopify API Endpoints Needed

```graphql
# Create Cart
mutation cartCreate($input: CartInput!) {
  cartCreate(input: $input) {
    cart {
      id
      checkoutUrl
      lines(first: 10) {
        edges {
          node {
            id
            quantity
            merchandise {
              ... on ProductVariant {
                id
                title
                priceV2 { amount currencyCode }
                product { title }
              }
            }
          }
        }
      }
    }
  }
}

# Add Items to Cart
mutation cartLinesAdd($cartId: ID!, $lines: [CartLineInput!]!) {
  cartLinesAdd(cartId: $cartId, lines: $lines) {
    cart { id checkoutUrl }
  }
}

# Update Quantity
mutation cartLinesUpdate($cartId: ID!, $lines: [CartLineUpdateInput!]!) {
  cartLinesUpdate(cartId: $cartId, lines: $lines) {
    cart { id }
  }
}

# Remove Items
mutation cartLinesRemove($cartId: ID!, $lineIds: [ID!]!) {
  cartLinesRemove(cartId: $cartId, lineIds: $lineIds) {
    cart { id }
  }
}

# Fetch Cart
query cart($id: ID!) {
  cart(id: $id) {
    id
    checkoutUrl
    totalQuantity
    cost {
      totalAmount { amount currencyCode }
    }
    lines(first: 50) {
      edges {
        node {
          id
          quantity
          merchandise {
            ... on ProductVariant {
              id
              title
              priceV2 { amount currencyCode }
              image { url }
              product { title }
            }
          }
        }
      }
    }
  }
}
```

### Files to Create/Modify

**Backend:**
- `backend-python/app/modules/shopify/cart.py` (new)
- `backend-python/app/api/shopify_api.py` (new)
- `backend-python/app/core/config.py` (add Shopify API credentials)
- `backend-python/.env` (add `SHOPIFY_STOREFRONT_ACCESS_TOKEN`)

**Frontend:**
- `frontend/src/lib/api.ts` (update cart functions)
- `frontend/src/store/cartStore.ts` (use Shopify endpoints)
- `frontend/src/components/chat/CartView.tsx` (add checkout button)

### Dependencies

- Shopify Storefront API access token (already have)
- GraphQL client for Python (e.g., `gql` or `httpx`)

### Risks & Considerations

1. **API Rate Limits** - Shopify Storefront API has rate limits
2. **Product Variants** - Need to map product SKU to Shopify variant ID
3. **Cart Expiry** - Shopify carts expire after X days
4. **Offline Mode** - Need fallback if Shopify API is down
5. **CORS** - Need to configure Shopify domain access

### Success Criteria

- ✅ Items added in chat widget appear in Shopify cart
- ✅ Quantity changes sync both ways
- ✅ Checkout button redirects to Shopify with correct items
- ✅ Cart persists across browser sessions
- ✅ No data loss during cart operations

---

## Issue #3: Shopify Store Embed Integration Required

**Status:** 🔴 Not Started  
**Priority:** High  
**Date Identified:** December 19, 2025  
**Assigned To:** TBD

### Description

Chat widget currently only works on localhost. Need to embed chat widget on actual Shopify store (easymartdummy.myshopify.com) so customers can use it while browsing products.

### Current Behavior

- Chat widget accessible only at `localhost:3000`
- Not visible on Shopify store homepage
- No integration with Shopify themes

### Expected Behavior

- Chat widget appears on all Shopify store pages (homepage, product pages, collections)
- Widget accessible via floating button in bottom-right corner
- Seamless integration with Shopify theme
- CORS configured to allow Shopify domain requests

### Requirements

#### Shopify App Setup
- [ ] Create Shopify App in Partner Dashboard (if not exists)
- [ ] Configure App URL and redirect URLs
- [ ] Set up OAuth for app installation
- [ ] Configure app scopes (read_products, write_carts, etc.)

#### Backend Configuration
- [ ] Set up App Proxy to serve widget from backend
- [ ] Configure CORS to allow `easymartdummy.myshopify.com`
- [ ] Add Shopify domain to allowed origins
- [ ] Handle Shopify webhook validation

#### Frontend Deployment
- [ ] Build widget as standalone script
- [ ] Create embeddable widget loader script
- [ ] Minimize bundle size for fast loading
- [ ] Add widget to Shopify theme via script tag

#### Theme Integration
- [ ] Create Theme App Extension for widget
- [ ] Add widget to theme's `layout/theme.liquid`
- [ ] Style widget to match store theme
- [ ] Test on mobile and desktop

### Implementation Plan

#### Phase 1: Shopify App Setup
1. Create app in Shopify Partner Dashboard
2. Configure app URLs and scopes
3. Install app on easymartdummy.myshopify.com
4. Test OAuth flow

#### Phase 2: Widget Bundle Creation
1. Create `frontend/src/widget/index.tsx` (standalone entry)
2. Configure Vite/Next.js to build widget bundle
3. Add widget loader script (inject iframe/div)
4. Test bundle on local Shopify theme

#### Phase 3: Deployment
1. Deploy backend with CORS for Shopify domain
2. Upload widget bundle to CDN or static hosting
3. Add script tag to Shopify theme
4. Test on live store

#### Phase 4: Theme App Extension (Optional, Better UX)
1. Create Theme App Extension in Partner Dashboard
2. Add app block for widget placement
3. Allow merchants to customize widget position
4. Submit extension for review

### Technical Approach

**Option A: Script Tag (Quick)**
Add script to theme's `theme.liquid`:
```html
<script src="https://your-cdn.com/easymart-widget.js"></script>
<script>
  EasymartWidget.init({
    apiUrl: 'https://your-backend.com',
    shopDomain: 'easymartdummy.myshopify.com'
  });
</script>
```

**Option B: App Proxy (Recommended)**
- Shopify proxies requests to your backend
- URL: `easymartdummy.myshopify.com/apps/easymart-chat`
- Better security and control

**Option C: Theme App Extension (Best UX)**
- Merchants can drag-drop widget in theme editor
- No code changes needed
- Better for multi-store deployment

### Files to Create/Modify

**Shopify App Config:**
- `shopify.app.toml` (new)
- Partner Dashboard settings

**Frontend Widget:**
- `frontend/src/widget/index.tsx` (new)
- `frontend/src/widget/loader.js` (new)
- `frontend/vite.config.ts` (add widget build target)

**Backend:**
- `backend-node/src/modules/shopify/proxy.ts` (new)
- `backend-node/src/config/cors.ts` (update allowed origins)

**Shopify Theme:**
- `theme/layout/theme.liquid` (add script tag)
- `theme/snippets/easymart-widget.liquid` (optional)

### CORS Configuration

```typescript
// backend-node/src/config/cors.ts
const allowedOrigins = [
  'http://localhost:3000',
  'https://easymartdummy.myshopify.com',
  'https://admin.shopify.com', // For app embed
];
```

### Testing Checklist

- [ ] Widget loads on Shopify homepage
- [ ] Widget works on product pages
- [ ] Widget works on collection pages
- [ ] Widget works on mobile devices
- [ ] Chat functionality works cross-origin
- [ ] Add to cart works from Shopify store
- [ ] Widget doesn't conflict with theme styles
- [ ] Loading performance acceptable (<2s)

### Dependencies

- Shopify Partner account (have)
- Shopify App created (need to create)
- CDN for widget hosting (optional, can use backend)
- SSL certificate for backend (needed for production)

### Success Criteria

- ✅ Chat widget visible on easymartdummy.myshopify.com
- ✅ Widget works seamlessly with Shopify theme
- ✅ All chat features functional on live store
- ✅ CORS properly configured
- ✅ No console errors on store pages

---

## Issue #4: Decrease Quantity Bug

**Status:** 🟡 In Progress  
**Priority:** Medium  
**Date Identified:** December 19, 2025

### Description

Clicking the `-` (decrease) button on product quantity counter adds products instead of decreasing quantity.

### Current Behavior

- Click `+` button → quantity increases ✅
- Click `-` button → API returns 500 error, quantity doesn't decrease ❌

### Root Cause Analysis

**Identified Root Cause:** Node backend `cart.route.ts` was hardcoding `action: 'add'` instead of passing the `action` parameter from frontend.

**Frontend Flow:**
1. User clicks `-` → `handleDecrease(product)` called
2. `decreaseQuantity(productId)` calculates `newQuantity = currentQty - 1`
3. `cartApi.updateQuantity(productId, newQuantity)` sends request with `action: 'set'`
4. ✅ Frontend logic is correct

**Node Backend Issue (FIXED):**
- Line 38 in `cart.route.ts` was hardcoded: `action: 'add'`
- This overwrote the frontend's `action: 'set'` parameter
- Fixed by reading `action` from request body: `action: action || 'add'`

**Current Status:**
- Fixed Node backend to pass action parameter
- Getting 500 error from Python backend (needs investigation)
- Need to verify Python backend `action: 'set'` logic is working

### Investigation Progress

**Completed:**
- ✅ Added extensive debugging logs to frontend cartStore.ts
- ✅ Added debugging logs to backend tools.py (update_cart)
- ✅ Added debugging logs to backend session_store.py (add_to_cart)
- ✅ Fixed Node backend to pass action parameter from frontend
- ✅ Added field normalization in frontend (id and product_id)
- ✅ Fixed TypeScript error in cartStore (id could be undefined)

**Remaining Issues:**
- ❌ Python backend returning 500 error after Node fix
- ❌ Need to restart Python backend to load debug logs
- ❌ Need to verify session store operations

### Debugging Added

**Frontend (cartStore.ts):**
```typescript
// Lines 76-117: Enhanced decreaseQuantity with logging
console.log('🔍 [DECREASE] Current quantity:', currentQty);
console.log('📤 [DECREASE] Sending to API - newQuantity:', newQuantity);
console.log('📥 [DECREASE] Full response:', response);
console.log('✅ [DECREASE] Normalized items:', normalizedItems);
console.log('🔍 [DECREASE] Verify - quantity:', verifyQty);
```

**Backend (tools.py):**
```python
# Lines 553-560: Added logging for action='set'
logger.info(f"[CART SET] Before remove - cart_items: {session.cart_items}")
logger.info(f"[CART SET] After remove - cart_items: {session.cart_items}")
logger.info(f"[CART SET] After add ({quantity}) - cart_items: {session.cart_items}")
```

**Backend (session_store.py):**
```python
# Lines 115-135: Added logging for add_to_cart
logger.info(f"[ADD_TO_CART] product_id={product_id}, quantity={quantity}")
logger.info(f"[ADD_TO_CART] Current cart_items: {self.cart_items}")
logger.info(f"[ADD_TO_CART] Found existing item, adding...")
logger.info(f"[ADD_TO_CART] Cart items after add: {self.cart_items}")
```

### Next Steps

1. **Restart Python backend** - Load new debug logs
2. **Test decrease button** - Should see all debug logs in Python terminal
3. **Check Python 500 error** - Investigate exact error from Python backend
4. **Verify session persistence** - Ensure session.cart_items updates correctly
5. **Test edge cases:**
   - Decrease from 2 → 1 (should work)
   - Decrease from 1 → 0 (should remove item)
   - Check if cart_items updates in session store

### Files Modified

**Frontend:**
- `frontend/src/store/cartStore.ts` (added debugging, field normalization)
- `frontend/src/lib/api.ts` (CartItem interface with product_id)

**Backend:**
- `backend-node/src/modules/web/routes/cart.route.ts` (pass action parameter) ✅ FIXED
- `backend-python/app/modules/assistant/tools.py` (added debug logs)
- `backend-python/app/modules/assistant/session_store.py` (added debug logs)
- `backend-python/app/api/assistant_api.py` (cart enrichment with title/image fields)

### Known Issues Blocking Resolution

1. **Python backend not restarting** - Debug logs not appearing in terminal
2. **500 error from Python** - Need to see actual error message
3. **Session persistence unclear** - Need to verify cart_items updates are saved

### Testing Checklist

- [ ] Python backend restarted with debug logs
- [ ] Click `-` shows `[CART SET]` logs in Python terminal
- [ ] Cart response shows correct quantity after decrease
- [ ] Frontend normalizedItems has both id and product_id
- [ ] Zustand state updates correctly
- [ ] Cart badge updates to show correct item count

---

## Issue #5: (Placeholder for future issues)

**Status:** N/A  
**Priority:** N/A  
**Date Identified:** N/A

---

## Completed Issues

### ✅ Fixed: Tool Call Syntax Leaking to Users
**Fixed:** December 17, 2025  
**Solution:** Added regex cleanup in `handler.py` to strip `[TOOL_CALLS]` tags from final response

### ✅ Fixed: Product Cards Not Rendering
**Fixed:** December 17, 2025  
**Solution:** Added proper action transformation in `pythonClient.ts` to convert string actions to action objects with product data

### ✅ Fixed: "Found X products" Redundant Label
**Fixed:** December 17, 2025  
**Solution:** Removed label from `MessageBubble.tsx`, let cards speak for themselves

### ✅ Fixed: Product Price Type Error
**Fixed:** December 17, 2025  
**Solution:** Added type checking in `ProductCard.tsx` to handle both string and number price types
