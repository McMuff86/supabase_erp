import os
from typing import List, Dict
from urllib.parse import quote_plus
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv


def fetch_clients(limit: int = 50) -> List[Dict]:
    load_dotenv()
    host = os.getenv("PGHOST")
    port = os.getenv("PGPORT")
    db = os.getenv("PGDATABASE")
    user = os.getenv("PGUSER")
    pwd = os.getenv("PGPASSWORD")

    dsn = (
        f"postgresql://{quote_plus(user)}:{quote_plus(pwd)}@{host}:{port}/{db}"
        f"?sslmode=require&gssencmode=disable&target_session_attrs=any"
    )

    with psycopg2.connect(dsn, cursor_factory=RealDictCursor) as conn:
        with conn.cursor() as cur:
            cur.execute("select * from public.clients order by id asc limit %s;", (limit,))
            rows = cur.fetchall()
            return [dict(r) for r in rows]


if __name__ == "__main__":
    rows = fetch_clients(limit=100)
    for row in rows:
        print(row)
    print(f"Returned {len(rows)} rows")


