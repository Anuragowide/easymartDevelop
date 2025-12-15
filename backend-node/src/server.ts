import Fastify from "fastify";
import fastifyStatic from "@fastify/static";
import path from "path";
import { registerWebModule } from "./modules/web/web.module";
import { config } from "./config";
import { logger } from "./modules/observability/logger";

export async function startServer() {
  const fastify = Fastify({
    logger: {
      level: config.NODE_ENV === "production" ? "info" : "debug",
    },
  });

  // Register static file serving for widget
  await fastify.register(fastifyStatic, {
    root: path.join(__dirname, "modules/web/ui"),
    prefix: "/widget/",
  });

  // Register modules
  await registerWebModule(fastify);

  // Global health check
  fastify.get("/health", async () => ({
    status: "ok",
    service: "easymart-node-backend",
    timestamp: new Date().toISOString(),
  }));

  // Error handler
  fastify.setErrorHandler((error, request, reply) => {
    logger.error("Request error", { error: error.message, path: request.url });
    reply.status(500).send({ error: "Internal Server Error" });
  });

  // Start server
  try {
    await fastify.listen({
      port: config.PORT,
      host: "0.0.0.0",
    });
    logger.info(`🚀 Server running on port ${config.PORT}`);
  } catch (err) {
    logger.error("Failed to start server", err);
    throw err;
  }

  return fastify;
}
