import axios, { AxiosInstance, AxiosHeaders } from "axios";
import jwt from "jsonwebtoken";
import { SalesforceConfig, Logger } from "./types";

const defaultLogger: Logger = {
  debug: () => {},
  info: console.log,
  warn: console.warn,
  error: (msg: any) => console.error(msg),
};

export class SalesforceClient {
  private config: SalesforceConfig;
  private client: AxiosInstance;
  private accessToken = "";
  private instanceUrl = "";
  private expiresAt = 0;
  private logger: Logger;

  constructor(config: SalesforceConfig, logger?: Logger) {
    this.config = config;
    this.logger = logger || defaultLogger;
    this.client = axios.create();

    this.client.interceptors.request.use(async (req) => {
      await this.ensureToken();
      if (!req.headers) req.headers = new AxiosHeaders();
      (req.headers as any).Authorization = `Bearer ${this.accessToken}`;
      if (!req.baseURL && this.instanceUrl) {
        req.baseURL = this.instanceUrl;
      }
      return req;
    });
  }

  private normalizePrivateKey(raw: string): string {
    if (!raw) return "";
    return raw.replace(/\\n/g, "\n");
  }

  private async requestTokenWithJwt(): Promise<void> {
    const { tokenUrl, clientId, jwtUsername, jwtPrivateKey } = this.config;
    if (!tokenUrl || !clientId || !jwtUsername || !jwtPrivateKey) {
      throw new Error("JWT config incomplete");
    }

    const privateKey = this.normalizePrivateKey(jwtPrivateKey);
    const now = Math.floor(Date.now() / 1000);
    const payload = { iss: clientId, sub: jwtUsername, aud: tokenUrl, exp: now + 180 };
    const assertion = jwt.sign(payload, privateKey, { algorithm: "RS256" });

    const params = new URLSearchParams();
    params.append("grant_type", "urn:ietf:params:oauth:grant-type:jwt-bearer");
    params.append("assertion", assertion);

    const resp = await axios.post(tokenUrl, params.toString(), {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });

    this.accessToken = resp.data.access_token;
    this.instanceUrl = resp.data.instance_url || this.instanceUrl;
    this.expiresAt = Date.now() + (resp.data.expires_in || 3600) * 1000;
    this.client.defaults.baseURL = this.instanceUrl;

    this.logger.info("Salesforce token acquired", { instanceUrl: this.instanceUrl });
  }

  private async requestTokenWithPassword(): Promise<void> {
    const { tokenUrl, clientId, clientSecret, username, password, securityToken } = this.config;
    if (!tokenUrl || !clientId) throw new Error("Password flow config incomplete");

    const params = new URLSearchParams();
    params.append("grant_type", "password");
    params.append("client_id", clientId);
    params.append("client_secret", clientSecret || "");
    params.append("username", username || "");
    params.append("password", `${password || ""}${securityToken || ""}`);

    const resp = await axios.post(tokenUrl, params.toString(), {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });

    this.accessToken = resp.data.access_token;
    this.instanceUrl = resp.data.instance_url || this.instanceUrl;
    this.expiresAt = Date.now() + (resp.data.expires_in || 3600) * 1000;
    this.client.defaults.baseURL = this.instanceUrl;

    this.logger.info("Salesforce password token acquired", { instanceUrl: this.instanceUrl });
  }

  private async ensureToken(): Promise<void> {
    const refreshThreshold = 60 * 1000;
    if (this.accessToken && Date.now() < this.expiresAt - refreshThreshold) return;

    if (this.config.jwtPrivateKey) {
      await this.requestTokenWithJwt();
    } else if (this.config.username && this.config.password) {
      await this.requestTokenWithPassword();
    } else {
      throw new Error("No Salesforce auth method configured");
    }
  }

  getAxios(): AxiosInstance {
    return this.client;
  }

  getConfig(): SalesforceConfig {
    return this.config;
  }
}