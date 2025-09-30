from typing import List, Dict
from supabase_client import get_supabase


def fetch_clients(limit: int = 50) -> List[Dict]:
    sb = get_supabase()
    # Adjust table name to match your Supabase table. Screenshot shows `clients`.
    response = sb.table("clients").select("*").limit(limit).execute()
    # Supabase-py v2 returns .data field
    return response.data or []


if __name__ == "__main__":
    rows = fetch_clients(limit=100)
    for row in rows:
        print(row)
    print(f"Returned {len(rows)} rows")


