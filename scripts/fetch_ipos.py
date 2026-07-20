"""Fetch the official Nasdaq IPO calendar and write data/ipos.json for the app.

Runs daily via GitHub Actions. Stdlib only — no dependencies.
"""
import json
import os
import re
import urllib.request
from datetime import date, datetime, timezone

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15")


def fetch_month(yyyy_mm):
    url = f"https://api.nasdaq.com/api/ipo/calendar?date={yyyy_mm}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get("data") or {}


def to_num(s):
    if not s:
        return 0
    digits = re.sub(r"[^0-9.]", "", str(s))
    try:
        return float(digits) if digits else 0
    except ValueError:
        return 0


def to_iso(mdy):
    try:
        return datetime.strptime(mdy, "%m/%d/%Y").date().isoformat()
    except (ValueError, TypeError):
        return None


def convert(row, status, date_field):
    iso = to_iso(row.get(date_field))
    if not iso:
        return None
    return {
        "date": iso,
        "exchange": row.get("proposedExchange") or "",
        "name": row.get("companyName") or "",
        "numberOfShares": int(to_num(row.get("sharesOffered"))),
        "price": row.get("proposedSharePrice") or "",
        "status": status,
        "symbol": row.get("proposedTickerSymbol") or "",
        "totalSharesValue": to_num(row.get("dollarValueOfSharesOffered")),
    }


def main():
    today = date.today()
    months = [today.strftime("%Y-%m")]
    nxt = (today.replace(day=1).toordinal() + 32)
    months.append(date.fromordinal(nxt).replace(day=1).strftime("%Y-%m"))

    ipos, seen = [], set()
    for m in months:
        data = fetch_month(m)
        for section, status, date_field in (
            ("priced", "priced", "pricedDate"),
            ("upcoming", "expected", "expectedPriceDate"),
        ):
            for row in (data.get(section) or {}).get("rows") or []:
                item = convert(row, status, date_field)
                if item and row.get("dealID") not in seen:
                    seen.add(row.get("dealID"))
                    ipos.append(item)

    ipos.sort(key=lambda i: i["date"])
    out = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "Nasdaq official IPO calendar",
        "ipoCalendar": ipos,
    }
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "data"), exist_ok=True)
    path = os.path.join(os.path.dirname(__file__), "..", "data", "ipos.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    print(f"wrote {len(ipos)} IPOs to data/ipos.json")


if __name__ == "__main__":
    main()
