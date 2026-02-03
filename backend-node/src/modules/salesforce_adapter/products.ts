import { SalesforceClient } from "./client";
import { Logger } from "./types";
import { config as envConfig } from "../../config";

// Normalized Product shape (matches what Python backend expects)
export interface Product {
  id: string;
  title: string;
  description?: string;
  price: string;
  image?: string;
  url?: string;
  inStock?: boolean;
  inventory_quantity?: number;
}

const defaultLogger: Logger = {
  debug: () => {},
  info: console.log,
  warn: console.warn,
  error: (msg: any) => console.error(msg),
};

export class ProductService {
  private client: SalesforceClient;
  private logger: Logger;

  constructor(client: SalesforceClient, logger?: Logger) {
    this.client = client;
    this.logger = logger || defaultLogger;
  }

  async search(query: string, limit = 10): Promise<Product[]> {
    const axios = this.client.getAxios();
    const config = this.client.getConfig();

    const PAGE_SIZE = 50;
    const pageSize = Math.min(PAGE_SIZE, Math.max(1, limit > PAGE_SIZE ? PAGE_SIZE : limit));
    let page = 1;
    const out: Product[] = [];
    const seen = new Set<string>();

    const normalize = (p: any): Product => {
      const id = p.id || p.Id || p.Id__c || (p.SKU && `${p.SKU}`) || undefined;
      const title = p.name || p.title || p.Name || "";
      const priceObj = p.price || p.pricebookEntry || p.pricebookEntry?.UnitPrice || p.UnitPrice;
      const amount = typeof priceObj === "object" ? (priceObj.amount ?? priceObj.UnitPrice ?? 0) : (priceObj ?? p.UnitPrice ?? 0);
      const images = Array.isArray(p.images) ? p.images : (p.images?.map?.((i:any)=> typeof i === "string" ? { url: i } : i) || []);
      return {
        id: id || `${title}-${Math.random().toString(36).slice(2,8)}`,
        title,
        description: p.description || p.Description || "",
        price: String(amount ?? 0),
        image: images[0]?.url || "",
        url: p.url || p.ProductUrl || `${config.siteBaseUrl || ""}/product/${id || ""}`,
        inStock: p.inventory?.available ?? (p.IsAvailable ?? true),
        inventory_quantity: p.inventory?.quantity ?? p.QuantityAvailable ?? 0,
      };
    };

    while (out.length < limit) {
      const body = { query: query ?? "", pageSize, page };
      const resp = await axios.post(
        `${envConfig.PYTHON_BASE_URL}/internal/salesforce/search`,
        body
      );

      const data = resp.data || {};
      const items = Array.isArray(data.results) ? data.results : (Array.isArray(data.products) ? data.products : (Array.isArray(data) ? data : []));

      if (!items || items.length === 0) break;

      for (const p of items) {
        const normalized = normalize(p);
        if (seen.has(normalized.id)) continue;
        seen.add(normalized.id);
        out.push(normalized);
        if (out.length >= limit) break;
      }

      const total = typeof data.total === "number" ? data.total : undefined;
      if (total !== undefined && page * pageSize >= total) break;
      if (items.length < pageSize) break;
      page++;
    }

    return out;
  }

  async getById(productId: string): Promise<Product | null> {
    const axios = this.client.getAxios();
    const config = this.client.getConfig();

    this.logger.info("Salesforce getProductById", { productId });

    try {
      const resp = await axios.get(`/services/apexrest/commerce/product/${productId}`);
      const p = resp.data;
      if (!p) return null;

      return {
        id: p.Id || p.id,
        title: p.Name || p.name || p.title,
        description: p.Description || p.description,
        price: String(p.UnitPrice || p.price || "0"),
        image: p.ImageUrl || p.image || "",
        url: p.ProductUrl || p.url || `${config.siteBaseUrl || ""}/product/${p.Id || p.id}`,
        inStock: p.IsAvailable ?? p.inStock ?? true,
        inventory_quantity: p.QuantityAvailable ?? p.inventory_quantity,
      };
    } catch (err) {
      this.logger.error("Salesforce getById failed", err);
      return null;
    }
  }
}