"""
Quick script to check current CSV catalog data
"""
import os
import pandas as pd
from pathlib import Path

def check_csv_catalog():
    """Check what's in the current CSV file"""
    
    # Find the CSV file
    csv_path = Path(__file__).parent / "data" / "products.csv"
    
    if not csv_path.exists():
        print(f"❌ CSV file not found at: {csv_path}")
        return
    
    print("\n" + "="*60)
    print("📄 CSV CATALOG CHECK")
    print("="*60 + "\n")
    
    print(f"📁 File: {csv_path}")
    print(f"📊 Size: {csv_path.stat().st_size / 1024:.2f} KB\n")
    
    try:
        df = pd.read_csv(csv_path)
        
        print(f"✅ Loaded CSV successfully")
        print(f"📦 Total products: {len(df)}")
        print(f"📋 Columns: {len(df.columns)}\n")
        
        print("📋 COLUMN NAMES:")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i:2d}. {col}")
        
        print(f"\n📊 FIRST 5 PRODUCTS:")
        print("-" * 100)
        
        # Select key columns
        display_cols = []
        for col in ['Title', 'Variant SKU', 'Variant Price', 'Product Category', 'Vendor', 'Handle']:
            if col in df.columns:
                display_cols.append(col)
        
        if display_cols:
            print(df[display_cols].head(5).to_string(index=False))
        else:
            print(df.head(5).to_string(index=False))
        
        print("-" * 100)
        
        # Statistics
        print(f"\n📊 STATISTICS:")
        
        if 'Product Category' in df.columns:
            categories = df['Product Category'].value_counts()
            print(f"\n  Categories ({len(categories)} unique):")
            for cat, count in categories.head(10).items():
                print(f"    • {cat}: {count}")
        
        if 'Vendor' in df.columns:
            vendors = df['Vendor'].value_counts()
            print(f"\n  Vendors ({len(vendors)} unique):")
            for vendor, count in vendors.head(5).items():
                print(f"    • {vendor}: {count}")
        
        if 'Variant Price' in df.columns:
            prices = df['Variant Price'].dropna()
            if len(prices) > 0:
                print(f"\n  Price Range:")
                print(f"    • Min: ${prices.min():.2f}")
                print(f"    • Max: ${prices.max():.2f}")
                print(f"    • Average: ${prices.mean():.2f}")
        
        # Check for missing data
        print(f"\n⚠️  MISSING DATA:")
        missing = df.isnull().sum()
        missing = missing[missing > 0].sort_values(ascending=False)
        
        if len(missing) > 0:
            print(f"  Columns with missing values:")
            for col, count in missing.head(10).items():
                pct = (count / len(df)) * 100
                print(f"    • {col}: {count} ({pct:.1f}%)")
        else:
            print("  ✅ No missing values!")
        
    except Exception as e:
        print(f"❌ Error reading CSV: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_csv_catalog()
    
    print("\n" + "="*60)
    print("✅ CHECK COMPLETE")
    print("="*60 + "\n")
