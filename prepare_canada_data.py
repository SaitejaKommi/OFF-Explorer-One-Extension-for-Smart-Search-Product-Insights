#!/usr/bin/env python3
"""
Setup script to prepare Canada-only Open Food Facts data.
This script extracts Canada data from the provided parquet file.
"""

import pandas as pd
import sys
from pathlib import Path

def prepare_canada_data():
    """Extract Canada-filtered data from food.parquet"""
    
    downloads_path = Path.home() / "Downloads" / "food.parquet"
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    if not downloads_path.exists():
        print(f"❌ Error: {downloads_path} not found!")
        print("Please ensure food.parquet exists in your Downloads folder.")
        return False
    
    print(f"📂 Loading data from {downloads_path}...")
    try:
        df = pd.read_parquet(downloads_path)
        print(f"✓ Loaded {len(df):,} products")
        
        # Select only relevant columns
        required_cols = [
            "code", "product_name", "categories_tags", "labels_tags",
            "nutriscore_grade", "nova_group",
            "energy_kcal_100g", "proteins_100g", "fat_100g", "saturated_fat_100g",
            "sugars_100g", "fiber_100g", "salt_100g", "carbohydrates_100g",
            "countries_tags", "allergens_tags",
        ]
        
        # Check which columns exist
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            print(f"⚠️  Warning: Missing columns: {missing_cols}")
            # Use only available columns
            available_cols = [c for c in required_cols if c in df.columns]
            df = df[available_cols]
        else:
            df = df[required_cols]
        
        # Filter to Canada only
        print("🇨🇦 Filtering to Canada products...")
        if "countries_tags" in df.columns:
            canada_df = df[df["countries_tags"].str.contains("en:canada", case=False, na=False)]
            print(f"✓ Found {len(canada_df):,} Canada products")
        else:
            print("⚠️  Warning: 'countries_tags' column not found, using all data")
            canada_df = df
        
        # Save Canada dataset
        output_path = data_dir / "products_canada.parquet"
        canada_df.to_parquet(output_path, index=False, compression='snappy')
        print(f"✓ Saved to {output_path}")
        
        # Also save full dataset for reference
        full_path = data_dir / "products.parquet"
        df.to_parquet(full_path, index=False, compression='snappy')
        print(f"✓ Also saved to {full_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = prepare_canada_data()
    sys.exit(0 if success else 1)
