"""
Application-wide configuration.
Loads environment variables and provides centralized config access.
"""

import os
from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Application
    APP_NAME: str = Field(default="Easymart Assistant", description="Application name")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")
    DEBUG: bool = Field(default=False, description="Debug mode")
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    
    # Server
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    
    # CORS
    ALLOWED_ORIGINS: str = Field(default="http://localhost:3000,http://localhost:3001", description="Comma-separated CORS origins")
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse ALLOWED_ORIGINS into list"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    # Backend Node.js URL (for Shopify adapter calls)
    NODE_BACKEND_URL: str = Field(default="http://localhost:3000", description="Node.js backend URL")
    
    # Hugging Face Configuration (for Mistral-7B)
    HUGGINGFACE_API_KEY: Optional[str] = Field(default=None, description="Hugging Face API key")
    HUGGINGFACE_MODEL: str = Field(default="mistralai/Mistral-7B-Instruct-v0.2", description="HF model identifier")
    HUGGINGFACE_BASE_URL: str = Field(default="https://router.huggingface.co", description="HF Inference API base URL")
    HUGGINGFACE_TIMEOUT: int = Field(default=30, description="HF API timeout in seconds")
    HUGGINGFACE_MAX_RETRIES: int = Field(default=3, description="HF API max retries")
    
    # OpenAI / LLM Configuration (optional fallback)
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    LLM_MODEL: str = Field(default="gpt-4", description="LLM model name")
    LLM_TEMPERATURE: float = Field(default=0.7, description="LLM temperature")
    LLM_MAX_TOKENS: int = Field(default=512, description="LLM max tokens")
    
    # Embedding Model (for vector search)
    EMBEDDING_MODEL: str = Field(default="all-MiniLM-L6-v2", description="Sentence transformer model")
    
    # Database / Data Storage
    @property
    def DATA_DIR(self) -> Path:
        """Data directory path"""
        return Path(__file__).parent.parent.parent / "data"
    
    @property
    def DATABASE_URL(self) -> str:
        """Database URL"""
        return f"sqlite:///{self.DATA_DIR / 'easymart.db'}"
    
    # Search Configuration
    SEARCH_LIMIT_DEFAULT: int = Field(default=5, description="Default search result limit")
    SEARCH_HYBRID_ALPHA: float = Field(default=0.5, description="Hybrid search weight (0-1)")
    
    # Session Management
    SESSION_TIMEOUT_MINUTES: int = Field(default=30, description="Session timeout in minutes")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Log format: json or text")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"


# Singleton settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings
