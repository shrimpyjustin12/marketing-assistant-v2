"""
FastAPI Backend for Marketing Dashboard
Supports Toast POS Menu Breakdown CSV format with revenue data.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional

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


class SalesSummaryWithConfig(BaseModel):
    top_items: List[TopItem]
    top_categories: List[TopCategory]
    insights: List[Insight]
    api_key: str
    model: Optional[str] = "gpt-5-mini-2025-08-07"


class PromotionIdea(BaseModel):
    text: str
    reason: str

class MarketingContent(BaseModel):
    captions: List[str]
    hashtags: List[str]
    promotion_ideas: List[PromotionIdea]


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Marketing Dashboard API"}


@app.post("/upload-csv", response_model=SalesSummary)
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload a CSV file and get a sales summary.
    
    Supports Toast Menu Breakdown format with columns:
    Sales Category, Item Name, Quantity, Avg Price, Gross Sales, Discount Amount, Net Sales
    """
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        # Read file content
        content = await file.read()
        csv_content = content.decode('utf-8')
        
        # Process CSV and generate summary
        summary = generate_summary(csv_content)
        
        return summary
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")


@app.post("/generate-content", response_model=MarketingContent)
async def generate_marketing_content(request: SalesSummaryWithConfig):
    """
    Generate marketing content from a sales summary (non-streaming).
    """
    try:
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
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)