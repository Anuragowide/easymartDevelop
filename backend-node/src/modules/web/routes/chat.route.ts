import { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { pythonAssistantClient } from "../../../utils/pythonClient";
import { logger } from "../../observability/logger";

interface ChatRequestBody {
  message: string;
  sessionId?: string;
}

export default async function chatRoute(app: FastifyInstance) {
  app.post("/", async (req: FastifyRequest<{ Body: ChatRequestBody }>, reply: FastifyReply) => {
    const { message, sessionId } = req.body;

    // Validate request
    if (!message || typeof message !== "string") {
      return reply.status(400).send({ error: "message is required and must be a string" });
    }

    // Generate session ID if not provided
    const session = sessionId || `guest-${Date.now()}`;

    logger.info("Chat request received", { sessionId: session, messageLength: message.length });

    try {
      // Forward to Python assistant
      const response = await pythonAssistantClient.sendMessage({
        message,
        sessionId: session,
      });

      logger.info("Chat response sent", { sessionId: session });
      return reply.send(response);
    } catch (error: any) {
      logger.error("Error calling Python assistant", { 
        error: error.message, 
        sessionId: session 
      });
      
      return reply.status(500).send({ 
        error: "Failed to process message",
        message: "Our assistant is temporarily unavailable. Please try again."
      });
    }
  });
}
