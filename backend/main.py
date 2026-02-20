"""
FastAPI Backend for Marketing Dashboard
Supports Toast POS Menu Breakdown CSV format with revenue data.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from csv_processor import generate_summary
from content_generator import generate_content, generate_content_stream

app = FastAPI(
    title="Marketing Dashboard API",
    description="Generate marketing content from sales data",
    version="1.0.0"
)

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for request/response
class TopItem(BaseModel):
    item_name: str
    quantity: int
    net_sales: Optional[float] = None
    avg_price: Optional[float] = None
    performance_tag: Optional[Dict[str, str]] = None


class TopCategory(BaseModel):
    category: str
    quantity: int
    net_sales: Optional[float] = None


class Insight(BaseModel):
    type: str
    text: str


class SalesSummary(BaseModel):
    top_items: List[TopItem]
    top_categories: List[TopCategory]
    insights: List[Insight]


class ContentRequest(BaseModel):
    api_key: str
    model: Optional[str] = "gpt-5-mini-2025-08-07"


class SalesSummaryWithConfig(SalesSummary):
    api_key: str
    model: Optional[str] = "gpt-5-mini-2025-08-07"


@app.get("/")
async def root():
    return {"status": "online", "message": "Marketing Dashboard API is running"}


@app.post("/upload-csv", response_model=SalesSummary)
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload a CSV file and return a summary of the sales data.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    
    try:
        content = await file.read()
        csv_text = content.decode('utf-8')
        
        summary_data = generate_summary(csv_text)
        
        return summary_data
    
    except Exception as e:
        print(f"Error processing CSV: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")


@app.post("/generate-content")
async def generate_marketing_content(request: SalesSummaryWithConfig):
    """
    Generate marketing content based on the sales summary.
    """
    try:
        # Convert Pydantic models to dict for the generator
        summary_dict = {
            "top_items": [item.model_dump() for item in request.top_items],
            "top_categories": [cat.model_dump() for cat in request.top_categories],
            "insights": [ins.model_dump() for ins in request.insights],
        }
        
        content = generate_content(
            summary_dict, 
            api_key=request.api_key, 
            model=request.model or "gpt-5-mini-2025-08-07"
        )
        
        return content
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating content: {str(e)}")


@app.post("/generate-content-stream")
async def generate_marketing_content_stream(request: SalesSummaryWithConfig):
    """
    Generate marketing content with streaming response for real-time feedback.
    """
    summary_dict = {
        "top_items": [item.model_dump() for item in request.top_items],
        "top_categories": [cat.model_dump() for cat in request.top_categories],
        "insights": [ins.model_dump() for ins in request.insights],
    }
    
    async def event_generator():
        for chunk in generate_content_stream(
            summary_dict, 
            api_key=request.api_key, 
            model=request.model or "gpt-5-mini-2025-08-07"
        ):
            yield f"data: {chunk}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")