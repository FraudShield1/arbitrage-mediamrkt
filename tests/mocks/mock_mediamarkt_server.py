"""
Mock MediaMarkt server using FastAPI for integration tests.
"""

from fastapi import FastAPI, Response
from tests.mocks.mediamarkt_html import (
    MEDIAMARKT_PAGE_1_HTML,
    MEDIAMARKT_PAGE_2_HTML,
    MEDIAMARKT_EMPTY_PAGE_HTML,
    MEDIAMARKT_MALFORMED_HTML,
    MEDIAMARKT_ALTERNATIVE_SELECTORS_HTML
)

mock_mediamarkt_app = FastAPI()

@mock_mediamarkt_app.get("/pages/search-results-page")
async def search_results(page: int = 1):
    """
    Simulates the MediaMarkt search results page with pagination.
    """
    if page == 1:
        return Response(content=MEDIAMARKT_PAGE_1_HTML, media_type="text/html")
    elif page == 2:
        return Response(content=MEDIAMARKT_PAGE_2_HTML, media_type="text/html")
    else:
        # Return an empty page for any other page number to stop pagination
        return Response(content=MEDIAMARKT_EMPTY_PAGE_HTML, media_type="text/html")

@mock_mediamarkt_app.get("/product/{product_name}")
async def get_product_page(product_name: str):
    """
    Simulates a product detail page. For now, returns a simple HTML.
    This can be expanded to test scraping of detail pages if needed.
    """
    html_content = f"<html><body><h1>{product_name}</h1><p>Product details...</p></body></html>"
    return Response(content=html_content, media_type="text/html")

# Special endpoints for testing error conditions

@mock_mediamarkt_app.get("/malformed")
async def malformed_page():
    """Returns a page with malformed HTML."""
    return Response(content=MEDIAMARKT_MALFORMED_HTML, media_type="text/html")

@mock_mediamarkt_app.get("/alternative-selectors")
async def alternative_selectors_page():
    """Returns a page that uses different CSS selectors."""
    return Response(content=MEDIAMARKT_ALTERNATIVE_SELECTORS_HTML, media_type="text/html")

@mock_mediamarkt_app.get("/rate-limit")
async def rate_limit_endpoint():
    """Simulates a rate limit response."""
    return Response(content="Too many requests", status_code=429, headers={"Retry-After": "60"})

@mock_mediamarkt_app.get("/ip-ban")
async def ip_ban_endpoint():
    """Simulates an IP ban response."""
    return Response(content="Forbidden", status_code=403) 