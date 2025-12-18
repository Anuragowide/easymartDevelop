import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { logger } from '../../../modules/observability/logger';
import { pythonAssistantClient } from '../../../utils/pythonClient';

interface CartRequestBody {
  product_id: string;
  quantity?: number;
  action?: 'add' | 'remove' | 'set';
  session_id: string;
}

interface CartQuerystring {
  session_id: string;
}

export default async function cartRoutes(fastify: FastifyInstance) {
  /**
   * POST /api/cart/add
   * Add item to cart
   */
  fastify.post('/api/cart/add', async (request: FastifyRequest<{ Body: CartRequestBody }>, reply: FastifyReply) => {
    try {
      const { product_id, quantity = 1, session_id } = request.body;

      if (!product_id || !session_id) {
        return reply.code(400).send({
          success: false,
          error: 'product_id and session_id are required'
        });
      }

      logger.info('Adding to cart', { product_id, quantity, session_id });

      // Forward to Python backend
      const response = await pythonAssistantClient.request(
        'POST',
        '/assistant/cart',
        {
          product_id,
          quantity,
          action: 'add',
          session_id
        }
      );

      return reply.send(response.data);
    } catch (error: any) {
      logger.error('Cart add error:', error);
      return reply.code(500).send({
        success: false,
        error: error.message || 'Failed to add to cart'
      });
    }
  });

  /**
   * GET /api/cart
   * Get cart contents
   */
  fastify.get('/api/cart', async (request: FastifyRequest<{ Querystring: CartQuerystring }>, reply: FastifyReply) => {
    try {
      const { session_id } = request.query;

      if (!session_id) {
        return reply.code(400).send({
          success: false,
          error: 'session_id is required'
        });
      }

      // Get session cart from Python backend
      const response = await pythonAssistantClient.request(
        'POST',
        '/assistant/message',
        {
          message: 'show cart',
          session_id
        }
      );

      return reply.send({
        success: true,
        cart: response.data.cart || { items: [], item_count: 0, total: 0 }
      });
    } catch (error: any) {
      logger.error('Cart get error:', error);
      return reply.code(500).send({
        success: false,
        error: error.message || 'Failed to get cart'
      });
    }
  });
}
