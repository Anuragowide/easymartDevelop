"""
Database Layer for BM25 Metadata Storage

Uses SQLite for storing product and specification metadata.
"""

from sqlalchemy import create_engine, Column, String, Float, Integer, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path

from ..config import index_config

Base = declarative_base()


class ProductDB(Base):
    """Product table for BM25 indexing"""
    __tablename__ = 'products'
    
    sku = Column(String, primary_key=True)
    handle = Column(String, unique=True, index=True)
    title = Column(String, index=True)
    price = Column(Float)
    currency = Column(String)
    image_url = Column(String)
    product_url = Column(String)  # Full Shopify URL
    vendor = Column(String, index=True)
    tags = Column(JSON)
    description = Column(Text)
    search_content = Column(Text)
    
    def to_dict(self):
        return {
            'sku': self.sku,
            'handle': self.handle,
            'title': self.title,
            'price': self.price,
            'currency': self.currency,
            'image_url': self.image_url,
            'product_url': self.product_url,
            'vendor': self.vendor,
            'tags': self.tags,
            'description': self.description
        }


class ProductSpecDB(Base):
    """Product specs table for BM25 indexing"""
    __tablename__ = 'product_specs'
    
    id = Column(String, primary_key=True)
    sku = Column(String, index=True)
    section = Column(String, index=True)
    spec_text = Column(Text)
    attributes_json = Column(JSON)
    
    def to_dict(self):
        return {
            'id': self.id,
            'sku': self.sku,
            'section': self.section,
            'spec_text': self.spec_text,
            'attributes': self.attributes_json
        }


class ProductImageDB(Base):
    """Product images table"""
    __tablename__ = 'product_images'
    
    image_id = Column(String, primary_key=True)
    sku = Column(String, index=True)
    image_url = Column(String)
    position = Column(Integer, default=0)


class DatabaseManager:
    """Manages SQLite database for BM25 indexes"""
    
    def __init__(self, db_path: Path = None):
        if db_path is None:
            db_path = index_config.db_path
        
        self.db_path = Path(db_path)
        self.engine = create_engine(f'sqlite:///{self.db_path}')
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        print(f"[DB] Connected to SQLite: {self.db_path}")
    
    def get_session(self):
        return self.SessionLocal()
    
    def clear_all(self):
        """Clear all tables"""
        session = self.get_session()
        try:
            session.query(ProductDB).delete()
            session.query(ProductSpecDB).delete()
            session.query(ProductImageDB).delete()
            session.commit()
            print("[DB] Cleared all tables")
        finally:
            session.close()
