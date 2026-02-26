"""
Content Generator Module
Uses LangChain + OpenAI to generate marketing content from sales summaries.
Enhanced to support revenue-based insights from Toast POS data.
"""

import json
from typing import Dict, Any, Generator
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# System prompt for the marketing assistant
SYSTEM_PROMPT = """You are the social media manager of the restaurant itself — not a marketer, not an AI.

Write posts the way a real local restaurant would speak to customers. You MUST generate DIFFERENT content for Instagram vs TikTok.

PLATFORM GUIDELINES:

📸 INSTAGRAM (Feed/Grid)
- Tone: Polished, aesthetic, warm.
- Style: 1-2 short paragraphs with line breaks.
- Emojis: Use 2-4 per caption.
- Structure: Mood Hook → Community Milestone → Gentle CTA.
- Hashtags: 8-12 targeted, rotating through categories.

🎵 TIKTOK
- Tone: Casual, conversational, punchy.
- Style: ONE short sentence maximum.
- Hook: Strong opener (POV, "The neighborhood's favorite...").
- Hashtags: 3-5 viral tags (#foodtok, #fyp).

📌 THE "SOCIAL PROOF" RULE (CRITICAL - NO LISTING DATA):
- NEVER include exact decimal prices (e.g., NO "$15.28"). If price is mentioned, round it (e.g., "$15").
- NEVER list revenue (e.g., NO "Generated $4,500").
- NEVER mention "units sold" or "sales."
- INSTEAD, turn numbers into "Community Milestones":
  * "Over 300 bowls served this month! 🔥"
  * "301 of you chose our Pho Beef since we started this month's count."
  * "Our neighborhood favorite just hit a new record: 300+ bowls served."
- **THE VIBE CHECK:** If the caption sounds like a business report, it is WRONG. It should sound like a proud owner sharing a success.

📌 CAPTION VARIATION & ROTATION:
- Rotate between these 4 angles so they never repeat:
  1. THE WEATHER: "Perfect for this [rainy/cold/sunny] day."
  2. THE GRATITUDE: "Huge thanks to the 300+ people who swung by for Pho this week."
  3. THE CRAVING: "POV: You finally get that first sip of broth."
  4. THE LOCAL SPOT: "Keeping [City/Neighborhood] fed and happy."

📌 HASHTAG VARIATION RULES:
- Generate 8-12 hashtags for Instagram; 3-5 for TikTok.
- Rotate through categories: Food type, Mood, Occasion, Location, Quality, Action.
- NEVER repeat the exact same combination.

IMPORTANT RULES:
- Mention menu items by name.
- Sound human, not corporate.
- Never mention "data," "analytics," or "AI."

You MUST respond with valid JSON in this exact format:
{{
  "instagram": {{
    "caption": "Your Instagram caption here 🍜\n\nSecond paragraph ❤️",
    "hashtags": ["#tag1", "#tag2", ...]
  }},
  "tiktok": {{
    "caption": "Your snappy TikTok hook 👀",
    "hashtags": ["#tag1", "#tag2", ...]
  }},
  "promotion_ideas": [
    {{"text": "Specific promotion idea", "reason": "Internal business reason based on metrics"}},
    {{"text": "Specific promotion idea", "reason": "Internal business reason based on metrics"}},
    {{"text": "Specific promotion idea", "reason": "Internal business reason based on metrics"}}
  ]
}}
"""


def build_user_prompt(summary: Dict[str, Any]) -> str:
    """Build the user prompt from the sales summary with revenue data support."""
    lines = ["Here is a summary of recent sales data:", ""]

    # Top-selling items with revenue info
    if summary.get("top_items"):
        lines.append("Top-selling items:")
        for item in summary["top_items"]:
            if item.get('net_sales'):
                lines.append(f"- {item['item_name']}: {item['quantity']} units sold, ${item['net_sales']:,.2f} revenue, ${item['avg_price']:.2f} avg price")
            else:
                lines.append(f"- {item['item_name']}: {item['quantity']} units sold")
        lines.append("")

    # Top categories with revenue info
    if summary.get("top_categories"):
        lines.append("Top categories:")
        for cat in summary["top_categories"]:
            if cat.get('net_sales'):
                lines.append(f"- {cat['category']}: {cat['quantity']} units, ${cat['net_sales']:,.2f} revenue")
            else:
                lines.append(f"- {cat['category']}: {cat['quantity']} units")
        lines.append("")

    # Business insights
    if summary.get("insights"):
        lines.append("Key business insights:")
        for insight in summary["insights"]:
            lines.append(f"- {insight['text']}")
        lines.append("")

    # Legacy monthly trends support
    if summary.get("monthly_trends"):
        lines.append("Observed trends:")
        for trend in summary["monthly_trends"]:
            lines.append(f"- {trend['trend'].capitalize()} in {trend['month']}.")
        lines.append("")

    lines.append("Based on this data, generate Instagram content, TikTok content, and promotion ideas following the platform guidelines.")
    lines.append("Remember: Instagram needs 8-12 hashtags, TikTok needs 3-5 hashtags.")

    return "\n".join(lines)


def parse_llm_response(response_text: str) -> Dict[str, Any]:
    """Parse and validate the LLM response."""
    try:
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

        # Check for new format (instagram + tiktok)
        if "instagram" in result and "tiktok" in result and "promotion_ideas" in result:
            # Validate Instagram structure
            if "caption" not in result["instagram"] or "hashtags" not in result["instagram"]:
                raise ValueError("Instagram must have caption and hashtags")
            if not isinstance(result["instagram"]["hashtags"], list):
                raise ValueError("Instagram hashtags must be a list")
                
            # Validate TikTok structure
            if "caption" not in result["tiktok"] or "hashtags" not in result["tiktok"]:
                raise ValueError("TikTok must have caption and hashtags")
            if not isinstance(result["tiktok"]["hashtags"], list):
                raise ValueError("TikTok hashtags must be a list")
                
            # Validate promotion ideas
            for idea in result["promotion_ideas"]:
                if not isinstance(idea, dict):
                    raise ValueError("promotion ideas must contain objects")
                if "text" not in idea or "reason" not in idea:
                    raise ValueError("Each promotion idea must have text and reason")
            
            return result
            
        # Check for old format (captions + hashtags)
        elif "captions" in result and "hashtags" in result and "promotion_ideas" in result:
            print("Warning: Received old format, converting to new format...")
            # Convert old format to new format
            converted = {
                "instagram": {
                    "caption": result["captions"][0] if result["captions"] else "Check out our delicious food!",
                    "hashtags": result["hashtags"][:8]  # Take first 8 hashtags
                },
                "tiktok": {
                    "caption": result["captions"][1] if len(result["captions"]) > 1 else (result["captions"][0] if result["captions"] else "This food is amazing!"),
                    "hashtags": result["hashtags"][:3]  # Take first 3 hashtags
                },
                "promotion_ideas": result["promotion_ideas"]
            }
            return converted
        else:
            raise ValueError("Response missing required keys. Expected either 'instagram'/'tiktok' format or 'captions' format")

    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse LLM response as JSON: {e}")


def generate_content_stream(
    summary: Dict[str, Any], 
    api_key: str, 
    model: str = "gpt-5-mini-2025-08-07"
) -> Generator[str, None, None]:
    """
    Generate marketing content with streaming for real-time feedback.
    """
    if not api_key or len(api_key) < 10:
        yield json.dumps({"error": "Invalid API key. Please enter a valid OpenAI API key."})
        return

    try:
        yield json.dumps({"status": "connecting", "message": "Connecting to AI..."})
        
        llm = ChatOpenAI(
            model=model,
            temperature=1,
            api_key=api_key,
            streaming=True
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "{user_input}")
        ])
        
        user_prompt = build_user_prompt(summary)
        
        yield json.dumps({"status": "generating", "message": "Generating marketing content..."})
        
        chain = prompt | llm
        full_response = ""
        
        for chunk in chain.stream({"user_input": user_prompt}):
            if hasattr(chunk, 'content'):
                full_response += chunk.content
                yield json.dumps({"status": "streaming", "partial": len(full_response)})
        
        yield json.dumps({"status": "processing", "message": "Processing response..."})
        
        result = parse_llm_response(full_response)
        yield json.dumps({"status": "complete", "data": result})
        
    except Exception as e:
        error_msg = str(e).lower()
        
        if "authentication" in error_msg or "api key" in error_msg or "invalid_api_key" in error_msg:
            yield json.dumps({"error": "Invalid OpenAI API key. Please check your API key and try again."})
        elif "rate_limit" in error_msg or "rate limit" in error_msg:
            yield json.dumps({"error": "Rate limit exceeded. Please wait a moment and try again."})
        elif "model" in error_msg and ("not found" in error_msg or "does not exist" in error_msg):
            yield json.dumps({"error": f"Model '{model}' not found. Please check the model name."})
        elif "connection" in error_msg:
            yield json.dumps({"error": "Cannot connect to OpenAI. Please check your internet connection."})
        else:
            yield json.dumps({"error": f"Error: {str(e)}"})


def generate_content(
    summary: Dict[str, Any], 
    api_key: str, 
    model: str = "gpt-5-mini-2025-08-07"
) -> Dict[str, Any]:
    """
    Generate marketing content from a sales summary (non-streaming version).
    """
    if not api_key or len(api_key) < 10:
        raise ValueError("Invalid API key. Please enter a valid OpenAI API key.")

    try:
        llm = ChatOpenAI(
            model=model,
            temperature=1,
            api_key=api_key
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "{user_input}")
        ])
        
        user_prompt = build_user_prompt(summary)
        
        chain = prompt | llm
        response = chain.invoke({"user_input": user_prompt})
        
        return parse_llm_response(response.content)
        
    except Exception as e:
        error_msg = str(e)
        if "authentication" in error_msg.lower() or "api key" in error_msg.lower():
            raise ValueError("Invalid OpenAI API key. Please check your API key.")
        elif "rate_limit" in error_msg.lower():
            raise ValueError("Rate limit exceeded. Please wait a moment and try again.")
        elif "model" in error_msg.lower() and "not found" in error_msg.lower():
            raise ValueError(f"Model '{model}' not found. Please use a valid model name.")
        else:
            raise ValueError(f"Error: {error_msg}")