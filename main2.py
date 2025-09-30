import os
from urllib.parse import quote_plus
import psycopg2
from dotenv import load_dotenv

load_dotenv()

host = os.getenv("PGHOST")
port = os.getenv("PGPORT")
db   = os.getenv("PGDATABASE")
user = os.getenv("PGUSER")
pwd  = os.getenv("PGPASSWORD")

# DSN verwenden – so kommen die libpq-Parameter sicher an:
dsn = (
    f"postgresql://{quote_plus(user)}:{quote_plus(pwd)}@{host}:{port}/{db}"
    f"?sslmode=require&gssencmode=disable&target_session_attrs=any"
)

conn = psycopg2.connect(dsn)
with conn, conn.cursor() as cur:
    cur.execute("select now();")
    print("OK:", cur.fetchone()[0])
print("done.")
