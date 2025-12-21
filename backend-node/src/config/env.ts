import dotenv from "dotenv";

// Load environment variables
dotenv.config();

export const config = {
  // Server
  PORT: Number(process.env.PORT || 3001),
  NODE_ENV: process.env.NODE_ENV || "development",

  // Python Assistant API
  PYTHON_BASE_URL: process.env.PYTHON_BASE_URL || "http://localhost:8000",

  // Shopify credentials
  SHOPIFY_STORE_DOMAIN: (process.env.SHOPIFY_STORE_DOMAIN || "").replace(/^https?:\/\//, ""),
  SHOPIFY_ACCESS_TOKEN: process.env.SHOPIFY_ACCESS_TOKEN || "",
  SHOPIFY_API_VERSION: process.env.SHOPIFY_API_VERSION || "2024-01",

  // Session
  SESSION_SECRET: process.env.SESSION_SECRET || "easymart-secret-change-in-production",
};

// Validate required environment variables
const requiredEnvVars = ["SHOPIFY_STORE_DOMAIN", "SHOPIFY_ACCESS_TOKEN"];

for (const envVar of requiredEnvVars) {
  if (!process.env[envVar] && config.NODE_ENV === "production") {
    console.warn(`⚠️  Warning: ${envVar} is not set in environment variables`);
  }
}
