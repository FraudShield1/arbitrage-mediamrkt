"""
Load and stress tests for the MediaMarkt scraper using Locust.
"""

from locust import HttpUser, task, between

class ScraperLoadTestUser(HttpUser):
    """
    Locust user class to simulate a user scraping MediaMarkt.
    """
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks

    # The host would be the mock server if running this against a test environment
    # e.g., locust -f tests/load/test_scraper_load.py --host http://localhost:8001
    # where 8001 is the port of the mock_mediamarkt_server.

    @task
    def scrape_first_page(self):
        """Simulates scraping the first page of search results."""
        self.client.get("/pages/search-results-page?q=+")

    @task(3) # This task will be 3 times more likely to be chosen
    def scrape_paginated_results(self):
        """Simulates scraping subsequent pages."""
        for page_num in range(2, 6): # Scrape pages 2 through 5
            self.client.get(f"/pages/search-results-page?q=+&page={page_num}", name="/pages/search-results-page")

    @task
    def scrape_product_detail(self):
        """Simulates visiting a product detail page."""
        # A real test would use product URLs extracted from the search results
        self.client.get("/product/some-product-name", name="/product/[name]")

# To run this test:
# 1. Start the mock_mediamarkt_server.py on a specific port (e.g., 8001)
#    `uvicorn tests.mocks.mock_mediamarkt_server:mock_mediamarkt_app --port 8001`
# 2. Run Locust:
#    `locust -f tests/load/test_scraper_load.py --host http://localhost:8001`
# 3. Open the Locust web UI (usually http://localhost:8089) and start the test.

# Note on stress testing scenarios:
# - High Volume: Increase the number of users and spawn rate in the Locust UI.
# - Stress Scenarios (limited proxies, failures):
#   These are harder to simulate with Locust alone. They typically require
#   manipulating the test environment itself. For example:
#   - To test limited proxies, you would run the scraper service with a small, shared pool of proxies.
#   - To test network failures, you could use a tool like `toxiproxy` to inject latency or failures
#     between the scraper and the target server (or mock server).
#   - Prometheus would then be used to monitor the scraper's performance (e.g., error rates, retry counts, latency)
#     under these adverse conditions. The prometheus.yml file would configure Prometheus to scrape
#     metrics from the application's /metrics endpoint. 