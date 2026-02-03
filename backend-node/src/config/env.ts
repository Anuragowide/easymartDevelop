import dotenv from "dotenv";

// Load environment variables
dotenv.config();

export const config = {
  // Server
  PORT: Number(process.env.PORT || 3002),
  NODE_ENV: process.env.NODE_ENV || "development",

  // Python Assistant API
  PYTHON_BASE_URL: process.env.PYTHON_BASE_URL || "http://localhost:8000",

  // Platform Selection
  ACTIVE_PLATFORM: process.env.ACTIVE_PLATFORM || "shopify",

  // Shopify credentials
  SHOPIFY_STORE_DOMAIN: (process.env.SHOPIFY_STORE_DOMAIN || "").replace(/^https?:\/\//, ""),
  SHOPIFY_ACCESS_TOKEN: process.env.SHOPIFY_ACCESS_TOKEN || "",
  SHOPIFY_API_VERSION: process.env.SHOPIFY_API_VERSION || "2024-01",

  // Salesforce - JWT Bearer Flow (recommended)
  SALESFORCE_TOKEN_URL: process.env.SALESFORCE_TOKEN_URL || "https://login.salesforce.com/services/oauth2/token",
  SALESFORCE_JWT_CLIENT_ID: process.env.SALESFORCE_JWT_CLIENT_ID || "",
  SALESFORCE_JWT_USERNAME: process.env.SALESFORCE_JWT_USERNAME || "",
  SALESFORCE_JWT_PRIVATE_KEY: process.env.SALESFORCE_JWT_PRIVATE_KEY || "",

  // Salesforce - Password Flow (alternative) 
  SALESFORCE_CLIENT_ID: process.env.SALESFORCE_CLIENT_ID || "",
  SALESFORCE_CLIENT_SECRET: process.env.SALESFORCE_CLIENT_SECRET || "",
  SALESFORCE_USERNAME: process.env.SALESFORCE_USERNAME || "",
  SALESFORCE_PASSWORD: process.env.SALESFORCE_PASSWORD || "",
  SALESFORCE_SECURITY_TOKEN: process.env.SALESFORCE_SECURITY_TOKEN || "",

  // Salesforce - API Settings
  SALESFORCE_API_VERSION: process.env.SALESFORCE_API_VERSION || "v59.0",
  SALESFORCE_SITE_BASE_URL: process.env.SALESFORCE_SITE_BASE_URL || "",
  SALESFORCE_WEBSTORE_ID: process.env.SALESFORCE_WEBSTORE_ID || "",

  // Session
  SESSION_SECRET: process.env.SESSION_SECRET || "easymart-secret-change-in-production",
};

// Validate required environment variables
const activePlatform = config.ACTIVE_PLATFORM;

if (config.NODE_ENV === "production") {
  if (activePlatform === "shopify") {
    const requiredShopifyVars = ["SHOPIFY_STORE_DOMAIN", "SHOPIFY_ACCESS_TOKEN"];
    for (const envVar of requiredShopifyVars) {
      if (!process.env[envVar]) {
        console.warn(`⚠️  Warning: ${envVar} is not set in environment variables`);
      }
    }
  } else if (activePlatform === "salesforce") {
    const hasJwt = config.SALESFORCE_JWT_CLIENT_ID && config.SALESFORCE_JWT_USERNAME && config.SALESFORCE_JWT_PRIVATE_KEY;
    const hasPassword = config.SALESFORCE_CLIENT_ID && config.SALESFORCE_USERNAME && config.SALESFORCE_PASSWORD;

    if (!hasJwt && !hasPassword) {
      console.warn("⚠️  Warning: No Salesforce authentication configured");
    }
  }
}
