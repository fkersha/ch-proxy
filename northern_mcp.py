# file: northern_mcp.py
from typing import Any, List, Union, Dict
import asyncio
import os
import httpx
from mcp.server.fastmcp import FastMCP

CH_WORKER_BASE = "https://ch-api.felixmkershaw.workers.dev/advanced"

mcp = FastMCP("northern")  # Server name shown to clients


def _norm_sic(sic_codes: Union[str, List[str], None]) -> str:
    """
    Accept "41100,41202" OR ["41100","41202"] OR "41100"
    Return a clean comma-separated string without spaces.
    """
    if sic_codes is None:
        return ""
    if isinstance(sic_codes, list):
        items = [str(c).strip() for c in sic_codes if str(c).strip()]
    else:
        items = [c.strip() for c in str(sic_codes).split(",") if c.strip()]
    return ",".join(items)


@mcp.tool()
async def ch_search(
    location: str,
    sic_codes: Union[str, List[str], None] = None,
    size: int = 100
) -> Dict[str, Any]:
    """
    Search Companies House proxy by location/SIC and size.
    Calls your Cloudflare Worker:
      GET /advanced?location=<>&sic_codes=<csv>&size=<int>
    Returns parsed JSON (or a structured error with status/text).
    """
    params = {
        "location": str(location).strip(),
        "size": int(size),
    }
    sic_csv = _norm_sic(sic_codes)
    if sic_csv:
        params["sic_codes"] = sic_csv

    headers = {
        # If your Worker expects a key, set CH_WORKER_KEY in env and uncomment below.
        "User-Agent": "northern-mcp/1.0"
    }
    key = os.getenv("CH_WORKER_KEY")
    if key:
        # Adjust header name if your Worker expects e.g. "x-api-key"
        headers["Authorization"] = f"Bearer {key}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(CH_WORKER_BASE, params=params, headers=headers)
            ct = resp.headers.get("content-type", "")
            if resp.status_code >= 400:
                return {
                    "ok": False,
                    "status": resp.status_code,
                    "content_type": ct,
                    "text": resp.text[:2000]
                }
            try:
                data = resp.json()
            except Exception:
                data = {"text": resp.text}
            return {"ok": True, "status": resp.status_code, "data": data}
        except httpx.HTTPError as e:
            return {"ok": False, "error": f"http_error: {e.__class__.__name__}", "detail": str(e)}


@mcp.tool()
async def http_get(url: str) -> Dict[str, Any]:
    """
    Simple HTTP GET (for debugging connectivity).
    """
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            r = await client.get(url)
            out: Dict[str, Any] = {"status": r.status_code, "headers": dict(r.headers)}
            try:
                out["json"] = r.json()
            except Exception:
                out["text"] = r.text[:4000]
            return out
        except Exception as e:
            return {"error": str(e)}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true", help="Run MCP over HTTP (for StackAI).")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.http:
        # HTTP transport (best for StackAI)
        mcp.run_http(host=args.host, port=args.port)
    else:
        # Stdio transport (for local CLI clients)
        mcp.run_stdio()

