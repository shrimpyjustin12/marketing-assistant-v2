# Quick Start Guide

Get the AI Marketing Dashboard running in under 5 minutes.

## Requirements

- Python 3.10+
- Node.js 18+
- OpenAI API key ([get one here](https://platform.openai.com/api-keys))

## Option 1: Using the Start Script (Recommended)

```bash
# Make the script executable (first time only)
chmod +x start.sh

# Run both frontend and backend
./start.sh
```

## Option 2: Manual Start

### Terminal 1 - Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Terminal 2 - Frontend
```bash
cd frontend
npm install
npm run dev
```

## Using the Dashboard

1. **Open the app**: Go to `http://localhost:5173`

2. **Add your API key**: 
   - Click the ⚙️ settings icon (top right)
   - Paste your OpenAI API key
   - Click Save

3. **Upload sales data**:
   - Drag and drop a CSV file, or click to browse
   - Use `sample_data.csv` for testing

4. **Generate content**:
   - Review the sales summary
   - Click "Generate Marketing Content"
   - Wait for AI to generate captions, hashtags, and ideas

5. **Copy and use**:
   - Click the copy button next to any content
   - Paste into your social media posts

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Port 8000 already in use | Kill existing process or use `--port 8001` |
| CSV parsing error | Check your CSV format matches the supported formats |
| API key error | Verify your OpenAI API key is valid and has credits |
| "Model not found" | Use a valid model name like `gpt-4o` or `gpt-4o-mini` |

## Sample CSV Data

A `sample_data.csv` file is included for testing. You can also create your own:

```csv
date,item_name,quantity_sold,category
2025-01-01,Pho Beef,25,Noodles
2025-01-01,Banh Mi,18,Sandwich
2025-01-02,Spring Rolls,30,Appetizer
```

## Next Steps

- Read `docs/main.tex` for full technical documentation
- Modify the system prompt in `backend/content_generator.py` to customize AI output
- Adjust the UI in `frontend/src/App.jsx` and `frontend/src/App.css`

