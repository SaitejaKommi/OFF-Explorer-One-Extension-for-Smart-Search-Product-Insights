# Data Directory

This directory stores the Open Food Facts parquet datasets used by DuckDB.

## Download Instructions

### Option 1: Direct download (recommended)

```bash
# Create data directory if needed
mkdir -p data

# Download the Open Food Facts CSV and convert to parquet
# (requires pandas and pyarrow)
pip install pandas pyarrow requests

python - <<'EOF'
import pandas as pd
import requests
import os

url = "https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz"
print("Downloading OFF dataset (~2 GB compressed)...")
r = requests.get(url, stream=True)
with open("data/products.csv.gz", "wb") as f:
    for chunk in r.iter_content(chunk_size=8192):
        f.write(chunk)

print("Converting to parquet...")
df = pd.read_csv(
    "data/products.csv.gz",
    sep="\t",
    low_memory=False,
    usecols=[
        "code", "product_name", "categories_tags", "labels_tags",
        "nutriscore_grade", "nova_group",
        "energy_kcal_100g", "proteins_100g", "fat_100g", "saturated_fat_100g",
        "sugars_100g", "fiber_100g", "salt_100g", "carbohydrates_100g",
        "countries_tags", "allergens_tags",
    ],
    dtype={"code": str},
)
df.to_parquet("data/products.parquet", index=False)
print(f"Done! {len(df):,} products saved to data/products.parquet")
EOF
```

### Option 2: Canada-filtered dataset (smaller, faster)

```bash
python - <<'EOF'
import pandas as pd

df = pd.read_parquet("data/products.parquet")
ca = df[df["countries_tags"].str.contains("en:canada", na=False)]
ca.to_parquet("data/products_canada.parquet", index=False)
print(f"Canada subset: {len(ca):,} products")
EOF
```

Then update `PARQUET_GLOB=data/products_canada.parquet` in your `.env`.

## OFF Schema Reference

| Column | Type | Description |
|--------|------|-------------|
| `code` | VARCHAR | EAN barcode |
| `product_name` | VARCHAR | Product display name |
| `categories_tags` | VARCHAR | Comma-separated OFF category tags (e.g. `en:snacks,en:biscuits`) |
| `labels_tags` | VARCHAR | Dietary labels (e.g. `en:organic,en:vegan`) |
| `nutriscore_grade` | VARCHAR | a / b / c / d / e |
| `nova_group` | INTEGER | 1–4 (NOVA processing level) |
| `energy_kcal_100g` | DOUBLE | Calories per 100 g |
| `proteins_100g` | DOUBLE | Protein g per 100 g |
| `fat_100g` | DOUBLE | Total fat g per 100 g |
| `saturated_fat_100g` | DOUBLE | Saturated fat g per 100 g |
| `sugars_100g` | DOUBLE | Sugars g per 100 g |
| `fiber_100g` | DOUBLE | Dietary fiber g per 100 g |
| `salt_100g` | DOUBLE | Salt g per 100 g |
| `carbohydrates_100g` | DOUBLE | Carbs g per 100 g |
| `countries_tags` | VARCHAR | Countries where product is sold |
| `allergens_tags` | VARCHAR | Declared allergens |

## Notes

- Data files (`*.parquet`, `*.csv.gz`) are excluded from git via `.gitignore`
- The backend will start with an empty stub view if no parquet files are present
- For development, you can use a small sample file placed at `data/sample.parquet`
