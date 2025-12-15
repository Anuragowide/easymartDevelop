import { FastifyInstance } from "fastify";
import { config } from "../../../config";

export default async function healthRoute(app: FastifyInstance) {
  app.get("/health", async () => ({
    status: "ok",
    service: "node-backend",
    environment: config.NODE_ENV,
    timestamp: new Date().toISOString(),
    pythonBackend: config.PYTHON_BASE_URL,
    shopifyConfigured: !!config.SHOPIFY_ACCESS_TOKEN,
  }));
}
