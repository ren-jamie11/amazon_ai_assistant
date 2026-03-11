# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Validation Commands

**IMPORTANT**: After every code change, validate the build succeeds

## Commands

```bash
# Run the main app
streamlit run app.py

# Install dependencies
pip install -r requirements.txt
```

## Secrets Setup

Create `.streamlit/secrets.toml` (never commit this file). It must include:
- `OPENAI_API_KEY` — OpenAI API key
- `GOOGLE_GENAI_API_KEY` — Google Generative AI key
- `PASS_<USERNAME>` entries for each user (e.g. `PASS_JAMIE`)
- `gcp_service_account` — Google Sheets service account JSON
- `sheet.name` — Target Google Sheet name

See `secrets.toml.example` for the expected structure.

## Architecture

### Main Files
- **`app.py`** — Primary Streamlit app (900+ lines). Multi-tab interface: Image Analysis, Title & Keywords, Listing Writer, Analytics, Rewrite & Grammar.
- **`app_one_product.py`** — Simplified single-product variant (ignore unless told otherwise)
- **`helpers_ai_prompting.py`** — All AI model calls (OpenAI GPT, Google Gemini) and image processing (base64 encoding, PIL conversion). Contains prompt strings.
- **`helpers_analytics.py`** — Data loading, filtering, clustering, and visualization logic for keyword/category analysis.
- **`user_login.py`** — Session-based multi-user authentication with password check against secrets.

### Data Layer
Product data lives in `data_files/<Product>/<Subcategory>/` as parquet files:
- `*_bullet_labels.parquet` — Titles and product metadata
- `*_bullet_keywords.parquet` — Keyword clusters
- `*_bullet_clusters.parquet` — Category clustering data
- `*_bullet_diagram.parquet` — Category frequency data
- `*_keyword_phrases.parquet` — Common keyword phrases
- `*_secondary_keywords.txt` — Additional keyword suggestions

Current products: **Mugs**, **Picture Frames**, **Vases**. Adding a new product requires adding its parquet files following this naming convention and updating the product selector in `app.py`.

### AI Integration
- **OpenAI** (GPT models): image specs extraction, title generation, listing writing, keyword grammar fixes
- **Google Gemini**: vision-based image analysis, title/listing generation (alternative pipeline)
- All AI calls are logged to Google Sheets (user, timestamp, function, input, output) via `gspread`

### Caching
Uses `@st.cache_data` and `@st.cache_resource` for product parquet files and Google Sheets connections. Clear cache via Streamlit's built-in UI or restart the app when data files change.
