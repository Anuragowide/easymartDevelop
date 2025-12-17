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

## Issue #2: (Placeholder for future issues)

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
