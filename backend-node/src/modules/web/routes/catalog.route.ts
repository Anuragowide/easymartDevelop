import { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { logger } from "../../observability/logger";
import { config } from "../../../config";
import * as shopify from "../../shopify_adapter";
import { createSalesforceAdapter } from "../../salesforce_adapter";

// Normalizer for Shopify products (keeps existing behavior)
function normalizeShopifyProduct(product: any) {
  const firstVariant = product.variants?.[0] || {};
  const firstImage = product.images?.[0];
  const inventoryManaged = firstVariant.inventory_management !== null;
  const inventoryQuantity = firstVariant.inventory_quantity || 0;
  const isInStock = !inventoryManaged || inventoryQuantity > 0;
  const reportedQuantity = inventoryManaged ? inventoryQuantity : 999;

  return {
    sku: firstVariant.sku || product.handle,
    title: product.title,
    description: product.body_html?.replace(/<[^>]*>/g, "") || "",
    price: parseFloat(firstVariant.price || "0"),
    compare_at_price: parseFloat(firstVariant.compare_at_price || "0") || undefined,
    currency: "AUD",
    category: product.product_type || "General",
    product_type: product.product_type || "General",
    tags: product.tags ? product.tags.split(", ") : [],
    image_url: firstImage?.src,
    vendor: product.vendor || "EasyMart",
    handle: product.handle,
    product_url: `https://${config.SHOPIFY_STORE_DOMAIN}/products/${product.handle}`,
    stock_status: isInStock ? "in_stock" : "out_of_stock",
    status: product.status,
    options: product.options || [],
    variants: product.variants || [],
    images: product.images || [],
    available: typeof firstVariant.available === "boolean" ? firstVariant.available : isInStock,
    inventory_managed: inventoryManaged,
    barcode: firstVariant.barcode,
    specs: {
      weight: firstVariant.weight,
      weight_unit: firstVariant.weight_unit,
      inventory_quantity: reportedQuantity,
      inventory_managed: inventoryManaged,
      barcode: firstVariant.barcode,
      specifications: product.body_html?.replace(/<[^>]*>/g, "") || "",
      features: product.tags,
      material: product.options?.find((o: any) => o.name === "Material")?.values?.join(", "),
      options: product.options,
      variants: product.variants,
      images: product.images,
      raw_body_html: product.body_html
    },
  };
}

// Minimal in-file adapter selector (singleton)
// Replace getAdapter() with this block
let _adapter: any = null;
function getAdapter() {
  if (_adapter) return _adapter;
  const active = (config.ACTIVE_PLATFORM || "shopify").toLowerCase();

  if (active === "salesforce") {
    const sfConfig = {
      tokenUrl: config.SALESFORCE_TOKEN_URL,
      clientId: config.SALESFORCE_JWT_CLIENT_ID || config.SALESFORCE_CLIENT_ID,
      jwtUsername: config.SALESFORCE_JWT_USERNAME,
      jwtPrivateKey: config.SALESFORCE_JWT_PRIVATE_KEY,
      username: config.SALESFORCE_USERNAME,
      password: config.SALESFORCE_PASSWORD,
      securityToken: config.SALESFORCE_SECURITY_TOKEN,
      apiVersion: config.SALESFORCE_API_VERSION || "v57.0",
      siteBaseUrl: config.SALESFORCE_SITE_BASE_URL,
      webstoreId: config.SALESFORCE_WEBSTORE_ID,
    };
    const sf = createSalesforceAdapter({ config: sfConfig });
    _adapter = {
      products: {
        search: (q: string, limit = 10) => sf.products.search(q, limit),
        getById: (id: string) => sf.products.getById(id),
      },
      cart: {
        getCart: (id: string) => sf.cart.getCart(id),
        addToCart: (p: string, q: number, id: string) => sf.cart.addToCart(p, q, id),
        updateCartItem: (cartItemId: string, qty: number, id: string) => sf.cart.updateCartItem(cartItemId, qty, id),
        removeFromCart: (cartItemId: string, id: string) => sf.cart.removeFromCart(cartItemId, id),
      },
      client: sf.client,
    };
  } else {
    _adapter = {
      products: {
        search: shopify.searchProducts,
        getById: shopify.getProductDetails,
        getAllProducts: shopify.getAllProducts,
      },
      cart: {
        getCart: shopify.getCart,
        addToCart: shopify.addToCart,
        updateCartItem: shopify.updateCartItem,
        removeFromCart: (sessionId: string, variantId: number) => shopify.removeFromCart(sessionId, variantId),
        clearCart: shopify.clearCart,
      },
      client: (shopify as any).shopifyClient,
    };
  }

  return _adapter;
}

export default async function catalogRoutes(fastify: FastifyInstance) {
  fastify.get("/api/internal/catalog/export", async (_request: FastifyRequest, reply: FastifyReply) => {
    try {
      logger.info("Catalog export requested");
      const adapter = getAdapter();
      const active = (config.ACTIVE_PLATFORM || "shopify").toLowerCase();

      if (active === "shopify" && adapter.products.getAllProducts) {
        // Shopify paging logic
        let sinceId: number | undefined = undefined;
        let hasMore = true;
        let pageCount = 0;
        const MAX_PAGES = 10;
        const allProducts: any[] = [];
        while (hasMore && pageCount < MAX_PAGES) {
          const products: any[] = await adapter.products.getAllProducts(250, sinceId);
          if (!products || products.length === 0) {
            hasMore = false;
            break;
          }
          allProducts.push(...products.map((p: any) => normalizeShopifyProduct(p)));
          sinceId = products[products.length - 1].id;
          pageCount++;
        }
        return reply.send({ products: allProducts });
      } else {
        // For Salesforce, use POST route
        return reply.code(400).send({ error: "Salesforce export should use POST" });
      }
    } catch (error: any) {
      logger.error("Catalog stats failed", { error: error.message });
      return reply.code(500).send({ error: "Failed to get catalog stats", message: error.message });
    }
  });

  // Debug: forward arbitrary body to Salesforce search (returns raw Apex response)
  fastify.post("/api/internal/catalog/debug-search", async (request: FastifyRequest, reply: FastifyReply) => {
    try {
      const adapter = getAdapter();
      const active = (config.ACTIVE_PLATFORM || "shopify").toLowerCase();
      const body = (request.body as any) || {};
      logger.info("Debug search requested", { body });
      if (active === "shopify" && adapter.products.getAllProducts) {
        // Shopify paging logic
        let sinceId: number | undefined = undefined;
        let hasMore = true;
        let pageCount = 0;
        const MAX_PAGES = 10;
        const allProducts: any[] = [];
        while (hasMore && pageCount < MAX_PAGES) {
          const products: any[] = await adapter.products.getAllProducts(250, sinceId);
          if (!products || products.length === 0) {
            hasMore = false;
            break;
          }
          allProducts.push(...products.map((p: any) => normalizeShopifyProduct(p)));
          sinceId = products[products.length - 1].id;
          pageCount++;
        }
        return reply.send({ products: allProducts });
      } else {
        // Forward to Python Salesforce search endpoint
        const { query, page = 1, pageSize = 10 } = body;
        const axios = adapter.client.getAxios();
        try {
          const resp = await axios.post(
            `${config.PYTHON_BASE_URL}/internal/salesforce/search`,
            { query, page, pageSize }
          );
          return reply.code(resp.status).send(resp.data);
        } catch (err: any) {
          logger.error("Debug search failed", {
            error: err?.message || String(err),
            upstreamStatus: err?.response?.status,
            upstreamBody: err?.response?.data,
          });
          return reply.code(err?.response?.status || 500).send({ error: err?.message || String(err), upstream: err?.response?.data });
        }
      }
    } catch (err: any) {
      logger.error("Debug product failed", { error: err?.message || String(err) });
      return reply.code(500).send({ error: err?.message || String(err) });
    }
  });

  // POST: Salesforce export with query
  fastify.post("/api/internal/catalog/export", async (request: FastifyRequest, reply: FastifyReply) => {
    try {
      const adapter = getAdapter();
      const active = (config.ACTIVE_PLATFORM || "shopify").toLowerCase();
      if (active === "salesforce") {
        const { query, page = 1, pageSize = 10 } = (request.body as any) || {};
        // Forward to Python Salesforce exporter using GET (Python expects GET /export)
        const axios = adapter.client.getAxios();
        const resp = await axios.get(`${config.PYTHON_BASE_URL}/internal/salesforce/export`, {
          params: { query, page, pageSize },
        });
        return reply.code(resp.status).send(resp.data);
      } else {
        // For Shopify, fallback to GET logic or error
        return reply.code(400).send({ error: "Shopify export should use GET" });
      }
    } catch (err: any) {
      logger.error("POST catalog export failed", {
        error: err?.message || String(err),
        upstreamStatus: err?.response?.status,
        upstreamBody: err?.response?.data,
      });
      return reply.code(err?.response?.status || 500).send({ error: err?.message || String(err), upstream: err?.response?.data });
    }
  });
}
