import argparse
import json
from typing import Dict, List
from supabase_client import get_supabase
from postgrest.exceptions import APIError


def get_next_int_id(sb) -> int:
    # Fetch highest current id and return next integer
    res = sb.table("clients").select("id").order("id", desc=True).limit(1).execute()
    rows = res.data or []
    if not rows:
        return 1
    try:
        current_max = int(rows[0]["id"])
    except (KeyError, TypeError, ValueError):
        raise RuntimeError("Top row id is not an integer; cannot compute next id.")
    return current_max + 1


def parse_sets(sets: List[str]) -> Dict:
    result: Dict[str, str] = {}
    for item in sets or []:
        if "=" not in item:
            raise ValueError(f"--set expects key=value, got: {item}")
        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"Empty key in --set: {item}")
        result[key] = value
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Insert a row into the public.clients table via Supabase.")
    parser.add_argument(
        "--json",
        type=str,
        help="JSON payload for the row, e.g. '{\"name\":\"Acme GmbH\",\"email\":\"info@acme.de\"}'",
    )
    parser.add_argument(
        "--set",
        action="append",
        help="Provide key=value pairs (can be repeated). Example: --set name=Acme --set email=info@acme.de",
    )
    parser.add_argument(
        "--use-next-id",
        action="store_true",
        help="Compute next integer id as max(id)+1 if you didn't pass an explicit id.",
    )
    args = parser.parse_args()

    if not args.json and not args.set:
        print("No data provided. Use --json '{...}' or --set key=value (repeatable).")
        return

    payload: Dict
    if args.json:
        payload = json.loads(args.json)
        if not isinstance(payload, dict):
            raise ValueError("JSON must represent an object (a single row).")
    else:
        payload = parse_sets(args.set)

    sb = get_supabase()
    try:
        if args.use_next_id and "id" not in payload:
            payload["id"] = get_next_int_id(sb)

        # Adjust table name if your table differs
        resp = sb.table("clients").insert(payload).execute()
        print("Inserted:", resp.data)
        print(f"Done. Inserted {len(resp.data or [])} row(s).")
    except APIError as e:
        # Common case: PK conflict due to non-auto-increment id column
        print("Insert failed:", getattr(e, "message", str(e)))
        try:
            details = getattr(e, "details", None)
            code = getattr(e, "code", None)
            if code == "23505":  # unique_violation
                print(
                    "Hint: Your `clients.id` may not be auto-generated. "
                    "Make the `id` column identity/serial or use a UUID default."
                )
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()


