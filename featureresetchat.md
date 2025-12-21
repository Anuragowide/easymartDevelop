# Feature: Chat Session Reset

This document details the implementation of the Chat Session Reset feature, which allows users to clear their conversation history and start a new session either via a UI button or by typing specific commands.

## Overview

The feature involves changes across the full stack:
- **Frontend**: Added a reset button, updated the chat store to handle session clearing, and updated API types.
- **Backend**: Added logic to intercept reset commands and pass a signal back to the frontend to trigger a client-side reset.

## Detailed Changes

### 1. Frontend: API Type Definition
**File:** `frontend/src/lib/api.ts`

Updated the `ChatResponse` interface to support arbitrary metadata from the backend. This allows the backend to send flags like `reset_session` without affecting the main message content.

```typescript
export interface ChatResponse {
  replyText: string;
  actions?: MessageAction[];
  sessionId: string;
  metadata?: Record<string, any>; // Added this field
}
```

### 2. Frontend: State Management
**File:** `frontend/src/store/chatStore.ts`

Updated the `sendMessage` action in the Zustand store to check for the `reset_session` flag in the API response.

- **Logic:**
    - If `response.metadata?.reset_session` is `true`:
        - Call `clearMessages()` to wipe local history and generate a new `sessionId`.
        - Add the assistant's confirmation message as the *first* message of the new session.
        - Stop processing (do not append the old response to the cleared list).

```typescript
// Inside sendMessage function:
const response: ChatResponse = await chatApi.sendMessage(text, sessionId);

// Check for session reset signal
if (response.metadata?.reset_session) {
  get().clearMessages(); // Generates new session ID and clears history
  
  // Add the reset confirmation as the first message of the new session
  const resetMessage: Message = {
    id: generateUUID(),
    role: 'assistant',
    content: response.replyText,
    timestamp: new Date().toISOString(),
  };
  
  set({
    messages: [resetMessage],
    isLoading: false
  });
  return;
}
```

### 3. Frontend: UI Components
**File:** `frontend/src/components/chat/ChatHeader.tsx`

Added a "Reset" button to the chat header.

- **Import:** Added `useChatStore`.
- **Button:** Added a button icon next to the close button that calls `clearMessages` when clicked.

```tsx
const { clearMessages } = useChatStore();

// Render:
<button
  onClick={clearMessages}
  className="..."
  aria-label="Reset chat"
  title="Reset conversation"
>
  <svg>...</svg>
</button>
```

### 4. Backend: Assistant Handler
**File:** `backend-python/app/modules/assistant/handler.py`

Modified `handle_message` to detect reset-related keywords *before* processing standard intents or calling the LLM.

- **Keywords:** "clear chat", "reset chat", "start over", "clear history", "clear session", "reset session", "clear all", "restart chat".
- **Action:**
    - If detected, return a predefined `AssistantResponse`.
    - Set `metadata={"reset_session": True}`.
    - Set `products=[]` (empty list).

```python
# CHECK FOR RESET/CLEAR COMMANDS
reset_keywords = ['clear chat', 'reset chat', 'start over', 'clear history', 'clear session', 'reset session', 'clear all', 'restart chat']
is_reset = any(keyword in message_lower for keyword in reset_keywords)

if is_reset:
    logger.info(f"[HANDLER] Reset command detected: {request.message}")
    return AssistantResponse(
        message="I've cleared our conversation history...",
        session_id=session.session_id,
        products=[],
        metadata={
            "intent": "system_reset",
            "reset_session": True, # Critical flag
            "entities": {},
            "function_calls_made": 0
        }
    )
```

### 5. Backend: API Endpoint
**File:** `backend-python/app/api/assistant_api.py`

Updated the endpoint to ensure the `reset_session` flag from the internal handler is correctly passed to the public API response.

```python
return MessageResponse(
    # ... other fields
    metadata={
        # ... other stats
        "reset_session": assistant_response.metadata.get("reset_session", False)
    }
)
```

## How it Works

1.  **Manual Reset (Button):**
    - User clicks the "Reset" icon in the header.
    - `clearMessages()` is called directly in the store.
    - Messages array is emptied, and a new Session ID is generated locally.

2.  **Conversational Reset (Command):**
    - User types "clear chat".
    - Backend receives message, detects intent.
    - Backend returns response with `reset_session: true` in metadata.
    - Frontend store sees the flag.
    - Frontend triggers `clearMessages()`.
    - Frontend displays the "History cleared" message as the start of the new session.
