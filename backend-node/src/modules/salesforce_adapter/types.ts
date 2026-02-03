export interface Logger {
  debug(msg: string, data?: object): void;
  info(msg: string, data?: object): void;
  warn(msg: string, data?: object): void;
  error(msg: string | Error, data?: any): void;
}

/**
 * Salesforce Adapter Types
 */

export interface SalesforceConfig {
  tokenUrl: string;
  clientId: string;
  jwtUsername?: string;
  jwtPrivateKey?: string;
  username?: string;
  password?: string;
  securityToken?: string;
  clientSecret?: string;
  apiVersion: string;
  siteBaseUrl?: string;
  webstoreId?: string;
}

export interface SalesforceProduct {
  Id: string;
  Name: string;
  Description?: string;
  UnitPrice?: number;
  ImageUrl?: string;
  ProductUrl?: string;
  IsAvailable?: boolean;
  QuantityAvailable?: number;
  ProductCode?: string;
  Family?: string;
}

export interface SalesforceCartLine {
  cartItemId: string;
  productId: string;
  productName?: string;
  quantity: number;
  price: number | string;
  imageUrl?: string;
}

export interface SalesforceCartResponse {
  cartId: string;
  lines: SalesforceCartLine[];
  totalAmount?: number;
}