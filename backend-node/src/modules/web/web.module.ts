import { FastifyInstance } from "fastify";
import chatRoute from "./routes/chat.route";
import healthRoute from "./routes/health.route";

export async function registerWebModule(app: FastifyInstance) {
  await app.register(chatRoute, { prefix: "/api/chat" });
  await app.register(healthRoute, { prefix: "/api" });
  // Widget static files are served by @fastify/static in server.ts
}
