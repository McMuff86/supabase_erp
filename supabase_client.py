import os
from typing import Optional
from dotenv import load_dotenv, find_dotenv
from supabase import Client, create_client


_supabase_client: Optional[Client] = None


def get_supabase() -> Client:
    """Create or return a cached Supabase client using env vars.

    Required env vars:
      - SUPABASE_URL
      - SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    # Load .env from project root or parent folders. Override to ensure values are present.
    load_dotenv(find_dotenv(), override=True)
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        raise RuntimeError(
            "Missing SUPABASE_URL and/or SUPABASE_{SERVICE_ROLE_KEY|ANON_KEY} in environment"
        )

    _supabase_client = create_client(url, key)
    return _supabase_client


