# backend-pylang/app/modules/normalizer.py
def normalize_product(raw: dict):
    # Best-effort mapping — tune after you see a real Apex product JSON
    # Handle multiple possible field names used by Apex/Storefront
    sku = raw.get("sku") or raw.get("id") or raw.get("productId")
    title = raw.get("title") or raw.get("name") or raw.get("productName") or ""
    price_val = raw.get("price") or raw.get("salePrice") or raw.get("unitPrice") or raw.get("UnitPrice") or 0
    try:
        price = float(price_val or 0)
    except Exception:
        price = 0.0

    image = None
    images = raw.get("images") or raw.get("imageUrls") or []
    # Some Apex DTOs use imageUrl or ImageUrl single field
    if not images and raw.get("imageUrl"):
        images = [raw.get("imageUrl")]

    if images and isinstance(images, list):
        image = images[0].get("url") if isinstance(images[0], dict) else images[0]

    product_url = raw.get("product_url") or raw.get("url") or raw.get("handle") or raw.get("ProductUrl")
    specs = raw.get("specs") or {}

    # compute availability robustly
    _available = raw.get("available")
    _is_available = raw.get("IsAvailable")
    inventory_qty = raw.get("inventory_quantity") if raw.get("inventory_quantity") is not None else raw.get("QuantityAvailable")
    if raw.get("stock_status") and inventory_qty is not None:
        stock_status = raw.get("stock_status")
    elif _available is not None:
        stock_status = "in_stock" if bool(_available) else "out_of_stock"
    elif _is_available is not None:
        stock_status = "in_stock" if bool(_is_available) else "out_of_stock"
    elif inventory_qty is not None:
        stock_status = "in_stock" if inventory_qty > 0 else "out_of_stock"
    else:
        stock_status = "in_stock"

    return {
        "id": raw.get("id") or sku or raw.get("productId"),
        "sku": sku,
        "title": title,
        "description": raw.get("description") or raw.get("longDescription") or raw.get("Description") or "",
        "price": price,
        "currency": raw.get("currency") or raw.get("CurrencyIsoCode") or "AUD",
        "category": raw.get("category") or raw.get("product_type") or "General",
        "product_type": raw.get("product_type") or raw.get("category"),
        "tags": raw.get("tags") or [],
        "image_url": image,
        "vendor": raw.get("vendor") or raw.get("brand"),
        "handle": raw.get("handle") or sku,
        "product_url": product_url,
        "stock_status": stock_status,
        "status": raw.get("status"),
        "options": raw.get("options") or [],
        "variants": raw.get("variants") or [],
        "images": images,
        "available": raw.get("available", True),
        "inventory_managed": raw.get("inventory_managed", False),
        "barcode": raw.get("barcode"),
        "specs": specs
    }