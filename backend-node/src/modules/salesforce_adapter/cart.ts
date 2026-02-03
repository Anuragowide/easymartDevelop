import { SalesforceClient } from "./client";
import { Logger } from "./types";

export interface CartItem {
  id: string;
  productId: string;
  title: string;
  quantity: number;
  price: number;
  image?: string;
}

export interface Cart {
  id: string;
  items: CartItem[];
  totalQuantity: number;
  totalPrice: number;
}

const defaultLogger: Logger = {
  debug: () => {},
  info: console.log,
  warn: console.warn,
  error: (msg: any) => console.error(msg),
};

export class CartService {
  private client: SalesforceClient;
  private logger: Logger;

  constructor(client: SalesforceClient, logger?: Logger) {
    this.client = client;
    this.logger = logger || defaultLogger;
  }

  async getCart(buyerAccountId: string): Promise<Cart> {
    const axios = this.client.getAxios();
    this.logger.info?.("Salesforce getCart", { buyerAccountId });
    try {
      const resp = await axios.get("/services/apexrest/CartApi/getCart", {
        params: { buyerAccountId },
      });
      const data = resp.data || {};
      const items: CartItem[] = (data.items || data.lines || []).map((l: any) => ({
        id: l.cartItemId || l.id || l.cartItemId__c,
        productId: l.productId || l.productId__c,
        title: l.name || l.productName || "",
        quantity: l.qty || l.quantity || l.qty__c || 0,
        price: typeof l.price === "number" ? l.price : parseFloat(l.price || "0"),
        image: l.imageUrl || l.image || "",
      }));

      return {
        id: data.cartId || data.id || "",
        items,
        totalQuantity: items.reduce((s, i) => s + (i.quantity || 0), 0),
        totalPrice: items.reduce((s, i) => s + (i.price || 0) * (i.quantity || 0), 0),
      };
    } catch (err: any) {
      this.logger.error?.("Salesforce getCart failed", err);
      throw err;
    }
  }

  async addToCart(productId: string, quantity: number, buyerAccountId: string): Promise<Cart> {
    const axios = this.client.getAxios();
    this.logger.info?.("Salesforce addToCart", { productId, quantity, buyerAccountId });
    try {
      await axios.post("/services/apexrest/CartApi/addItem", {
        cartId: buyerAccountId,
        productId,
        quantity,
      }, { headers: { "Content-Type": "application/json" }});
      return this.getCart(buyerAccountId);
    } catch (err: any) {
      this.logger.error?.("Salesforce addToCart failed", err);
      throw err;
    }
  }

  async updateCartItem(cartItemId: string, quantity: number, buyerAccountId: string): Promise<Cart> {
    const axios = this.client.getAxios();
    this.logger.info?.("Salesforce updateCartItem", { cartItemId, quantity, buyerAccountId });
    try {
      await axios.post("/services/apexrest/CartApi/updateItem", {
        cartId: buyerAccountId,
        cartItemId,
        quantity,
      }, { headers: { "Content-Type": "application/json" }});
      return this.getCart(buyerAccountId);
    } catch (err: any) {
      this.logger.error?.("Salesforce updateCartItem failed", err);
      throw err;
    }
  }

  async removeFromCart(cartItemId: string, buyerAccountId: string): Promise<Cart> {
    const axios = this.client.getAxios();
    this.logger.info?.("Salesforce removeFromCart", { cartItemId, buyerAccountId });
    try {
      await axios.post("/services/apexrest/CartApi/removeItem", {
        cartId: buyerAccountId,
        cartItemId,
      }, { headers: { "Content-Type": "application/json" }});
      return this.getCart(buyerAccountId);
    } catch (err: any) {
      this.logger.error?.("Salesforce removeFromCart failed", err);
      throw err;
    }
  }
}