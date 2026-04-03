"""
Content Generator Module
Uses LangChain + OpenAI to generate marketing content from sales summaries.
Enhanced to support revenue-based insights from Toast POS data.
"""

import json
from typing import Dict, Any, Generator, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import time

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
  * "Hundreds of you chose this favorite this month."
  * "301 of you chose our Pho Beef since we started this month's count."
  * "Our neighborhood favorite just hit a new record: 300+ bowls served."
- **THE VIBE CHECK:** If the caption sounds like a business report, it is WRONG. It should sound like a proud owner sharing a success.

📌 CAPTION VARIATION & ROTATION:
- Rotate between these 4 angles so they never repeat:
  1. THE WEATHER: "Perfect for this [rainy/cold/sunny] day."
  2. THE GRATITUDE: "Huge thanks to everyone who stopped by for this favorite this week."
  3. THE CRAVING: "POV: You finally get that first bite you've been craving."
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

INSTAGRAM_PROMPT = """You are the restaurant's social media manager.

You are generating ONLY Instagram content. Follow ALL rules below.

GLOBAL RULES (apply to everything):
- Sound like a real local restaurant owner/manager. Human, warm, not corporate.
- Never mention "data", "analytics", "AI", "machine learning", or anything like that.
- Never include revenue, net sales, or “generated $X”.
- Never include "units sold" / "sales" / “quantity sold”.
- If mentioning price, round it (NO decimals like $15.28).
- Mention real menu items by name.
- Must be noticeably DIFFERENT from previous_text if provided (avoid repeating phrases).

INSTAGRAM RULES (must follow):
- Tone: Polished, aesthetic, warm.
- Length: 1–2 short paragraphs max with line breaks.
- Emojis: 2–4.
- Structure: Mood Hook → Community Milestone (no “units sold”) → Gentle CTA.
- Hashtags: 8–12 targeted hashtags, rotating categories (Food type, Mood, Occasion, Location, Quality, Action).
- Do NOT repeat the exact same hashtag combination from previous_text.

CONTENT ISOLATION (critical):
- Do NOT include TikTok ideas, TikTok concepts, video instructions, shot lists, POV lines, or “TikTok”.
- Do NOT include promotion/recommendation lists, action plans, or “promotion ideas”.
- No headings like "Instagram post:" or bullet lists.

OUTPUT FORMAT (critical):
Return ONLY raw JSON (no markdown, no extra keys, no extra text) in EXACTLY this shape:
{{
  "caption": "Your Instagram caption here\\n\\nSecond paragraph here",
  "hashtags": ["#tag1", "#tag2", "..."]
}}
"""

TIKTOK_PROMPT = """You are the restaurant's social media manager.

You are generating ONLY TikTok content. Follow ALL rules below.

GLOBAL RULES (apply to everything):
- Sound like a real local restaurant owner/manager. Human, warm, not corporate.
- Never mention "data", "analytics", "AI", "machine learning", or anything like that.
- Never include revenue, net sales, or “generated $X”.
- Never include "units sold" / "sales" / “quantity sold”.
- If mentioning price, round it (NO decimals like $15.28).
- Mention real menu items by name.
- Must be noticeably DIFFERENT from previous_text if provided (avoid repeating phrases).

TIKTOK RULES (must follow):
- ONE sentence maximum (short, punchy).
- Strong hook opener (POV, “You know it’s a good day when…”, etc.).
- Tone: Casual, conversational.
- Hashtags: 3–5, include viral-style tags like #foodtok / #fyp when appropriate.

CONTENT ISOLATION (critical):
- Do NOT write Instagram-style paragraphs.
- Do NOT include promotion/recommendation lists, action plans, or “promotion ideas”.
- No headings like "TikTok:".

OUTPUT FORMAT (critical):
Return ONLY raw JSON (no markdown, no extra keys, no extra text) in EXACTLY this shape:
{{
  "caption": "One-sentence hook",
  "hashtags": ["#tag1", "#tag2", "..."]
}}
"""
ACTIONS_PROMPT = """You are the restaurant's marketing planner.

You are generating ONLY 3 recommended promotion actions. Follow ALL rules below.

GLOBAL RULES (apply to everything):
- Do NOT mention "data", "analytics", "AI", or model names.
- Do NOT include revenue, net sales, or “generated $X”.
- Do NOT include "units sold" / "sales" / “quantity sold”.
- If mentioning price, round it (NO decimals like $15.28).
- Must be noticeably DIFFERENT from previous_text if provided (avoid repeating phrases).
- Keep actions realistic for a small local restaurant.

ACTIONS RULES (must follow):
- Output exactly 3 actions.
- Each action should be specific and runnable (not vague).
- Phrase as a short action line (not a paragraph).
- No captions, no hashtags.

CONTENT ISOLATION (critical):
- Do NOT include Instagram captions.
- Do NOT include TikTok hooks.
- Do NOT include hashtags.
- No headings like "Promotion ideas:".

OUTPUT FORMAT (critical):
Return ONLY raw JSON (no markdown, no extra keys, no extra text) in EXACTLY this shape:
{{
  "actions": [
    "Action 1",
    "Action 2",
    "Action 3"
  ]
}}
"""

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

        # If the whole response is double-encoded JSON, decode again
        if isinstance(result, str):
            result = json.loads(result)

        # If the assistant accidentally put the whole object inside instagram.caption,
        # try to recover from it.
        if (
            isinstance(result, dict)
            and "instagram" in result
            and isinstance(result["instagram"], dict)
            and isinstance(result["instagram"].get("caption"), str)
        ):
            caption_text = result["instagram"]["caption"].strip()
            if caption_text.startswith("{") and '"instagram"' in caption_text and '"tiktok"' in caption_text:
                nested = json.loads(caption_text)
                if isinstance(nested, dict) and "instagram" in nested and "tiktok" in nested:
                    result = nested

        # Validate final structure
        if "instagram" in result and "tiktok" in result and "promotion_ideas" in result:
            if not isinstance(result["instagram"], dict):
                raise ValueError("Instagram must be an object")
            if not isinstance(result["tiktok"], dict):
                raise ValueError("TikTok must be an object")

            if "caption" not in result["instagram"] or "hashtags" not in result["instagram"]:
                raise ValueError("Instagram must have caption and hashtags")
            if not isinstance(result["instagram"]["caption"], str):
                raise ValueError("Instagram caption must be a string")
            if not isinstance(result["instagram"]["hashtags"], list):
                raise ValueError("Instagram hashtags must be a list")

            if "caption" not in result["tiktok"] or "hashtags" not in result["tiktok"]:
                raise ValueError("TikTok must have caption and hashtags")
            if not isinstance(result["tiktok"]["caption"], str):
                raise ValueError("TikTok caption must be a string")
            if not isinstance(result["tiktok"]["hashtags"], list):
                raise ValueError("TikTok hashtags must be a list")

            # Reject captions that still look like raw JSON
            for platform in ("instagram", "tiktok"):
                caption = result[platform]["caption"].strip()
                if caption.startswith("{") and ('"instagram"' in caption or '"tiktok"' in caption):
                    raise ValueError(f"{platform} caption contains embedded JSON instead of plain caption text")

            for idea in result["promotion_ideas"]:
                if not isinstance(idea, dict):
                    raise ValueError("promotion ideas must contain objects")
                if "text" not in idea or "reason" not in idea:
                    raise ValueError("Each promotion idea must have text and reason")

            return result

        elif "captions" in result and "hashtags" in result and "promotion_ideas" in result:
            converted = {
                "instagram": {
                    "caption": result["captions"][0] if result["captions"] else "Check out our delicious food!",
                    "hashtags": result["hashtags"][:8]
                },
                "tiktok": {
                    "caption": result["captions"][1] if len(result["captions"]) > 1 else (
                        result["captions"][0] if result["captions"] else "This food is amazing!"
                    ),
                    "hashtags": result["hashtags"][:3]
                },
                "promotion_ideas": result["promotion_ideas"]
            }
            return converted

        else:
            raise ValueError("Response missing required keys. Expected either new or old format")

    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse LLM response as JSON: {e}")
    
def build_user_prompt(summary: Dict[str, Any]) -> str:
    lines = ["Here is a summary of recent sales data:", ""]

    selected_item_name = summary.get("selected_item")
    selected_item = None

    if selected_item_name and summary.get("top_items"):
        selected_item = next(
            (item for item in summary["top_items"] if item["item_name"] == selected_item_name),
            None
        )

    if selected_item:
        lines.append("IMPORTANT FOCUS ITEM:")
        lines.append(
            f"- The ONLY main item for this content is {selected_item['item_name']}."
        )
        lines.append(
            "Instagram caption, TikTok hook, hashtags, and promotion actions must all center on this item."
        )
        lines.append(
            "You may mention the restaurant generally, but do not make Pho Beef or any other item the star unless it is the selected item."
        )
        lines.append("")

    if summary.get("top_items"):
        lines.append("Top-selling items:")
        for item in summary["top_items"]:
            if item.get("net_sales"):
                lines.append(
                    f"- {item['item_name']}: {item['quantity']} units sold, "
                    f"${item['net_sales']:,.2f} revenue, ${item['avg_price']:.2f} avg price"
                )
            else:
                lines.append(f"- {item['item_name']}: {item['quantity']} units sold")
        lines.append("")

    if summary.get("top_categories"):
        lines.append("Top categories:")
        for cat in summary["top_categories"]:
            if cat.get("net_sales"):
                lines.append(
                    f"- {cat['category']}: {cat['quantity']} units, ${cat['net_sales']:,.2f} revenue"
                )
            else:
                lines.append(f"- {cat['category']}: {cat['quantity']} units")
        lines.append("")

    if summary.get("insights"):
        lines.append("Key business insights:")
        for insight in summary["insights"]:
            lines.append(f"- {insight['text']}")
        lines.append("")

    lines.append("Based on this data, generate Instagram content, TikTok content, and promotion ideas following the platform guidelines.")
    lines.append("Remember: Instagram needs 8-12 hashtags, TikTok needs 3-5 hashtags.")

    return "\n".join(lines)


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
        
def parse_platform_json(text: str) -> Dict[str, Any]:
    """Parse JSON that should contain only one platform section."""
    try:
        t = text.strip()

        if "```json" in t:
            start = t.find("```json") + 7
            end = t.find("```", start)
            t = t[start:end].strip()
        elif "```" in t:
            start = t.find("```") + 3
            end = t.find("```", start)
            t = t[start:end].strip()

        return json.loads(t)
    except Exception as e:
        raise ValueError(f"Failed to parse platform response as JSON: {e}")

def generate_platform_content(
    platform: str,
    summary: Dict[str, Any],
    api_key: str,
    model: str = "gpt-5-mini-2025-08-07",
    previous_text: Optional[str] = None,
    nonce: Optional[int] = None
) -> Dict[str, Any]:
    """
    Generate ONLY the requested platform content.
    platform: "instagram" | "tiktok" | "actions"
    """
    if not api_key or len(api_key) < 10:
        raise ValueError("Invalid API key. Please enter a valid OpenAI API key.")

    # pick the right system prompt
    if platform == "instagram":
        system_prompt = INSTAGRAM_PROMPT
    elif platform == "tiktok":
        system_prompt = TIKTOK_PROMPT
    elif platform == "actions":
        system_prompt = ACTIONS_PROMPT
    else:
        raise ValueError("platform must be one of: instagram, tiktok, actions")

    n = nonce or int(time.time())

    # Build the same user prompt you already use, but add variation controls
    user_prompt = build_user_prompt(summary)
    user_prompt += "\n\n"
    user_prompt += f"nonce={n}\n"
    if previous_text:
        user_prompt += f"previous_text={previous_text}\n"
        user_prompt += "Generate a NEW variation that avoids repeating phrases from previous_text.\n"

    llm = ChatOpenAI(
        model=model,
        temperature=1,
        api_key=api_key
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{user_input}")
    ])

    chain = prompt | llm
    response = chain.invoke({"user_input": user_prompt})

    result = parse_platform_json(response.content)

    # light validation per platform
    if platform in ("instagram", "tiktok"):
        if "caption" not in result or "hashtags" not in result or not isinstance(result["hashtags"], list):
            raise ValueError(f"{platform} response must contain caption (string) and hashtags (list)")
    if platform == "actions":
        if "actions" not in result or not isinstance(result["actions"], list) or len(result["actions"]) < 3:
            raise ValueError("actions response must contain actions: [..] with 3 items")
    
    return result