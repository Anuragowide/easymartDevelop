import { FastifyInstance } from "fastify";
import chatRoute from "./routes/chat.route";
import healthRoute from "./routes/health.route";
import catalogRoute from "./routes/catalog.route";
import cartRoute from "./routes/cart.route";

export async function registerWebModule(app: FastifyInstance) {
  await app.register(chatRoute, { prefix: "/api/chat" });
  await app.register(healthRoute, { prefix: "/api" });
  await app.register(catalogRoute); // Internal catalog endpoints
  await app.register(cartRoute); // Cart endpoints
  // Widget static files are served by @fastify/static in server.ts
}
