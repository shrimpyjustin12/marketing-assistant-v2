"""
Vercel Serverless Function - Main API Handler
Supports Toast POS Menu Breakdown CSV format with revenue data.
API key is read from server-side environment variables (not exposed to the browser).
"""

import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import pandas as pd
from io import StringIO
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# System prompt — platform-aware marketing content
SYSTEM_PROMPT = """You are a marketing strategist for a small food business.
Your job is to analyze sales data and produce platform-specific social media content.
Do not mention analytics, data processing, or AI. Write as if a human marketer created this.

You MUST respond with valid JSON in this exact format:
{{
    "recommended_actions": [
        "Concise, actionable strategy point 1",
        "Concise, actionable strategy point 2",
        "Concise, actionable strategy point 3"
    ],
    "instagram": {{
        "caption": "Instagram caption here (polished tone, use emojis, 1-2 short paragraphs, highlight bestsellers and value)",
        "hashtags": ["#Hashtag1", "#Hashtag2", "#Hashtag3", "#Hashtag4", "#Hashtag5", "#Hashtag6", "#Hashtag7", "#Hashtag8"]
    }},
    "tiktok": {{
        "caption": "TikTok caption here (strong hook, casual/conversational tone, short, end with engagement question, use trend language)",
        "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"]
    }}
}}

Rules:
- recommended_actions: Exactly 3 concise, actionable strategy points based on the data (e.g. combo deals, promotions, loyalty programs).
- instagram.caption: Polished and aesthetic tone. Use emojis. Write 1-2 short paragraphs. Highlight the top sellers by name.
- instagram.hashtags: 8-12 targeted hashtags. Mix broad and niche (e.g. #VietnameseFood #PhoLovers #FoodieFinds).
- tiktok.caption: Start with a strong hook (e.g. "POV:", "This item outsold EVERYTHING..."). Keep it casual and conversational. End with an engagement question. Use 2-4 hashtags only.
- tiktok.hashtags: 2-4 hashtags max. Use trending/casual tags (e.g. #foodtok #viral)."""


# Pydantic models
class TopItem(BaseModel):
    item_name: str
    quantity: int
    net_sales: Optional[float] = None
    avg_price: Optional[float] = None
    badge: Optional[str] = None

class TopCategory(BaseModel):
    category: str
    quantity: int
    net_sales: Optional[float] = None
    badge: Optional[str] = None

class Insight(BaseModel):
    type: str
    text: str

class SalesSummary(BaseModel):
    top_items: List[TopItem]
    top_categories: List[TopCategory]
    insights: List[Insight]
    data_period: Optional[str] = None

class GenerateRequest(BaseModel):
    top_items: List[TopItem]
    top_categories: List[TopCategory]
    insights: List[Insight]
    model: Optional[str] = "gpt-5-mini-2025-08-07"

class InstagramContent(BaseModel):
    caption: str
    hashtags: List[str]

class TikTokContent(BaseModel):
    caption: str
    hashtags: List[str]

class MarketingContent(BaseModel):
    recommended_actions: List[str]
    instagram: InstagramContent
    tiktok: TikTokContent


# CSV Processing Functions
def parse_csv(csv_content: str) -> pd.DataFrame:
    """Parse CSV content into a pandas DataFrame."""
    csv_content = csv_content.replace('\r\n', '\n').replace('\r', '\n')
    lines = csv_content.strip().split('\n')
    fixed_lines = [line.rstrip(',').strip() for line in lines]
    csv_content = '\n'.join(fixed_lines)
    
    df = pd.read_csv(StringIO(csv_content))
    
    df = df.loc[:, ~df.columns.str.contains('^Unnamed', na=False)]
    df = df.loc[:, df.columns.str.strip() != '']
    
    column_mapping = {
        'sales category': 'category',
        'item name': 'item_name', 
        'quantity': 'quantity',
        'avg price': 'avg_price',
        'gross sales': 'gross_sales',
        'discount amount': 'discount_amount',
        'net sales': 'net_sales',
        'quantity_sold': 'quantity',
        'date': 'date'
    }
    
    new_columns = {}
    for col in df.columns:
        col_lower = col.lower().strip()
        if col_lower in column_mapping:
            new_columns[col] = column_mapping[col_lower]
    
    df = df.rename(columns=new_columns)
    
    if 'item_name' in df.columns and 'category' in df.columns:
        df['item_name'] = df['item_name'].fillna('').astype(str).str.strip()
        df = df[df['item_name'] != '']
        
        numeric_cols = ['quantity', 'avg_price', 'gross_sales', 'discount_amount', 'net_sales']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        if df.empty:
            raise ValueError("No item data found in CSV. Make sure the CSV contains rows with Item Name values.")
    
    elif 'date' in df.columns:
        required_columns = ['date', 'item_name', 'quantity', 'category']
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        df['date'] = pd.to_datetime(df['date'])
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
    
    else:
        available = list(df.columns)
        raise ValueError(f"CSV format not recognized. Available columns: {available}")
    
    return df


def _format_date(d):
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def get_data_period(df: pd.DataFrame):
    if 'date' not in df.columns or df.empty:
        return None
    try:
        dates = pd.to_datetime(df['date'], errors='coerce').dropna()
        if dates.empty:
            return None
        d_min, d_max = dates.min(), dates.max()
        if d_min == d_max:
            return _format_date(d_min)
        return f"{_format_date(d_min)} – {_format_date(d_max)}"
    except Exception:
        return None


def get_top_items(df: pd.DataFrame, limit: int = 5):
    if df.empty:
        return []
    
    if 'net_sales' in df.columns:
        item_sales = df.groupby('item_name').agg({
            'quantity': 'sum',
            'net_sales': 'sum',
            'avg_price': 'mean'
        }).reset_index()
        item_sales = item_sales.sort_values('quantity', ascending=False).head(limit)
        
        items = [
            {
                "item_name": row['item_name'],
                "quantity": int(row['quantity']),
                "net_sales": round(row['net_sales'], 2),
                "avg_price": round(row['avg_price'], 2),
                "badge": None
            }
            for _, row in item_sales.iterrows()
        ]
        if items:
            items[0]["badge"] = "Hot Seller"
            top_rev_idx = max(range(len(items)), key=lambda i: items[i]["net_sales"])
            if top_rev_idx == 0:
                items[0]["badge"] = "Hot Seller, Premium Performer"
            else:
                items[top_rev_idx]["badge"] = "Premium Performer"
        return items
    else:
        item_sales = df.groupby('item_name')['quantity'].sum().reset_index()
        item_sales = item_sales.sort_values('quantity', ascending=False).head(limit)
        
        items = [
            {"item_name": row['item_name'], "quantity": int(row['quantity']), "badge": None}
            for _, row in item_sales.iterrows()
        ]
        if items:
            items[0]["badge"] = "Hot Seller"
        return items


def get_top_categories(df: pd.DataFrame, limit: int = 5):
    if df.empty:
        return []
    
    if 'net_sales' in df.columns:
        category_sales = df.groupby('category').agg({
            'quantity': 'sum',
            'net_sales': 'sum'
        }).reset_index()
        category_sales = category_sales.sort_values('net_sales', ascending=False).head(limit)
        
        categories = [
            {
                "category": row['category'],
                "quantity": int(row['quantity']),
                "net_sales": round(row['net_sales'], 2),
                "badge": None
            }
            for _, row in category_sales.iterrows()
        ]
        if categories:
            categories[0]["badge"] = "High Revenue Driver"
        return categories
    else:
        category_sales = df.groupby('category')['quantity'].sum().reset_index()
        category_sales = category_sales.sort_values('quantity', ascending=False).head(limit)
        
        return [
            {"category": row['category'], "quantity": int(row['quantity'])}
            for _, row in category_sales.iterrows()
        ]


def get_insights(df: pd.DataFrame):
    insights = []
    
    if df.empty:
        return [{"type": "info", "text": "No data available for insights"}]
    
    if len(df) > 0 and 'quantity' in df.columns:
        top_idx = df['quantity'].idxmax()
        top_item = df.loc[top_idx]
        insights.append({
            "type": "bestseller",
            "text": f"{top_item['item_name']} is the top seller with {int(top_item['quantity'])} units sold"
        })
    
    if 'net_sales' in df.columns and df['net_sales'].sum() > 0:
        total_revenue = df['net_sales'].sum()
        
        category_revenue = df.groupby('category')['net_sales'].sum()
        if len(category_revenue) > 0:
            top_category = category_revenue.idxmax()
            top_cat_pct = (category_revenue[top_category] / total_revenue * 100)
            insights.append({
                "type": "revenue",
                "text": f"{top_category} drives {top_cat_pct:.0f}% of total revenue (${category_revenue[top_category]:,.2f})"
            })
        
        top_rev_idx = df['net_sales'].idxmax()
        top_revenue_item = df.loc[top_rev_idx]
        insights.append({
            "type": "top_revenue",
            "text": f"{top_revenue_item['item_name']} generates the most revenue at ${top_revenue_item['net_sales']:,.2f}"
        })
        
        if 'discount_amount' in df.columns:
            total_discount = df['discount_amount'].sum()
            if total_discount > 0:
                discount_pct = (total_discount / (total_revenue + total_discount)) * 100
                insights.append({
                    "type": "discount",
                    "text": f"Total discounts: ${total_discount:,.2f} ({discount_pct:.1f}% of gross sales)"
                })
        
        if 'avg_price' in df.columns:
            high_value = df[df['avg_price'] > 15].copy()
            if len(high_value) > 0:
                top_premium_idx = high_value['quantity'].idxmax()
                top_premium = high_value.loc[top_premium_idx]
                insights.append({
                    "type": "premium",
                    "text": f"{top_premium['item_name']} is the top premium item (${top_premium['avg_price']:.2f} avg) with {int(top_premium['quantity'])} sales"
                })
    
    return insights[:5]


def generate_summary(csv_content: str):
    df = parse_csv(csv_content)
    summary = {
        "top_items": get_top_items(df),
        "top_categories": get_top_categories(df),
        "insights": get_insights(df)
    }
    if 'date' in df.columns:
        period = get_data_period(df)
        if period:
            summary["data_period"] = period
    return summary


# Content generation helpers
def build_user_prompt(summary):
    lines = ["Here is a summary of recent sales data:", ""]
    
    if summary.get("top_items"):
        lines.append("Top-selling items:")
        for item in summary["top_items"]:
            if item.get('net_sales'):
                lines.append(f"- {item['item_name']}: {item['quantity']} units, ${item['net_sales']:,.2f} revenue, ${item['avg_price']:.2f} avg price")
            else:
                lines.append(f"- {item['item_name']}: {item['quantity']} units")
        lines.append("")
    
    if summary.get("top_categories"):
        lines.append("Top categories:")
        for cat in summary["top_categories"]:
            if cat.get('net_sales'):
                lines.append(f"- {cat['category']}: {cat['quantity']} units, ${cat['net_sales']:,.2f} revenue")
            else:
                lines.append(f"- {cat['category']}: {cat['quantity']} units")
        lines.append("")
    
    if summary.get("insights"):
        lines.append("Key business insights:")
        for insight in summary["insights"]:
            lines.append(f"- {insight['text']}")
        lines.append("")
    
    lines.append("Based on this data, generate:")
    lines.append("1. Top 3 recommended actions (concise strategy points)")
    lines.append("2. An Instagram caption with 8-12 hashtags")
    lines.append("3. A TikTok caption with 2-4 hashtags")
    
    return "\n".join(lines)


def parse_llm_response(response_text: str):
    text = response_text.strip()
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        text = text[start:end].strip()

    result = json.loads(text)

    if "recommended_actions" not in result or not isinstance(result["recommended_actions"], list):
        raise ValueError("Missing or invalid 'recommended_actions'")
    if "instagram" not in result or not isinstance(result["instagram"], dict):
        raise ValueError("Missing or invalid 'instagram'")
    if "tiktok" not in result or not isinstance(result["tiktok"], dict):
        raise ValueError("Missing or invalid 'tiktok'")

    for platform in ["instagram", "tiktok"]:
        if "caption" not in result[platform]:
            raise ValueError(f"Missing 'caption' in {platform}")
        if "hashtags" not in result[platform] or not isinstance(result[platform]["hashtags"], list):
            raise ValueError(f"Missing or invalid 'hashtags' in {platform}")

    return result


def _get_api_key() -> str:
    """Read OpenAI API key from environment."""
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key or len(key) < 10 or key == "your_openai_api_key_here":
        raise ValueError(
            "OpenAI API key is not configured on the server. "
            "Please set OPENAI_API_KEY in the environment variables."
        )
    return key


# Routes
@app.get("/")
@app.get("/api")
async def root():
    return JSONResponse(content={"status": "ok", "message": "Marketing Dashboard API"})

@app.post("/upload-csv")
@app.post("/api/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    try:
        content = await file.read()
        csv_content = content.decode('utf-8')
        summary = generate_summary(csv_content)
        return JSONResponse(content=summary)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")

@app.post("/generate-content-stream")
@app.post("/api/generate-content-stream")
async def generate_content_stream_endpoint(request: GenerateRequest):
    summary_dict = {
        "top_items": [item.model_dump() for item in request.top_items],
        "top_categories": [cat.model_dump() for cat in request.top_categories],
        "insights": [ins.model_dump() for ins in request.insights],
    }
    
    async def event_generator():
        model = request.model or "gpt-5-mini-2025-08-07"
        
        try:
            api_key = _get_api_key()
        except ValueError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return
        
        try:
            yield f"data: {json.dumps({'status': 'connecting', 'message': 'Connecting to AI...'})}\n\n"
            
            llm = ChatOpenAI(model=model, temperature=1, api_key=api_key, streaming=True)
            prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("human", "{user_input}")])
            user_prompt = build_user_prompt(summary_dict)
            
            yield f"data: {json.dumps({'status': 'generating', 'message': 'Generating marketing content...'})}\n\n"
            
            chain = prompt | llm
            full_response = ""
            
            for chunk in chain.stream({"user_input": user_prompt}):
                if hasattr(chunk, 'content'):
                    full_response += chunk.content
                    yield f"data: {json.dumps({'status': 'streaming', 'partial': len(full_response)})}\n\n"
            
            yield f"data: {json.dumps({'status': 'processing', 'message': 'Processing response...'})}\n\n"
            
            result = parse_llm_response(full_response)
            yield f"data: {json.dumps({'status': 'complete', 'data': result})}\n\n"
            
        except Exception as e:
            error_msg = str(e).lower()
            if "authentication" in error_msg or "api key" in error_msg:
                yield f"data: {json.dumps({'error': 'Invalid OpenAI API key. Please check the server configuration.'})}\n\n"
            elif "rate_limit" in error_msg:
                yield f"data: {json.dumps({'error': 'Rate limit exceeded. Please wait and try again.'})}\n\n"
            elif "model" in error_msg and "not found" in error_msg:
                yield f"data: {json.dumps({'error': f'Model not found. Please check the model name.'})}\n\n"
            elif "connection" in error_msg:
                yield f"data: {json.dumps({'error': 'Cannot connect to OpenAI. Please check your internet connection.'})}\n\n"
            else:
                yield f"data: {json.dumps({'error': f'Error: {str(e)}'})}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def catch_all(request: Request, path: str):
    return JSONResponse(content={"error": f"Route not found: /{path}", "method": request.method}, status_code=404)
