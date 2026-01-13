# ⚡ Quick Start Guide - Production Deployment

## ✅ PRE-LAUNCH CHECKLIST (DO THIS NOW!)

### 1. Create data directory for session persistence
```powershell
# In backend-python directory
New-Item -ItemType Directory -Force -Path "data"
```

### 2. Verify Node.js backend is running
```powershell
# Open a new terminal, go to backend-node
cd ..\backend-node
npm start
# Should see: Server running on port 3002
```

### 3. Test the Python backend
```powershell
# In backend-python terminal (with venv activated)
python -m pytest tests/test_api.py -v
```

### 4. Quick smoke test (5 minutes)
Open browser console and test these scenarios:

**Test 1: Product Search**
```
User: "Show me office chairs"
Expected: Returns list of chairs
```

**Test 2: Add to Cart**
```
User: "Add option 1 to cart"
Expected: Product added, cart count increases
```

**Test 3: Clear Cart**
```
User: "Clear my cart"
Expected: Cart cleared successfully
```

**Test 4: Find Similar**
```
User: "Find similar products"
Expected: Shows similar items without asking for clarification
```

**Test 5: Context Retention**
```
User: "Search for desks"
User: "wooden"
Expected: Shows wooden desks (not asking for clarification)
```

### 5. Check logs for errors
```powershell
# Look for ERROR or CRITICAL in logs
Get-Content backend-python/events.jsonl -Tail 50 | Select-String "ERROR|CRITICAL"
```

---

## 🚀 LAUNCH SEQUENCE (At 1 PM)

### Step 1: Restart backend with fresh sessions
```powershell
# Stop Python backend (Ctrl+C)
# Start fresh
uvicorn app.main:app --reload --port 8000
```

### Step 2: Verify health endpoints
```powershell
# Test health check
curl http://localhost:8000/health

# Expected: {"status":"healthy","timestamp":"..."}
```

### Step 3: Monitor first 10 minutes
Watch for:
- Response times < 5 seconds ✓
- No ERROR in logs ✓
- Cart operations working ✓
- Session persistence working ✓

---

## 🔧 IMPLEMENTED FIXES

### ✅ Today's Critical Fixes:
1. **Session Persistence** - Sessions now saved to `data/sessions.pkl`
2. **Timeout Configurations** - Added LLM_TIMEOUT, API_TIMEOUT, SEARCH_TIMEOUT
3. **Debug Logging** - Replaced print() with proper logger.debug()
4. **Context Retention** - Fixed "wooden" after "desks" issue
5. **Find Similar** - Works without clarification
6. **Clear Cart** - Properly syncs with Node.js
7. **Quantity Handling** - No more double-add

---

## 📊 MONITORING COMMANDS

### Watch logs in real-time
```powershell
Get-Content backend-python/events.jsonl -Wait -Tail 20
```

### Count errors
```powershell
(Get-Content backend-python/events.jsonl | Select-String "ERROR").Count
```

### Check session file
```powershell
Test-Path backend-python/data/sessions.pkl
# Should return: True (if sessions created)
```

---

## 🆘 TROUBLESHOOTING

### Issue: "Sessions not persisting"
**Solution:**
```powershell
# Check if data directory exists
Test-Path backend-python/data
# If False, create it:
New-Item -ItemType Directory -Force -Path "backend-python/data"
```

### Issue: "Cart not updating"
**Solution:**
```powershell
# Verify Node.js is running
curl http://localhost:3002/health
# Restart if needed
```

### Issue: "Slow responses"
**Check:**
```python
# Look for timeout logs
Get-Content backend-python/events.jsonl -Tail 100 | Select-String "timeout|TIMEOUT"
```

### Issue: "Context not retained"
**Check:**
```python
# Verify session ID is consistent across messages
# Look in browser DevTools > Network > Payload
```

---

## 📞 EMERGENCY CONTACTS

**If critical issue:**
1. Check logs: `backend-python/events.jsonl`
2. Restart services
3. Direct users to phone: **1300 327 962**

**Fallback message to display:**
```
"Our chatbot is temporarily unavailable. 
Please call us at 1300 327 962 or email support@easymart.com.au"
```

---

## 🎯 SUCCESS CRITERIA

Your launch is successful if:
- ✅ 95%+ of messages get response < 5 seconds
- ✅ No critical errors in first hour
- ✅ Cart operations work consistently
- ✅ Sessions persist across server restarts
- ✅ Context is retained across messages

---

## 📈 POST-LAUNCH (Next 24 Hours)

### Monitor these metrics:
1. **Response Time Average** - Should be 2-3 seconds
2. **Error Rate** - Should be < 5%
3. **Session Count** - Track growth
4. **Cart Conversion** - Add-to-cart success rate

### Quick check command:
```powershell
# Count total requests today
(Get-Content backend-python/events.jsonl | Select-String "assistant_request").Count

# Count errors today
(Get-Content backend-python/events.jsonl | Select-String '"event_type":"error"').Count
```

---

## 🎉 YOU'RE READY TO GO LIVE!

All critical fixes are implemented. Your chatbot is production-ready.

**Good luck with the 1 PM launch! 🚀**
