"""
FastAPI Backend for Marketing Dashboard
Supports Toast POS Menu Breakdown CSV format with revenue data.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from typing import Literal  # add to imports

from csv_processor import generate_summary, build_top5_panels
from content_generator import generate_content, generate_content_stream, generate_platform_content

previous_summary = None

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


class ContentRequest(BaseModel):
    api_key: str
    model: Optional[str] = "gpt-5-mini-2025-08-07"

class ComparisonRow(BaseModel):
    item: str
    previous: int
    current: int
    percent_change: float
    prev_rank: Optional[int] = None
    curr_rank: Optional[int] = None
    rank_change: Optional[int] = None

class SalesSummary(BaseModel):
    top_items: List[TopItem]
    top_categories: List[TopCategory]
    insights: List[Insight]
    comparison: Optional[List[ComparisonRow]] = None

class SalesSummaryWithConfig(SalesSummary):
    api_key: str
    model: Optional[str] = "gpt-5-mini-2025-08-07"
    selected_item: Optional[str] = None


class SalesSummaryWithComparison(SalesSummary):
    comparison: Optional[List[ComparisonRow]] = None

class OldTopItemComparison(BaseModel):
    item_name: str
    prev_rank: int
    prev_qty: int
    curr_qty: int
    pct_change: Optional[float] = None
    status: str  # "Still Top 5" / "Dropped from Top 5"

class NewTopItem(BaseModel):
    item_name: str
    curr_rank: int
    curr_qty: int

class Top5Panels(BaseModel):
    old_top5_comparison: List[OldTopItemComparison]
    new_top5: List[NewTopItem]

class SalesSummaryWithPanels(SalesSummary):  # or whatever your base summary model is named
    top5_panels: Optional[Top5Panels] = None
    
@app.get("/")
async def root():
    return {"status": "online", "message": "Marketing Dashboard API is running"}


@app.post("/upload-csv", response_model=SalesSummaryWithPanels)
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    try:
        content = await file.read()
        csv_text = content.decode("utf-8")

        summary_data = generate_summary(csv_text)

        global previous_summary

        if previous_summary:
            summary_data["top5_panels"] = build_top5_panels(
                previous_summary, summary_data, top_n=5
            )

        previous_summary = summary_data
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
            "selected_item": request.selected_item,
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
        "selected_item": request.selected_item,
    }
    
    async def event_generator():
        for chunk in generate_content_stream(
            summary_dict, 
            api_key=request.api_key, 
            model=request.model or "gpt-5-mini-2025-08-07"
        ):
            yield f"data: {chunk}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

class PlatformRefreshRequest(SalesSummaryWithConfig):
    platform: Literal["instagram", "tiktok", "actions"]
    previous_text: Optional[str] = None
    nonce: Optional[int] = None

@app.post("/generate-platform")
async def generate_platform(request: PlatformRefreshRequest):
    """
    Generate ONLY one platform section (instagram OR tiktok OR actions).
    Used for per-card refresh/regenerate.
    """
    try:
        summary_dict = {
            "top_items": [item.model_dump() for item in request.top_items],
            "top_categories": [cat.model_dump() for cat in request.top_categories],
            "insights": [ins.model_dump() for ins in request.insights],
            "selected_item": request.selected_item,
        }

        content = generate_platform_content(
            platform=request.platform,
            summary=summary_dict,
            api_key=request.api_key,
            model=request.model or "gpt-5-mini-2025-08-07",
            previous_text=request.previous_text,
            nonce=request.nonce
        )

        return {"platform": request.platform, "data": content}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating platform content: {str(e)}")
    

