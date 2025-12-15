(function () {
  // Configuration - Replace with your actual backend URL
  const backendUrl = window.EASYMART_BACKEND_URL || "http://localhost:3001/api/chat";
  
  // Session management
  const SESSION_KEY = "easymart_session_id";
  let sessionId = localStorage.getItem(SESSION_KEY);
  if (!sessionId) {
    sessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    localStorage.setItem(SESSION_KEY, sessionId);
  }

  // State
  let isOpen = false;
  let messages = [];

  // Create chat UI
  function createChatUI() {
    const container = document.createElement("div");
    container.id = "easymart-chat-container";
    container.innerHTML = `
      <div id="easymart-chat-toggle" class="easymart-chat-toggle">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
      </div>
      <div id="easymart-chat-box" class="easymart-chat-box" style="display: none;">
        <div class="easymart-chat-header">
          <span>Shopping Assistant</span>
          <button id="easymart-chat-close" class="easymart-close-btn">&times;</button>
        </div>
        <div id="easymart-chat-body" class="easymart-chat-body">
          <div class="easymart-welcome-message">
            👋 Hi! I'm your shopping assistant. How can I help you today?
          </div>
        </div>
        <div class="easymart-chat-input-container">
          <input 
            id="easymart-chat-input" 
            class="easymart-chat-input" 
            placeholder="Ask about products..."
            autocomplete="off"
          />
          <button id="easymart-send-btn" class="easymart-send-btn">Send</button>
        </div>
      </div>
    `;
    document.body.appendChild(container);

    // Event listeners
    document.getElementById("easymart-chat-toggle").addEventListener("click", toggleChat);
    document.getElementById("easymart-chat-close").addEventListener("click", toggleChat);
    document.getElementById("easymart-send-btn").addEventListener("click", sendMessage);
    document.getElementById("easymart-chat-input").addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        sendMessage();
      }
    });
  }

  // Toggle chat visibility
  function toggleChat() {
    isOpen = !isOpen;
    const chatBox = document.getElementById("easymart-chat-box");
    const toggle = document.getElementById("easymart-chat-toggle");
    
    if (isOpen) {
      chatBox.style.display = "flex";
      toggle.style.display = "none";
    } else {
      chatBox.style.display = "none";
      toggle.style.display = "flex";
    }
  }

  // Send message
  async function sendMessage() {
    const input = document.getElementById("easymart-chat-input");
    const userMessage = input.value.trim();
    
    if (!userMessage) return;

    // Clear input
    input.value = "";

    // Add user message
    appendMessage("user", userMessage);

    // Show typing indicator
    const typingId = showTypingIndicator();

    try {
      const response = await fetch(backendUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sessionId: sessionId,
          message: userMessage,
        }),
      });

      removeTypingIndicator(typingId);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      // Handle response
      const replyText = data.replyText || data.message || "Sorry, I couldn't process that.";
      appendMessage("assistant", replyText);

      // Handle actions (e.g., product cards)
      if (data.actions) {
        handleActions(data.actions);
      }
    } catch (error) {
      removeTypingIndicator(typingId);
      console.error("Chat error:", error);
      appendMessage("assistant", "Sorry, I'm having trouble connecting. Please try again.");
    }
  }

  // Append message to chat
  function appendMessage(sender, text) {
    const body = document.getElementById("easymart-chat-body");
    const messageDiv = document.createElement("div");
    messageDiv.className = `easymart-message easymart-message-${sender}`;
    
    const bubble = document.createElement("div");
    bubble.className = "easymart-message-bubble";
    bubble.textContent = text;
    
    messageDiv.appendChild(bubble);
    body.appendChild(messageDiv);
    
    // Scroll to bottom
    body.scrollTop = body.scrollHeight;
    
    messages.push({ sender, text, timestamp: Date.now() });
  }

  // Show typing indicator
  function showTypingIndicator() {
    const body = document.getElementById("easymart-chat-body");
    const typingDiv = document.createElement("div");
    const typingId = `typing-${Date.now()}`;
    typingDiv.id = typingId;
    typingDiv.className = "easymart-message easymart-message-assistant";
    typingDiv.innerHTML = `
      <div class="easymart-message-bubble easymart-typing">
        <span></span><span></span><span></span>
      </div>
    `;
    body.appendChild(typingDiv);
    body.scrollTop = body.scrollHeight;
    return typingId;
  }

  // Remove typing indicator
  function removeTypingIndicator(typingId) {
    const typingDiv = document.getElementById(typingId);
    if (typingDiv) {
      typingDiv.remove();
    }
  }

  // Handle actions (product cards, etc.)
  function handleActions(actions) {
    const body = document.getElementById("easymart-chat-body");
    
    actions.forEach(action => {
      if (action.type === "product_card") {
        const card = createProductCard(action.data);
        body.appendChild(card);
      }
    });
    
    body.scrollTop = body.scrollHeight;
  }

  // Create product card
  function createProductCard(product) {
    const card = document.createElement("div");
    card.className = "easymart-product-card";
    card.innerHTML = `
      <img src="${product.image}" alt="${product.title}" />
      <div class="easymart-product-info">
        <h4>${product.title}</h4>
        <p class="easymart-product-price">${product.price}</p>
        <a href="${product.url}" target="_blank" class="easymart-product-link">View Product</a>
      </div>
    `;
    return card;
  }

  // Initialize
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", createChatUI);
  } else {
    createChatUI();
  }
})();
