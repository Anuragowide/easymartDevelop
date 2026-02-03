# backend-pylang/app/modules/salesforce_client.py
import time, os, requests, jwt, logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

class SalesforceClient:
    def __init__(self):
        self.token_url = os.getenv("SALESFORCE_TOKEN_URL")
        self.client_id = os.getenv("SALESFORCE_JWT_CLIENT_ID") or os.getenv("SALESFORCE_CLIENT_ID")
        self.jwt_username = os.getenv("SALESFORCE_JWT_USERNAME")
        self.jwt_private_key = os.getenv("SALESFORCE_JWT_PRIVATE_KEY", "").replace("\\n", "\n")
        self.username = os.getenv("SALESFORCE_USERNAME")
        self.password = os.getenv("SALESFORCE_PASSWORD")
        self.security_token = os.getenv("SALESFORCE_SECURITY_TOKEN")
        self._access_token = None
        self._instance_url = None
        self._expires_at = 0

    def _get_jwt_token(self):
        now = int(time.time())
        payload = {"iss": self.client_id, "sub": self.jwt_username, "aud": self.token_url, "exp": now + 120}
        logger.debug("Creating JWT payload: %s", {k: payload[k] for k in ("iss","sub","aud","exp")})
        signed = jwt.encode(payload, self.jwt_private_key, algorithm="RS256")
        logger.debug("JWT signed (first 40 chars): %s", str(signed)[:40])
        return signed

    def _request_token_with_jwt(self):
        assertion = self._get_jwt_token()
        data = {"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion}
        logger.debug("Requesting token (JWT) from %s", self.token_url)
        r = requests.post(self.token_url, data=data, timeout=20)
        logger.debug("Token response status: %s, body: %s", r.status_code, r.text[:1000])
        r.raise_for_status()
        return r.json()

    def _request_token_with_password(self):
        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "username": self.username,
            "password": f"{self.password}{self.security_token}"
        }
        logger.debug("Requesting token (password) from %s", self.token_url)
        r = requests.post(self.token_url, data=data, timeout=20)
        logger.debug("Token response status: %s, body: %s", r.status_code, r.text[:1000])
        r.raise_for_status()
        return r.json()

    def ensure_token(self):
        if self._access_token and time.time() < self._expires_at - 30:
            logger.debug("Using cached token, expires_at=%s", self._expires_at)
            return
        logger.debug("Ensuring token; token_url=%s, client_id=%s", self.token_url, self.client_id)
        try:
            token_resp = self._request_token_with_jwt()
            logger.debug("Authenticated with JWT")
        except Exception as e_jwt:
            logger.debug("JWT auth failed: %s; falling back to password flow", e_jwt)
            try:
                token_resp = self._request_token_with_password()
                logger.debug("Authenticated with password flow")
            except Exception as e_pass:
                logger.exception("Both JWT and password token requests failed")
                raise

        self._access_token = token_resp.get("access_token")
        self._instance_url = token_resp.get("instance_url")
        self._expires_at = time.time() + int(token_resp.get("expires_in", 3600))
        logger.info("Token acquired; instance_url=%s, access_token_first8=%s", self._instance_url, (self._access_token or "")[:8])

    def post_search(self, body: dict):
        self.ensure_token()
        if not self._instance_url:
            logger.error("No instance_url available after token; token_url=%s, client_id=%s", self.token_url, self.client_id)
            raise RuntimeError("No instance_url for Salesforce instance")
        url = f"{self._instance_url}/services/apexrest/commerce/search"
        headers = {"Authorization": f"Bearer {self._access_token}", "Content-Type": "application/json"}
        logger.debug("POST %s payload=%s", url, body)
        r = requests.post(url, json=body, headers=headers, timeout=30)
        logger.debug("Salesforce search response status=%s body=%s", r.status_code, (r.text or "")[:2000])
        try:
            return r.status_code, r.json() if r.content else {}
        except Exception:
            logger.exception("Failed parsing search response JSON")
            return r.status_code, {}

    def get_product(self, product_id: str):
        self.ensure_token()
        if not self._instance_url:
            logger.error("No instance_url available after token; cannot get product")
            raise RuntimeError("No instance_url for Salesforce instance")
        url = f"{self._instance_url}/services/apexrest/commerce/product/{product_id}"
        headers = {"Authorization": f"Bearer {self._access_token}"}
        logger.debug("GET %s", url)
        r = requests.get(url, headers=headers, timeout=20)
        logger.debug("Salesforce get_product status=%s body=%s", r.status_code, (r.text or "")[:2000])
        try:
            return r.status_code, r.json() if r.content else {}
        except Exception:
            logger.exception("Failed parsing product response JSON")
            return r.status_code, {}