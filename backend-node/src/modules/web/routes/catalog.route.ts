import { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { getAllProducts } from "../../shopify_adapter/products";
import { logger } from "../../observability/logger";
import { config } from "../../../config";

interface NormalizedProduct {
  sku: string;
  title: string;
  description: string;
  price: number;
  currency: string;
  category: string;
  tags: string[];
  image_url?: string;
  vendor: string;
  handle: string;
  product_url: string;
  specs?: Record<string, any>;
  stock_status?: string;
}

/**
 * Normalize Shopify product to internal catalog format
 */
function normalizeShopifyProduct(product: any): NormalizedProduct {
  const firstVariant = product.variants?.[0] || {};
  const firstImage = product.images?.[0];

  return {
    sku: firstVariant.sku || product.handle,
    title: product.title,
    description: product.body_html?.replace(/<[^>]*>/g, "") || "", // Strip HTML
    price: parseFloat(firstVariant.price || "0"),
    currency: "AUD",
    category: product.product_type || "General",
    tags: product.tags ? product.tags.split(", ") : [],
    image_url: firstImage?.src,
    vendor: product.vendor || "EasyMart",
    handle: product.handle,
    product_url: `https://${config.SHOPIFY_STORE_DOMAIN}/products/${product.handle}`,
    stock_status: firstVariant.inventory_quantity > 0 ? "in_stock" : "out_of_stock",
    specs: {
      weight: firstVariant.weight,
      weight_unit: firstVariant.weight_unit,
      inventory_quantity: firstVariant.inventory_quantity,
      barcode: firstVariant.barcode,
    },
  };
}

export default async function catalogRoutes(fastify: FastifyInstance) {
  /**
   * GET /api/internal/catalog/export
   * Export all products in normalized format for Python catalog indexer
   */
  fastify.get("/api/internal/catalog/export", async (_request: FastifyRequest, reply: FastifyReply) => {
    try {
      logger.info("Catalog export requested");

      const allProducts = [];
      let sinceId: number | undefined = undefined;
      let hasMore = true;
      let pageCount = 0;
      const MAX_PAGES = 10; // Safety limit

      // Paginate through all products
      while (hasMore && pageCount < MAX_PAGES) {
        const products = await getAllProducts(250, sinceId);

        if (products.length === 0) {
          hasMore = false;
          break;
        }

        allProducts.push(...products);
        sinceId = products[products.length - 1].id;
        pageCount++;

        logger.info(`Fetched page ${pageCount}`, {
          productsInPage: products.length,
          totalSoFar: allProducts.length,
        });
      }

      // Normalize all products
      const normalized = allProducts.map(normalizeShopifyProduct);

      logger.info("Catalog export complete", {
        totalProducts: normalized.length,
        pagesProcessed: pageCount,
      });

      return reply.code(200).send(normalized);
    } catch (error: any) {
      logger.error("Catalog export failed", { error: error.message });
      return reply.code(500).send({
        error: "Failed to export catalog",
        message: error.message,
      });
    }
  });

  /**
   * GET /api/internal/catalog/stats
   * Get catalog statistics
   */
  fastify.get("/api/internal/catalog/stats", async (_request: FastifyRequest, reply: FastifyReply) => {
    try {
      const products = await getAllProducts(1);
      
      return reply.code(200).send({
        status: "available",
        sample_product: products[0] ? {
          id: products[0].id,
          title: products[0].title,
          handle: products[0].handle,
        } : null,
      });
    } catch (error: any) {
      logger.error("Catalog stats failed", { error: error.message });
      return reply.code(500).send({
        error: "Failed to get catalog stats",
        message: error.message,
      });
    }
  });
}
