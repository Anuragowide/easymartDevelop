I will now generate all Node.js backend code, file-by-file, exactly matching your structure, with full wiring, module connections, interfaces, routes, services, and integration with the Python Assistant.

⚠️ I will NOT generate the Python logic, but I will show exactly how your Node backend should call the Python service, so you can plug in the Python team’s API later.

You will be ready to paste these files into VS Code and run the Node backend today.

TECH STACK ASSUMED FOR BACKEND-NODE:
Node.js + TypeScript
Fastify (preferred for speed) — If you want Express, I can switch.
Axios for calling Python + Shopify
Module-based folder structure (clean architecture)

1. ENTRY FILE — src/index.ts:
import { startServer } from "./server";

startServer()
  .then(() => console.log("⚡ Easymart Node backend started"))
  .catch((err) => {
    console.error("❌ Failed to start server", err);
    process.exit(1);
  });

2. SERVER BOOT FILE — src/server.ts:
import Fastify from "fastify";
import { registerWebModule } from "./modules/web/web.module";
import { config } from "./config";

export async function startServer() {
  const fastify = Fastify({
    logger: true,
  });

  // Register modules
  registerWebModule(fastify);

  // Health check
  fastify.get("/health", async () => ({ status: "ok" }));

  // Start
  await fastify.listen({
    port: config.PORT,
    host: "0.0.0.0",
  });

  console.log(`🚀 Server running on port ${config.PORT}`);
}

3. CONFIG FILE — src/config/env.ts:
import dotenv from "dotenv";
dotenv.config();

export const config = {
  PORT: Number(process.env.PORT || 3001),

  // Python Assistant API
  PYTHON_BASE_URL: process.env.PYTHON_BASE_URL || "http://python-app:8000",

  // Shopify credentials
  SHOPIFY_STORE_DOMAIN: process.env.SHOPIFY_STORE_DOMAIN!,
  SHOPIFY_ACCESS_TOKEN: process.env.SHOPIFY_ACCESS_TOKEN!,
  SHOPIFY_API_VERSION: process.env.SHOPIFY_API_VERSION || "2024-01",
};

4. WEB MODULE — src/modules/web/web.module.ts:
import { FastifyInstance } from "fastify";
import chatRoute from "./routes/chat.route";
import healthRoute from "./routes/health.route";
import widgetRoute from "./routes/widget.route";

export function registerWebModule(app: FastifyInstance) {
  app.register(chatRoute, { prefix: "/api/chat" });
  app.register(healthRoute, { prefix: "/api" });
  app.register(widgetRoute, { prefix: "/widget" });
}

5. Chat Route — src/modules/web/routes/chat.route.ts

This is the MOST IMPORTANT wiring file —
//This is where your Node backend → Python Assistant integration happens.
import { FastifyInstance } from "fastify";
import { pythonAssistantClient } from "../../../utils/pythonClient";

export default async function chatRoute(app: FastifyInstance) {
  app.post("/", async (req: any, reply) => {
    const { message, sessionId } = req.body;

    if (!message) {
      return reply.status(400).send({ error: "message is required" });
    }

    const response = await pythonAssistantClient.sendMessage({
      message,
      sessionId,
    });

    return reply.send(response);
  });
}

6. Health Route — src/modules/web/routes/health.route.ts:
import { FastifyInstance } from "fastify";

export default async function healthRoute(app: FastifyInstance) {
  app.get("/health", async () => ({
    status: "ok",
    service: "node-backend",
  }));
}

7. Widget Route — src/modules/web/routes/widget.route.ts:
import { FastifyInstance } from "fastify";
import path from "path";

export default async function widgetRoute(app: FastifyInstance) {
  app.get("/script.js", async (req, reply) => {
    reply.type("application/javascript");
    return reply.sendFile("chat-widget.js", path.join(__dirname, "../ui"));
  });

  app.get("/style.css", async (req, reply) => {
    reply.type("text/css");
    return reply.sendFile("chat-widget.css", path.join(__dirname, "../ui"));
  });
}

8. Chat Widget Script (Embeds on Shopify Store)

src/modules/web/ui/chat-widget.js:
(function () {
  const backendUrl = "https://your-node-backend-domain.com/api/chat";

  function createChatUI() {
    const box = document.createElement("div");
    box.id = "easymart-chat-box";
    box.innerHTML = `
      <div class="chat-header">Easymart Assistant</div>
      <div class="chat-body" id="chatBody"></div>
      <input id="chatInput" placeholder="Ask for products..."/>
    `;
    document.body.appendChild(box);

    const input = document.getElementById("chatInput");
    input.addEventListener("keydown", async (e) => {
      if (e.key === "Enter") {
        const userMessage = e.target.value;
        e.target.value = "";
        appendMessage("user", userMessage);

        const res = await fetch(backendUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            sessionId: localStorage.getItem("sessionId") || "guest-123",
            message: userMessage,
          }),
        });
        const data = await res.json();
        appendMessage("assistant", data.replyText);
      }
    });
  }

  function appendMessage(sender, text) {
    const body = document.getElementById("chatBody");
    const p = document.createElement("p");
    p.className = sender;
    p.textContent = text;
    body.appendChild(p);
  }

  createChatUI();
})();

9. Shopify Adapter — Main Index

src/modules/shopify_adapter/index.ts:
export * from "./products";
export * from "./cart";

10. Shopify API Client 
— src/modules/shopify_adapter/client.ts:
import axios from "axios";
import { config } from "../../config";

export const shopifyClient = axios.create({
  baseURL: `https://${config.SHOPIFY_STORE_DOMAIN}/admin/api/${config.SHOPIFY_API_VERSION}`,
  headers: {
    "X-Shopify-Access-Token": config.SHOPIFY_ACCESS_TOKEN,
    "Content-Type": "application/json",
  },
});


11. Shopify Product Service — 
src/modules/shopify_adapter/products.ts:
import { shopifyClient } from "./client";

export async function getProductDetails(productId: string) {
  const { data } = await shopifyClient.get(`/products/${productId}.json`);
  return data.product;
}

export async function searchProducts(query: string) {
  const { data } = await shopifyClient.get(`/products.json`, {
    params: { title: query },
  });
  return data.products;
}

12. Shopify Cart Service — 
src/modules/shopify_adapter/cart.ts:
import { shopifyClient } from "./client";

export async function addToCart(sessionId: string, productId: string, qty = 1) {
  const { data } = await shopifyClient.post(`/cart/add.js`, {
    id: productId,
    quantity: qty,
  });
  return data;
}

export async function getCart(sessionId: string) {
  const { data } = await shopifyClient.get(`/cart.js`);
  return data;
}

13. Python Assistant Client (HTTP Caller)

src/utils/pythonClient.ts:
import axios from "axios";
import { config } from "../config/env";

export const pythonAssistantClient = {
  async sendMessage({ message, sessionId }: { message: string; sessionId: string }) {
    const res = await axios.post(`${config.PYTHON_BASE_URL}/assistant/message`, {
      message,
      sessionId,
    });

    return res.data;
  },
};

14. Session Helper 
— src/utils/session.ts:
export function getSessionId(headers: any): string {
  return headers["x-session-id"] || "guest-session";
}

15. Node Logging 
— src/modules/observability/logger.ts:
export const logger = {
  info: (msg: string, data?: any) => console.log("INFO:", msg, data || ""),
  error: (msg: string, data?: any) => console.error("ERROR:", msg, data || ""),
};

###################################

NOW — NODE BACKEND DEPENDENCIES (List + Install Commands)

Go inside:
cd easymart-v1/backend-node
Then run:

A. Core dependencies

1. Fastify (web server):
npm install fastify
2. Axios (for calling Python + Shopify):
npm install axios
3. Dotenv (load .env):
npm install dotenv
4. Fastify Static (for serving widget JS/CSS):
npm install @fastify/static


B. TypeScript dependencies

npm install --save-dev typescript ts-node @types/node @types/axios @types/fastify

Initialize TS:
npx tsc --init

C. Linting & formatting (recommended)
npm install --save-dev eslint prettier @typescript-eslint/parser @typescript-eslint/eslint-plugin

D. Optional but recommended
Node fetch alternative
-npm install node-fetch

uuid for session IDs:
-npm install uuid

cookie parser (if needed):
-npm install cookie-parser

SUMMARY: Full Dependency List
Runtime Dependencies

fastify

axios

dotenv

@fastify/static

uuid (optional)

Dev Dependencies

typescript

ts-node

@types/node

@types/fastify

@types/axios

eslint

prettier

:- MUST CREATE THESE DIRECTORIES BEFORE CODING

Inside backend-node:
src/
  modules/
    web/
      routes/
      ui/
    shopify_adapter/
    observability/
  utils/
  config/

This avoids “path not found” errors when pasting my code.

