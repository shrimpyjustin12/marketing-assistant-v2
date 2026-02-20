# AI Marketing Dashboard

A web application that transforms sales data into social media marketing content using AI. Upload your sales CSV, view insights, and generate promotional captions, hashtags, and marketing ideas.

## Features

- **CSV Upload**: Drag-and-drop file upload with support for multiple formats
- **Sales Analytics**: Automatic extraction of top items, categories, and business insights
- **AI Content Generation**: Generate marketing content using OpenAI's language models
- **Real-time Streaming**: See AI responses as they're generated
- **Copy to Clipboard**: One-click copy for all generated content

## Tech Stack

| Layer | Technologies |
|-------|--------------|
| **Frontend** | React 18, Vite, CSS3 |
| **Backend** | Python, FastAPI, Pandas |
| **AI** | LangChain, OpenAI API |

## Project Structure

```
Marketing-Agent/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── csv_processor.py     # CSV parsing and analysis
│   ├── content_generator.py # AI content generation
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main dashboard component
│   │   └── components/      # React components
│   └── package.json         # Node dependencies
├── docs/                    # Project documentation
├── sample_data.csv          # Sample CSV for testing
└── start.sh                 # Quick start script
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI API key

## Quick Start

The easiest way to run the project:

```bash
./start.sh
```

This starts both the backend (port 8000) and frontend (port 5173).

## Manual Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Usage

1. Open `http://localhost:5173` in your browser
2. Click the **Settings** icon and enter your OpenAI API key
3. Upload a CSV file (or use `sample_data.csv`)
4. Review the sales summary and insights
5. Click **Generate Marketing Content**
6. Copy the generated captions, hashtags, and ideas

## Supported CSV Formats

### Toast POS Format
```csv
Sales Category,Item Name,Modifier,,Avg Price,Quantity,Gross Sales,Discount Amount,Net Sales
Food,Pho Beef,,,15.28,301,4600.00,34.03,4565.97
```

### Simple Format
```csv
date,item_name,quantity_sold,category
2025-03-01,Pho Beef,24,Noodles
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/upload-csv` | POST | Upload CSV and get sales summary |
| `/generate-content-stream` | POST | Generate AI marketing content |

## Documentation

See the `docs/` folder for detailed project documentation including:
- Tools and technologies overview
- Build timeline
- Technical explanations of each component

## License

MIT
