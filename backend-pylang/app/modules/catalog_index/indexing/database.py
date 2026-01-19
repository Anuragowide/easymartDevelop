"""
Database Layer for BM25 Metadata Storage

Uses SQLite for storing product and specification metadata.
"""

from sqlalchemy import create_engine, Column, String, Float, Integer, JSON, Text, Index, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path

from ..config import index_config

Base = declarative_base()


class ProductDB(Base):
    """Product table for BM25 indexing with performance indexes"""
    __tablename__ = 'products'
    
    sku = Column(String, primary_key=True)
    handle = Column(String, unique=True, index=True)
    title = Column(String, index=True)
    price = Column(Float, index=True)  # Added index for price filters
    compare_at_price = Column(Float)
    currency = Column(String)
    image_url = Column(String)
    product_url = Column(String)  # Full Shopify URL
    vendor = Column(String, index=True)
    tags = Column(JSON)
    description = Column(Text)
    search_content = Column(Text)
    inventory_quantity = Column(Integer, default=0)  # Stock quantity
    category = Column(String, index=True)
    product_type = Column(String, index=True)
    status = Column(String, index=True)
    options_json = Column(JSON)
    variants_json = Column(JSON)
    images_json = Column(JSON)
    available = Column(Integer, default=1)
    inventory_managed = Column(Integer, default=0)
    barcode = Column(String)
    
    # Define composite indexes for common query patterns
    __table_args__ = (
        Index('idx_vendor_price', 'vendor', 'price'),
        Index('idx_title_price', 'title', 'price'),
    )
    
    def to_dict(self):
        return {
            'sku': self.sku,
            'handle': self.handle,
            'title': self.title,
            'price': self.price,
            'compare_at_price': self.compare_at_price,
            'currency': self.currency,
            'image_url': self.image_url,
            'product_url': self.product_url,
            'vendor': self.vendor,
            'tags': self.tags,
            'description': self.description,
            'inventory_quantity': self.inventory_quantity,
            'category': self.category,
            'product_type': self.product_type,
            'status': self.status,
            'options': self.options_json,
            'variants': self.variants_json,
            'images': self.images_json,
            'available': self.available,
            'inventory_managed': self.inventory_managed,
            'barcode': self.barcode
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
    """Manages SQLite database for BM25 indexes with FTS5 support"""
    
    def __init__(self, db_path: Path = None):
        if db_path is None:
            db_path = index_config.db_path
        
        self.db_path = Path(db_path)
        self.engine = create_engine(f'sqlite:///{self.db_path}')
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Setup FTS5 virtual table for full-text search
        self._setup_fts5()
        self._ensure_product_columns()
        
        print(f"[DB] Connected to SQLite: {self.db_path}")
    
    def _setup_fts5(self):
        """Create FTS5 virtual table for efficient full-text search"""
        with self.engine.connect() as conn:
            # Check if FTS5 table exists
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='products_fts'")
            )
            if result.fetchone() is None:
                # Create FTS5 virtual table
                conn.execute(text("""
                    CREATE VIRTUAL TABLE products_fts USING fts5(
                        sku UNINDEXED,
                        title,
                        description,
                        search_content,
                        content=products,
                        content_rowid=rowid
                    )
                """))
                
                # Create triggers to keep FTS5 in sync with products table
                conn.execute(text("""
                    CREATE TRIGGER products_fts_insert AFTER INSERT ON products BEGIN
                        INSERT INTO products_fts(rowid, sku, title, description, search_content)
                        VALUES (new.rowid, new.sku, new.title, new.description, new.search_content);
                    END
                """))
                
                conn.execute(text("""
                    CREATE TRIGGER products_fts_update AFTER UPDATE ON products BEGIN
                        UPDATE products_fts SET 
                            sku = new.sku,
                            title = new.title,
                            description = new.description,
                            search_content = new.search_content
                        WHERE rowid = old.rowid;
                    END
                """))
                
                conn.execute(text("""
                    CREATE TRIGGER products_fts_delete AFTER DELETE ON products BEGIN
                        DELETE FROM products_fts WHERE rowid = old.rowid;
                    END
                """))
                
                conn.commit()
                print("[DB] Created FTS5 virtual table with triggers")
            else:
                print("[DB] FTS5 table already exists")

    def _ensure_product_columns(self):
        """Ensure new columns exist on products table (SQLite ALTER TABLE)."""
        needed = {
            "compare_at_price": "FLOAT",
            "category": "TEXT",
            "product_type": "TEXT",
            "status": "TEXT",
            "options_json": "TEXT",
            "variants_json": "TEXT",
            "images_json": "TEXT",
            "available": "INTEGER",
            "inventory_managed": "INTEGER",
            "barcode": "TEXT"
        }
        with self.engine.connect() as conn:
            existing = {
                row[1]
                for row in conn.execute(text("PRAGMA table_info(products)")).fetchall()
            }
            for col, col_type in needed.items():
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE products ADD COLUMN {col} {col_type}"))
            conn.commit()
    
    def search_fts5(self, query: str, limit: int = 10) -> list:
        """
        Search using FTS5 for efficient full-text search.
        
        Args:
            query: Search query (supports FTS5 syntax like AND, OR, NEAR)
            limit: Maximum results
            
        Returns:
            List of product dictionaries with relevance rank
        """
        session = self.get_session()
        try:
            # Sanitize query for FTS5 (escape special chars)
            sanitized = query.replace('"', '""')
            
            # Try exact phrase match first, then fallback to individual terms
            results = session.execute(text(f"""
                SELECT 
                    p.*,
                    rank as relevance
                FROM products_fts 
                JOIN products p ON products_fts.rowid = p.rowid
                WHERE products_fts MATCH '"{sanitized}"'
                ORDER BY rank
                LIMIT {limit}
            """)).fetchall()
            
            # If no exact phrase matches, try AND query
            if not results:
                terms = sanitized.split()
                and_query = ' AND '.join(f'"{term}"' for term in terms)
                results = session.execute(text(f"""
                    SELECT 
                        p.*,
                        rank as relevance
                    FROM products_fts 
                    JOIN products p ON products_fts.rowid = p.rowid
                    WHERE products_fts MATCH '{and_query}'
                    ORDER BY rank
                    LIMIT {limit}
                """)).fetchall()
            
            # Convert to dictionaries
            products = []
            for row in results:
                products.append({
                    'sku': row.sku,
                    'handle': row.handle,
                    'title': row.title,
                    'price': row.price,
                    'currency': row.currency,
                    'image_url': row.image_url,
                    'product_url': row.product_url,
                    'vendor': row.vendor,
                    'tags': row.tags,
                    'description': row.description,
                    'inventory_quantity': row.inventory_quantity,
                    'relevance': row.relevance if hasattr(row, 'relevance') else 0
                })
            
            return products
        finally:
            session.close()
    
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
