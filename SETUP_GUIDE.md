# Quick Start Guide - OFF Explorer Extension

## 🎨 Visual Updates
✅ **Styling Updated** - The popup now uses the official Open Food Facts orange theme (#ff8714) with improved visual design

## 🇨🇦 Canada-Only Database
✅ **API Configured** - All API calls now exclusively use `ca.openfoodfacts.org` (Canadian database)

## 🔍 Enable Semantic Search

The search currently requires data to work. Follow these steps to prepare the Canadian dataset:

### Step 1: Copy Configuration
```bash
cp .env.example .env
```

### Step 2: Prepare Data
Run the data preparation script to extract Canadian products:
```bash
python prepare_canada_data.py
```

**Requirements:** `pandas` and `pyarrow` must be installed
```bash
pip install pandas pyarrow
```

**Output:** This creates two parquet files in the `data/` folder:
- `data/products.parquet` - Full dataset (if available)
- `data/products_canada.parquet` - Canada-only products (~100K-500K products)

### Step 3: Start Backend
```bash
# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Start FastAPI server
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 4: Load Extension in Chrome
1. Open Chrome → `chrome://extensions/`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked**
4. Select the `extension/` folder
5. Click the extension icon to open search popup

### Step 5: Try Search
In the popup, try these example queries:
- "low sugar snacks"
- "high protein breakfast"
- "vegan products"
- "organic cereals"

## 📋 What Each Change Does

### 1. Styling (popup.css)
- ✨ Orange color scheme matching Open Food Facts branding
- 🎯 Improved hover effects and visual hierarchy
- 📱 Mobile-friendly card design
- 🌈 Enhanced Nutri-Score badge colors

### 2. Canada-Only API (off_api_service.py)
- 🚀 Single API endpoint: `ca.openfoodfacts.org`
- ⚡ Faster response times (no world fallback)
- 🇨🇦 All results filtered to Canadian products

### 3. Data Preparation (prepare_canada_data.py)
- 📊 Converts parquet to DuckDB-ready format
- 🔍 Filters products by "en:canada" country tag
- ✅ Includes error handling and progress feedback

## 🐛 Troubleshooting

**Problem:** "No products found" 
- ✅ Have you run `python prepare_canada_data.py`?
- ✅ Is the backend server running on port 8000?
- ✅ Check browser console for API errors

**Problem:** Extension won't connect to backend
- ✅ Ensure backend is running: `http://localhost:8000/health`
- ✅ Check CORS in `.env`: `CORS_ORIGINS=["*"]`
- ✅ Reload extension after backend restart

**Problem:** Data preparation script fails
- ✅ Install requirements: `pip install pandas pyarrow`
- ✅ Check if `~/Downloads/food.parquet` exists
- ✅ Ensure `data/` directory exists

## 📚 Query Examples

The system uses smart intent parsing for natural language queries:

**Dietary filters:**
- "vegan snacks"
- "gluten-free bread"  
- "organic products"

**Nutrient constraints:**
- "low sugar cereal"
- "high protein breakfast"
- "low fat yogurt"

**Calorie limitations:**
- "under 200 calories granola"
- "less than 100 kcal cookies"

**Combined:**
- "low sugar vegan snacks under 100 calories"

## 🔧 Configuration

Edit `.env` to customize:

```env
# Change database (Canada only recommended)
PARQUET_GLOB=data/products_canada.parquet

# Adjust result limit
DEFAULT_RESULT_LIMIT=20

# Enable Ollama for enhanced parsing (optional)
SLM_ENABLED=False
```

## 📖 Next Steps

1. ✅ Complete the data preparation above
2. 🚀 Start the backend server
3. 🎨 Load the extension in Chrome
4. 🔍 Test with natural language queries
5. 📊 Explore product insights and recommendations

Good luck! 🍊
