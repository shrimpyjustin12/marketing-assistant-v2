"""
CSV Processing Module
Parses Toast Menu Breakdown CSV data and generates trend summaries for AI content generation.
Supports Toast POS export format with revenue data.
"""
# UPDATED: Fixed performacne tags function - March 2026

import pandas as pd
from io import StringIO
from typing import List, Dict, Any, Optional


def parse_csv(csv_content: str) -> pd.DataFrame:
    """Parse CSV content into a pandas DataFrame."""
    # Normalize line endings (handle CRLF, CR, LF) and fix trailing commas
    # Toast exports have mixed line endings and trailing commas on data rows
    csv_content = csv_content.replace('\r\n', '\n').replace('\r', '\n')
    lines = csv_content.strip().split('\n')
    fixed_lines = [line.rstrip(',').strip() for line in lines]
    csv_content = '\n'.join(fixed_lines)
    
    df = pd.read_csv(StringIO(csv_content))
    
    # Drop unnamed/empty columns (Toast exports have these from ,, in header)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed', na=False)]
    
    # Also drop columns that are completely empty or just whitespace
    df = df.loc[:, df.columns.str.strip() != '']
    
    # Handle Toast format column names (may have spaces and different naming)
    # Create a lowercase mapping for case-insensitive matching
    column_mapping = {
        'sales category': 'category',
        'item name': 'item_name', 
        'quantity': 'quantity',
        'avg price': 'avg_price',
        'gross sales': 'gross_sales',
        'discount amount': 'discount_amount',
        'net sales': 'net_sales',
        # Legacy format
        'quantity_sold': 'quantity',
        'date': 'date'
    }
    
    # Rename columns using case-insensitive matching
    new_columns = {}
    for col in df.columns:
        col_lower = col.lower().strip()
        if col_lower in column_mapping:
            new_columns[col] = column_mapping[col_lower]
    
    df = df.rename(columns=new_columns)
    print(f"Columns after renaming: {list(df.columns)}")
    
    # Check if this is Toast format (has item_name and category)
    if 'item_name' in df.columns and 'category' in df.columns:
        print(f"Detected Toast format. Total rows: {len(df)}")
        
        # Filter out rows where item_name is empty, NaN, or whitespace
        # First, fill NaN with empty string, then strip whitespace
        df['item_name'] = df['item_name'].fillna('').astype(str).str.strip()
        
        # Keep only rows with actual item names
        df = df[df['item_name'] != '']
        
        print(f"Rows after filtering empty items: {len(df)}")
        
        # Clean numeric columns
        numeric_cols = ['quantity', 'avg_price', 'gross_sales', 'discount_amount', 'net_sales']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Ensure we have data
        if df.empty:
            raise ValueError("No item data found in CSV. Make sure the CSV contains rows with Item Name values.")
    
    # Legacy format support
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


def get_top_items(df: pd.DataFrame, limit: int = 5) -> List[Dict[str, Any]]:
    """Get top-selling items by quantity and revenue."""
    if df.empty:
        return []
    
    # Group by item name in case of duplicates
    if 'net_sales' in df.columns:
        item_sales = df.groupby('item_name').agg({
            'quantity': 'sum',
            'net_sales': 'sum',
            'avg_price': 'mean'
        }).reset_index()
        item_sales = item_sales.sort_values('quantity', ascending=False).head(limit)
        
        return [
            {
                "item_name": row['item_name'],
                "quantity": int(row['quantity']),
                "net_sales": round(row['net_sales'], 2),
                "avg_price": round(row['avg_price'], 2)
            }
            for _, row in item_sales.iterrows()
        ]
    else:
        # Legacy format without revenue
        item_sales = df.groupby('item_name')['quantity'].sum().reset_index()
        item_sales = item_sales.sort_values('quantity', ascending=False).head(limit)
        
        return [
            {"item_name": row['item_name'], "quantity": int(row['quantity'])}
            for _, row in item_sales.iterrows()
        ]


def add_performance_tags(top_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Add performance tags to top items based on sales data."""
    if not top_items:
        return top_items
    
    # Find max values for comparison
    max_quantity = max(item['quantity'] for item in top_items)
    max_revenue = max(item.get('net_sales', 0) for item in top_items)
    
    tagged_items = []
    for item in top_items:
        item_with_tag = item.copy()
        
        # Determine tags (can be multiple, comma-separated)
        tags = []
        
        # Hot seller (highest quantity)
        if item['quantity'] == max_quantity and max_quantity > 0:
            tags.append('Hot Seller')
        
        # Premium (high price + good sales)
        elif item.get('avg_price', 0) > 15 and item['quantity'] > 50:
            tags.append('Premium Performer')
        
        # High revenue driver
        elif item.get('net_sales', 0) == max_revenue and max_revenue > 0:
            tags.append('High Revenue Driver')
        
        # Rising star (good quantity but not top)
        elif item['quantity'] > (max_quantity * 0.7):
            tags.append('Rising Star')
        
        # Join tags with comma if multiple
        item_with_tag['performance_tag'] = ', '.join(tags) if tags else None
            
        tagged_items.append(item_with_tag)
    
    return tagged_items


def get_top_categories(df: pd.DataFrame, limit: int = 5) -> List[Dict[str, Any]]:
    """Get top-selling categories by quantity and revenue."""
    if df.empty:
        return []
    
    if 'net_sales' in df.columns:
        category_sales = df.groupby('category').agg({
            'quantity': 'sum',
            'net_sales': 'sum'
        }).reset_index()
        category_sales = category_sales.sort_values('net_sales', ascending=False).head(limit)
        
        return [
            {
                "category": row['category'],
                "quantity": int(row['quantity']),
                "net_sales": round(row['net_sales'], 2)
            }
            for _, row in category_sales.iterrows()
        ]
    else:
        # Legacy format
        category_sales = df.groupby('category')['quantity'].sum().reset_index()
        category_sales = category_sales.sort_values('quantity', ascending=False).head(limit)
        
        return [
            {"category": row['category'], "quantity": int(row['quantity'])}
            for _, row in category_sales.iterrows()
        ]


def get_insights(df: pd.DataFrame) -> List[Dict[str, str]]:
    """Generate business insights from the data."""
    insights = []
    
    if df.empty:
        return [{"type": "info", "text": "No data available for insights"}]
    
    # Top seller insight
    if len(df) > 0 and 'quantity' in df.columns:
        top_idx = df['quantity'].idxmax()
        top_item = df.loc[top_idx]
        insights.append({
            "type": "bestseller",
            "text": f"{top_item['item_name']} is the top seller with {int(top_item['quantity'])} units sold"
        })
    
    # Revenue insights (Toast format only)
    if 'net_sales' in df.columns and df['net_sales'].sum() > 0:
        total_revenue = df['net_sales'].sum()
        
        # Category revenue breakdown
        category_revenue = df.groupby('category')['net_sales'].sum()
        if len(category_revenue) > 0:
            top_category = category_revenue.idxmax()
            top_cat_pct = (category_revenue[top_category] / total_revenue * 100)
            insights.append({
                "type": "revenue",
                "text": f"{top_category} drives {top_cat_pct:.0f}% of total revenue (${category_revenue[top_category]:,.2f})"
            })
        
        # Top revenue item
        top_rev_idx = df['net_sales'].idxmax()
        top_revenue_item = df.loc[top_rev_idx]
        insights.append({
            "type": "top_revenue",
            "text": f"{top_revenue_item['item_name']} generates the most revenue at ${top_revenue_item['net_sales']:,.2f}"
        })
        
        # Discount insight
        if 'discount_amount' in df.columns:
            total_discount = df['discount_amount'].sum()
            if total_discount > 0:
                discount_pct = (total_discount / (total_revenue + total_discount)) * 100
                insights.append({
                    "type": "discount",
                    "text": f"Total discounts: ${total_discount:,.2f} ({discount_pct:.1f}% of gross sales)"
                })
        
        # High-value items (avg price > $15)
        if 'avg_price' in df.columns:
            high_value = df[df['avg_price'] > 15].copy()
            if len(high_value) > 0:
                top_premium_idx = high_value['quantity'].idxmax()
                top_premium = high_value.loc[top_premium_idx]
                insights.append({
                    "type": "premium",
                    "text": f"{top_premium['item_name']} is the top premium item (${top_premium['avg_price']:.2f} avg) with {int(top_premium['quantity'])} sales"
                })
    
    # Legacy date-based insights
    elif 'date' in df.columns:
        df_copy = df.copy()
        df_copy['month'] = df_copy['date'].dt.month_name()
        monthly_category = df_copy.groupby(['month', 'category'])['quantity'].sum().reset_index()
        for month in monthly_category['month'].unique():
            month_data = monthly_category[monthly_category['month'] == month]
            if not month_data.empty:
                top_cat_idx = month_data['quantity'].idxmax()
                top_category = month_data.loc[top_cat_idx]
                insights.append({
                    "type": "trend",
                    "text": f"Higher {top_category['category'].lower()} sales in {month}"
                })
                if len(insights) >= 3:
                    break
    
    return insights[:5]  # Limit to 5 insights


def get_date_range(df: pd.DataFrame) -> Optional[Dict[str, str]]:
    """Extract date range if date column exists."""
    if 'date' not in df.columns:
        return None

    start = df['date'].min()
    end = df['date'].max()

    return {
        "start": start.strftime("%b %d, %Y"),
        "end": end.strftime("%b %d, %Y")
    }


def generate_summary(csv_content: str) -> Dict[str, Any]:
    """
    Main function to process CSV and generate a structured summary.
    
    Returns:
        Dictionary with top_items, top_categories, and insights
    """
    df = parse_csv(csv_content)

    date_range = get_date_range(df)

    # Get top items
    top_items = get_top_items(df)
    print(f"Got {len(top_items)} top items")  # Debug log
    
    # Add performance tags to top items
    top_items_with_tags = add_performance_tags(top_items)
    print(f"After tagging, first item keys: {top_items_with_tags[0].keys() if top_items_with_tags else 'No items'}")  # Debug log
    
    summary = {
        "date_range": date_range,
        "top_items": top_items_with_tags,  # MUST use the tagged version
        "top_categories": get_top_categories(df),
        "insights": get_insights(df)
    }
    
    return summary