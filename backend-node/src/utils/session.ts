import { v4 as uuidv4 } from "uuid";

/**
 * Extract session ID from request headers
 */
export function getSessionId(headers: Record<string, any>): string {
  return headers["x-session-id"] || headers["X-Session-ID"] || "guest-session";
}

/**
 * Generate a new session ID
 */
export function generateSessionId(): string {
  return `session-${Date.now()}-${uuidv4()}`;
}

/**
 * Validate session ID format
 */
export function isValidSessionId(sessionId: string): boolean {
  if (!sessionId || typeof sessionId !== "string") {
    return false;
  }
  
  // Check if it's a reasonable length (not too short, not too long)
  return sessionId.length >= 10 && sessionId.length <= 100;
}

/**
 * Sanitize session ID (remove special characters)
 */
export function sanitizeSessionId(sessionId: string): string {
  return sessionId.replace(/[^a-zA-Z0-9-_]/g, "");
}
