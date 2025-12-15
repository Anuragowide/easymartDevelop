I produce these sections in order:
Remaining Node backend files (all missing files with content)
api-contracts.md content (human-readable API contract doc)
docker-compose.yml (Node + Python + Elasticsearch)
OpenAPI (YAML) contract for Node ⇄ Python (/assistant/message)
Shared schemas (TypeScript interfaces + Pydantic models / JSON Schema)
Dev-run instructions for VS Code (commands, launch.json, tasks.json)

1) Remaining Node backend files (paste-ready)

Place these files under easymart-v1/backend-node/ as indicated.
package.json:
{
  "name": "easymart-backend-node",
  "version": "0.1.0",
  "description": "Easymart Node Gateway + Shopify Adapter",
  "main": "dist/index.js",
  "scripts": {
    "dev": "ts-node-dev --respawn --transpile-only src/index.ts",
    "build": "tsc -p .",
    "start": "node dist/index.js",
    "lint": "eslint . --ext .ts",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "axios": "^1.4.0",
    "dotenv": "^16.0.0",
    "fastify": "^4.18.0",
    "@fastify/static": "^6.9.0",
    "uuid": "^9.0.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/fastify": "^4.6.0",
    "@types/axios": "^0.14.0",
    "ts-node-dev": "^2.0.0",
    "typescript": "^5.3.0",
    "eslint": "^8.0.0",
    "@typescript-eslint/parser": "^6.0.0",
    "@typescript-eslint/eslint-plugin": "^6.0.0",
    "prettier": "^2.8.0"
  }
}

tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "CommonJS",
    "lib": ["ES2020"],
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true
  },
  "include": ["src/**/*"]
}

.env.example:
# Node backend
PORT=3001
PYTHON_BASE_URL=http://localhost:8000

# Shopify (Custom App)
SHOPIFY_STORE_DOMAIN=your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_xxxxxxxxxxxxxxxxx
SHOPIFY_API_VERSION=2024-01

Dockerfile:
FROM node:20-alpine

WORKDIR /usr/src/app

COPY package.json package-lock.json* ./

RUN npm ci --only=production

COPY . .

RUN npm run build

EXPOSE 3001

CMD ["node", "dist/index.js"]
##

README.md (backend-node):
# Easymart - Node Backend

This service acts as the web and Shopify adapter layer. It forwards chat messages to the Python assistant and handles Shopify product/cart calls.

## Run (local)

1. Copy `.env.example` to `.env` and fill values.
2. Install:
   ```bash
   npm install
3. Start in dev:
pnpm run dev

4. Build:
pnpm run build
pnpm start

Endpoints:

POST /api/chat — proxy to Python assistant
GET /api/health — health check
GET /widget/script.js — chat widget script
GET /widget/style.css — chat widget css

---

## `src/config/index.ts` (wrapper)
```ts
import { config as envConfig } from "./env";
export const config = envConfig;
(We already had env.ts earlier — keep both; env.ts loads dotenv.)

src/utils/httpClient.ts:
import axios, { AxiosInstance } from "axios";

export function createHttpClient(baseURL?: string): AxiosInstance {
  const instance = axios.create({
    baseURL,
    timeout: 15_000,
    headers: {
      "Content-Type": "application/json",
    },
  });

  instance.interceptors.response.use(
    (res) => res,
    (err) => {
      // Basic error translation
      throw err;
    }
  );

  return instance;
}

src/modules/web/routes/index.ts (optional aggregator)
import chatRoute from "./chat.route";
import healthRoute from "./health.route";
import widgetRoute from "./widget.route";

export default function routes(fastify) {
  fastify.register(chatRoute, { prefix: "/api/chat" });
  fastify.register(healthRoute, { prefix: "/api" });
  fastify.register(widgetRoute, { prefix: "/widget" });
}

Update src/server.ts to serve static files and register modules

Replace previous server.ts with this full version:
import Fastify from "fastify";
import path from "path";
import fastifyStatic from "@fastify/static";
import { registerWebModule } from "./modules/web/web.module";
import { config } from "./config";

export async function startServer() {
  const fastify = Fastify({
    logger: true,
  });

  // Serve static UI assets under /widget/static (chat widget)
  fastify.register(fastifyStatic, {
    root: path.join(__dirname, "modules/web/ui"),
    prefix: "/widget/static/",
  });

  // Register web module (routes)
  registerWebModule(fastify);

  // Generic health (already in module too)
  fastify.get("/health", async () => ({ status: "ok", service: "node-backend" }));

  const port = Number(config.PORT || 3001);
  await fastify.listen({
    port,
    host: "0.0.0.0",
  });

  fastify.log.info(`🚀 Node backend listening on port ${port}`);
}
Note: widget route can reference GET /widget/static/chat-widget.js (because we registered fastify-static). The earlier widget.route.ts that used sendFile can be simplified — current approach exposes static files directly.

src/modules/web/ui/chat-widget.css
#easymart-chat-box { position: fixed; right: 24px; bottom: 24px; width: 320px; max-width: calc(100% - 48px); background:#fff; border-radius:8px; box-shadow:0 6px 24px rgba(0,0,0,0.12); overflow:hidden; font-family: Arial, sans-serif; z-index: 999999; }
#easymart-chat-box .chat-header { padding: 12px; font-weight: 600; background:#0b6cf5; color:#fff; }
#easymart-chat-box .chat-body { max-height: 320px; overflow:auto; padding:12px; }
#easymart-chat-box input { width: calc(100% - 24px); margin: 8px 12px; padding:8px; border:1px solid #ddd; border-radius:6px; }
#easymart-chat-box p.user { text-align:right; color:#111; margin:8px 0; }
#easymart-chat-box p.assistant { text-align:left; color:#111; margin:8px 0; }

src/modules/web/ui/chat-widget.js (update to use static path)
(function () {
  const backendUrl = (function() {
    try { return window.EASYMART_BACKEND_URL || "http://localhost:3001/api/chat"; } catch(e) { return "http://localhost:3001/api/chat"; }
  })();

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
        const userMessage = e.target.value.trim();
        if (!userMessage) return;
        e.target.value = "";
        appendMessage("user", userMessage);
        try {
          const res = await fetch(backendUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              sessionId: localStorage.getItem("easymart-session") || generateSessionId(),
              message: userMessage,
            }),
          });
          const data = await res.json();
          appendMessage("assistant", data.replyText || JSON.stringify(data));
        } catch (err) {
          appendMessage("assistant", "Sorry — the assistant is unavailable.");
        }
      }
    });
  }

  function appendMessage(sender, text) {
    const body = document.getElementById("chatBody");
    const p = document.createElement("p");
    p.className = sender;
    p.textContent = text;
    body.appendChild(p);
    body.scrollTop = body.scrollHeight;
  }

  function generateSessionId() {
    const id = 'sess-' + Math.random().toString(36).substring(2, 10);
    try { localStorage.setItem("easymart-session", id); } catch(e) {}
    return id;
  }

  createChatUI();
})();

src/modules/shopify_adapter/index.ts (already exported earlier; ensure path)

(Already provided)

src/modules/observability/index.ts
export * from "./logger";


src/utils/pythonClient.ts (update with axios instance)
import axios from "axios";
import { config } from "../config";

const client = axios.create({
  baseURL: config.PYTHON_BASE_URL,
  timeout: 20000,
  headers: { "Content-Type": "application/json" },
});

export const pythonAssistantClient = {
  async sendMessage(payload: { message: string; sessionId?: string }) {
    const res = await client.post("/assistant/message", payload);
    return res.data;
  },
};

That covers the missing Node-side files and wiring. If you want, I can prepare a .prettierrc and .eslintrc next.

