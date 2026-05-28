import re
import httpx
import asyncio

def extract_urls(text: str) -> list:
    """
    Extracts all URLs from markdown links [text](url) and raw http/https strings.
    Returns a list of unique URLs.
    """
    # Markdown link pattern: [label](url)
    md_pattern = r"\[.*?\]\((https?://[^\s)]+)\)"
    md_urls = re.findall(md_pattern, text)
    
    # Raw URL pattern (ignoring ones already in markdown brackets)
    raw_pattern = r"\bhttps?://[a-zA-Z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+\b"
    raw_urls = re.findall(raw_pattern, text)
    
    all_urls = list(set(md_urls + raw_urls))
    return all_urls

async def check_url_health(url: str, client: httpx.AsyncClient) -> dict:
    """
    Checks the status of a URL using an async HTTP client.
    First tries HEAD, then falls back to GET on failure.
    """
    try:
        # Try HEAD request first for efficiency
        resp = await client.head(url, follow_redirects=True, timeout=3.0)
        # Some servers block HEAD requests, so check if status is 405 or 404/403 and retry with GET
        if resp.status_code in (404, 405, 403):
            resp = await client.get(url, follow_redirects=True, timeout=4.0)
            
        if resp.status_code >= 400:
            return {"url": url, "status": "failed", "code": resp.status_code, "reason": f"HTTP status {resp.status_code}"}
        return {"url": url, "status": "passed", "code": resp.status_code, "reason": "Link is healthy"}
    except httpx.ConnectError:
        return {"url": url, "status": "failed", "code": None, "reason": "Connection failed (potential hallucinated link)"}
    except httpx.TimeoutException:
        return {"url": url, "status": "warning", "code": None, "reason": "Request timed out"}
    except Exception as e:
        return {"url": url, "status": "failed", "code": None, "reason": f"Error: {str(e)}"}

async def verify_citations_and_links(text: str, source: str) -> dict:
    """
    Verifies grounding citations and tests their HTTP accessibility.
    """
    urls = extract_urls(text)
    
    # Search chatbots like Perplexity, Gemini should ideally ground their claims
    is_search_source = source.lower() in ("perplexity", "perplexity pro", "gemini", "gemini 1.5 pro", "gemini 1.5 flash")
    
    if not urls:
        if is_search_source:
            # Issue a warning if a search engine chatbot has no citations/links
            return {
                "status": "warning",
                "message": f"Source '{source}' is a search-enabled assistant, but no external citations or URLs were found in its output.",
                "details": {"citations_found": 0, "link_checks": []}
            }
        return {
            "status": "passed",
            "message": "No external URLs or citations found (none expected for this source).",
            "details": {"citations_found": 0, "link_checks": []}
        }
        
    # Verify links concurrently
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    async with httpx.AsyncClient(limits=limits, headers={"User-Agent": "VerifyAI/1.0"}) as client:
        tasks = [check_url_health(url, client) for url in urls]
        results = await asyncio.gather(*tasks)
        
    failed_links = [r for r in results if r["status"] == "failed"]
    warning_links = [r for r in results if r["status"] == "warning"]
    
    status = "passed"
    msg_parts = []
    
    if failed_links:
        # If there are broken links, the validation fails (indicating link hallucination)
        status = "failed"
        broken_desc = [f"{r['url']} ({r['reason']})" for r in failed_links]
        msg_parts.append(f"Broken links detected: " + ", ".join(broken_desc))
    if warning_links:
        warn_desc = [f"{r['url']} ({r['reason']})" for r in warning_links]
        msg_parts.append(f"Unresponsive links: " + ", ".join(warn_desc))
        if status == "passed":
            status = "warning"
            
    summary_message = f"All {len(urls)} links checked are healthy." if status == "passed" else " | ".join(msg_parts)
    
    return {
        "status": status,
        "message": summary_message,
        "details": {
            "citations_found": len(urls),
            "link_checks": results
        }
    }
