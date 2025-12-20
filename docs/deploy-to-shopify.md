# 🚀 Complete Step-by-Step Guide: Deploy EasyMart Chat to Shopify Store

**Goal:** Make your chat widget appear on easymartdummy.myshopify.com

---

## 📋 Prerequisites Checklist

✅ You have:
- Shopify store: `easymartdummy.myshopify.com`
- Shopify Admin access
- Access token (for API)
- Chat widget working on `localhost:3000`
- Backend running on `localhost:8000` (Python) and `localhost:3001` (Node)

---

## 🎯 Deployment Strategy

We'll use **Script Tag Method** (easiest for beginners)

**Steps Overview:**
1. Deploy backend to cloud (Render/Railway)
2. Deploy frontend to Vercel
3. Add widget script to Shopify theme
4. Test on live store

---

## 📦 PHASE 1: Deploy Backend (Python + Node)

### Option A: Deploy to Render.com (Recommended - Free Tier)

#### Step 1.1: Create Render Account
1. Go to https://render.com
2. Sign up with GitHub
3. Click "New +" → "Web Service"

#### Step 1.2: Deploy Python Backend
1. In Render dashboard, click "New +" → "Web Service"
2. Connect your GitHub repository
3. Configure:
   ```
   Name: easymart-python-backend
   Environment: Python 3
   Build Command: cd backend-python && pip install -r requirements.txt
   Start Command: cd backend-python && uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
4. Add Environment Variables:
   ```
   SHOPIFY_STORE_DOMAIN=easymartdummy.myshopify.com
   SHOPIFY_ACCESS_TOKEN=[your token]
   HUGGINGFACE_API_KEY=[your key]
   ENVIRONMENT=production
   ```
5. Click "Create Web Service"
6. Wait 5-10 minutes for deployment
7. **Copy the URL** (e.g., `https://easymart-python-backend.onrender.com`)

#### Step 1.3: Deploy Node Backend
1. Click "New +" → "Web Service" again
2. Same GitHub repo
3. Configure:
   ```
   Name: easymart-node-backend
   Environment: Node
   Build Command: cd backend-node && npm install
   Start Command: cd backend-node && npm start
   ```
4. Add Environment Variables:
   ```
   NODE_BACKEND_URL=https://easymart-python-backend.onrender.com
   SHOPIFY_STORE_DOMAIN=easymartdummy.myshopify.com
   ENVIRONMENT=production
   ```
5. Click "Create Web Service"
6. **Copy the URL** (e.g., `https://easymart-node-backend.onrender.com`)

---

## 🌐 PHASE 2: Deploy Frontend to Vercel

#### Step 2.1: Create Vercel Account
1. Go to https://vercel.com
2. Sign up with GitHub
3. Click "Add New" → "Project"

#### Step 2.2: Deploy Frontend
1. Select your GitHub repository
2. Configure:
   ```
   Framework Preset: Next.js
   Root Directory: frontend
   Build Command: npm run build
   Output Directory: .next
   ```
3. Add Environment Variables:
   ```
   NEXT_PUBLIC_API_URL=https://easymart-node-backend.onrender.com
   ```
4. Click "Deploy"
5. Wait 2-3 minutes
6. **Copy the URL** (e.g., `https://easymart.vercel.app`)

---

## 🛍️ PHASE 3: Add Widget to Shopify Store

### Step 3.1: Access Shopify Admin
1. Go to https://easymartdummy.myshopify.com/admin
2. Login with your credentials

### Step 3.2: Edit Theme Code
1. In Shopify Admin, click "Online Store" → "Themes"
2. Find your active theme (e.g., "Dawn")
3. Click "..." (Actions) → "Edit code"

### Step 3.3: Add Widget Script
1. In left sidebar, find `Layout` folder
2. Click `theme.liquid`
3. Find the closing `</body>` tag (usually near bottom)
4. **Paste this code BEFORE `</body>`:**

```html
<!-- EasyMart Chat Widget -->
<script>
  (function() {
    // Configuration
    var config = {
      apiUrl: 'https://easymart-node-backend.onrender.com',
      widgetUrl: 'https://easymart.vercel.app',
      shopDomain: 'easymartdummy.myshopify.com'
    };
    
    // Create iframe for chat widget
    var iframe = document.createElement('iframe');
    iframe.src = config.widgetUrl + '/chat';
    iframe.style.cssText = 'position: fixed; bottom: 20px; right: 20px; width: 400px; height: 600px; border: none; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); z-index: 9999;';
    iframe.id = 'easymart-chat-widget';
    
    // Add to page when DOM is ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function() {
        document.body.appendChild(iframe);
      });
    } else {
      document.body.appendChild(iframe);
    }
  })();
</script>
```

5. Click "Save" (top right)

### Step 3.4: Test the Widget
1. Visit your store: https://easymartdummy.myshopify.com
2. You should see the chat widget in bottom-right corner
3. Test by asking: "Show me office chairs"

---

## 🔧 PHASE 4: Configure CORS (Security)

### Step 4.1: Update Backend CORS Settings

**File:** server.ts

Find the CORS configuration and update:

```typescript
fastify.register(cors, {
  origin: [
    'http://localhost:3000',
    'https://easymart.vercel.app',
    'https://easymartdummy.myshopify.com',
    'https://admin.shopify.com'
  ],
  credentials: true
});
```

### Step 4.2: Redeploy Backend
1. Commit changes to GitHub
2. Render will auto-deploy (wait 2-3 minutes)

---

## 📱 PHASE 5: Mobile Optimization

### Step 5.1: Make Widget Responsive

Update the script in `theme.liquid`:

```html
<script>
  (function() {
    var config = {
      apiUrl: 'https://easymart-node-backend.onrender.com',
      widgetUrl: 'https://easymart.vercel.app',
      shopDomain: 'easymartdummy.myshopify.com'
    };
    
    var iframe = document.createElement('iframe');
    iframe.src = config.widgetUrl + '/chat';
    iframe.id = 'easymart-chat-widget';
    
    // Responsive sizing
    function updateSize() {
      var isMobile = window.innerWidth < 768;
      if (isMobile) {
        iframe.style.cssText = 'position: fixed; bottom: 0; right: 0; width: 100%; height: 70vh; border: none; z-index: 9999;';
      } else {
        iframe.style.cssText = 'position: fixed; bottom: 20px; right: 20px; width: 400px; height: 600px; border: none; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); z-index: 9999;';
      }
    }
    
    updateSize();
    window.addEventListener('resize', updateSize);
    
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function() {
        document.body.appendChild(iframe);
      });
    } else {
      document.body.appendChild(iframe);
    }
  })();
</script>
```

---

## ✅ PHASE 6: Testing Checklist

Test these scenarios:

### Desktop Testing
- [ ] Chat widget appears on homepage
- [ ] Widget appears on product pages
- [ ] Widget appears on collection pages
- [ ] Can search for products
- [ ] Product cards display correctly
- [ ] Add to cart works
- [ ] Cart badge updates

### Mobile Testing
- [ ] Widget is responsive
- [ ] Chat is usable on small screens
- [ ] Touch interactions work
- [ ] No layout breaking

### Functionality Testing
- [ ] Search: "Show me office chairs"
- [ ] Spec query: "What are the dimensions?"
- [ ] Add to cart
- [ ] View cart
- [ ] Off-topic query: "Tell me about cars" (should reject)

---

## 🚨 Troubleshooting Guide

### Issue: Widget Not Appearing
**Solution:**
1. Check browser console for errors (F12)
2. Verify widget URL is correct
3. Clear browser cache
4. Check if script is in `theme.liquid`

### Issue: CORS Errors
**Solution:**
1. Check backend CORS settings include Shopify domain
2. Redeploy backend after CORS changes
3. Check browser console for exact error

### Issue: Chat Not Responding
**Solution:**
1. Check backend is running (visit backend URL)
2. Check API URL in widget script is correct
3. Check Shopify store domain matches config

### Issue: Products Not Loading
**Solution:**
1. Check catalog is indexed in backend
2. Run: `cd backend-python && python -m app.modules.assistant.cli index-catalog`
3. Restart Python backend

---

## 📊 Monitoring & Analytics (Optional)

### Step 7.1: Add Analytics
1. In Shopify Admin → Settings → Integrations
2. Add Google Analytics tracking ID
3. Track chat widget usage

---

## 🎉 Success Criteria

You're done when:
- ✅ Chat widget visible on easymartdummy.myshopify.com
- ✅ Can search for products
- ✅ Products display in chat
- ✅ Add to cart works
- ✅ Cart badge updates
- ✅ Works on mobile and desktop
- ✅ No console errors

---

## 📞 Support Checklist

If you get stuck, check:
1. Backend is deployed and running (visit URL)
2. Frontend is deployed and running (visit URL)
3. Script is added to `theme.liquid` correctly
4. CORS is configured for Shopify domain
5. No console errors in browser (F12)

---

## 🔄 Alternative: Local Testing First

If cloud deployment is complex, test locally first:

1. **Expose local backend with ngrok:**
   ```bash
   # Install ngrok
   npm install -g ngrok
   
   # Expose Node backend
   ngrok http 3001
   # Copy URL: https://abc123.ngrok.io
   
   # Expose Python backend (in another terminal)
   ngrok http 8000
   # Copy URL: https://xyz789.ngrok.io
   ```

2. **Update widget script with ngrok URLs:**
   ```javascript
   apiUrl: 'https://abc123.ngrok.io'
   ```

3. **Test on Shopify store**

This lets you test before cloud deployment!

---

**Which deployment method do you want to start with?**
- A) Cloud deployment (Render + Vercel) - Production ready
- B) Local testing (ngrok) - Quick test first