import { config } from "../../config";

type LogLevel = "debug" | "info" | "warn" | "error";

interface LogData {
  [key: string]: any;
}

class Logger {
  private isDevelopment: boolean;

  constructor() {
    this.isDevelopment = config.NODE_ENV === "development";
  }

  private formatMessage(level: LogLevel, message: string, data?: LogData): string {
    const timestamp = new Date().toISOString();
    const logEntry = {
      timestamp,
      level: level.toUpperCase(),
      message,
      ...(data && { data }),
    };

    if (this.isDevelopment) {
      // Pretty print in development
      return `[${timestamp}] ${level.toUpperCase()}: ${message}${data ? ` ${JSON.stringify(data, null, 2)}` : ""}`;
    }

    // JSON format for production (easier to parse)
    return JSON.stringify(logEntry);
  }

  debug(message: string, data?: LogData): void {
    if (this.isDevelopment) {
      console.debug(this.formatMessage("debug", message, data));
    }
  }

  info(message: string, data?: LogData): void {
    console.info(this.formatMessage("info", message, data));
  }

  warn(message: string, data?: LogData): void {
    console.warn(this.formatMessage("warn", message, data));
  }

  error(message: string, data?: any): void {
    const errorData = data instanceof Error 
      ? { error: data.message, stack: data.stack }
      : data;
    
    console.error(this.formatMessage("error", message, errorData));
  }

  /**
   * Log request/response for API calls
   */
  logRequest(method: string, url: string, data?: any): void {
    this.info("API Request", { method, url, ...data });
  }

  logResponse(method: string, url: string, status: number, duration?: number): void {
    this.info("API Response", { method, url, status, duration });
  }
}

// Singleton instance
export const logger = new Logger();
