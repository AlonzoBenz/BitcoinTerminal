from src.fetchers import http


def parse_global(js):
    d = js["data"]
    return {"dominance_pct": float(d["market_cap_percentage"]["btc"]),
            "total_mcap_usd": float(d["total_market_cap"]["usd"])}


def fetch_global():
    return parse_global(http.get("https://api.coingecko.com/api/v3/global"))
