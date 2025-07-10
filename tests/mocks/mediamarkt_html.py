"""
Mock HTML data for MediaMarkt product pages used in unit tests.
"""

# Sample HTML for first page with 10 products
MEDIAMARKT_PAGE_1_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Search Results - MediaMarkt</title>
</head>
<body>
    <div class="search-results">
        <!-- Product 1 -->
        <div class="product-wrapper" data-ean="1234567890123">
            <h2 class="product-title">
                <a href="/product/apple-iphone-15-pro-256gb-natural-titanium" class="product-link">
                    Apple iPhone 15 Pro (256GB) - Natural Titanium
                </a>
            </h2>
            <div class="brand" data-brand="Apple">Apple</div>
            <div class="price-container">
                <span class="price-original">€1.399,99</span>
                <span class="price">€1.199,99</span>
                <span class="discount-percentage">-14%</span>
            </div>
            <div class="stock-status">Em stock</div>
            <div class="category" data-category="Smartphones">Smartphones</div>
        </div>

        <!-- Product 2 -->
        <div class="product-wrapper" data-ean="9876543210987">
            <h2 class="product-title">
                <a href="/product/samsung-galaxy-s24-ultra-256gb-titanium-black" class="product-link">
                    Samsung Galaxy S24 Ultra (256GB) - Titanium Black
                </a>
            </h2>
            <div class="brand" data-brand="Samsung">Samsung</div>
            <div class="price-container">
                <span class="price-original">€1.499,99</span>
                <span class="price">€1.299,99</span>
                <span class="discount-percentage">-13%</span>
            </div>
            <div class="stock-status">Em stock</div>
            <div class="category" data-category="Smartphones">Smartphones</div>
        </div>

        <!-- Product 3 -->
        <div class="product-wrapper" data-ean="1122334455667">
            <h2 class="product-title">
                <a href="/product/sony-wh-1000xm5-wireless-headphones" class="product-link">
                    Sony WH-1000XM5 Wireless Noise Canceling Headphones
                </a>
            </h2>
            <div class="brand" data-brand="Sony">Sony</div>
            <div class="price-container">
                <span class="price">€349,99</span>
            </div>
            <div class="stock-status">Em stock</div>
            <div class="category" data-category="Audio">Audio</div>
        </div>

        <!-- Product 4 -->
        <div class="product-wrapper" data-ean="2233445566778" data-asin="B0CHX2F5QT">
            <h2 class="product-title">
                <a href="/product/macbook-air-m2-13-inch-256gb" class="product-link">
                    MacBook Air M2 13" (256GB) - Midnight
                </a>
            </h2>
            <div class="brand" data-brand="Apple">Apple</div>
            <div class="price-container">
                <span class="price-original">€1.299,00</span>
                <span class="price">€1.099,00</span>
                <span class="discount-percentage">-15%</span>
            </div>
            <div class="stock-status">Em stock</div>
            <div class="category" data-category="Laptops">Laptops</div>
        </div>

        <!-- Product 5 -->
        <div class="product-wrapper" data-ean="3344556677889">
            <h2 class="product-title">
                <a href="/product/lg-oled55c3psa-55-4k-oled-tv" class="product-link">
                    LG OLED55C3PSA 55" 4K OLED Smart TV
                </a>
            </h2>
            <div class="brand" data-brand="LG">LG</div>
            <div class="price-container">
                <span class="price-original">€1.899,99</span>
                <span class="price">€1.599,99</span>
                <span class="discount-percentage">-16%</span>
            </div>
            <div class="stock-status">Em stock</div>
            <div class="category" data-category="TVs">TVs</div>
        </div>

        <!-- Product 6 -->
        <div class="product-wrapper" data-ean="4455667788990">
            <h2 class="product-title">
                <a href="/product/dyson-v15-detect-absolute" class="product-link">
                    Dyson V15 Detect Absolute Cordless Vacuum
                </a>
            </h2>
            <div class="brand" data-brand="Dyson">Dyson</div>
            <div class="price-container">
                <span class="price">€699,99</span>
            </div>
            <div class="stock-status">Em stock</div>
            <div class="category" data-category="Home Appliances">Home Appliances</div>
        </div>

        <!-- Product 7 -->
        <div class="product-wrapper" data-ean="5566778899001">
            <h2 class="product-title">
                <a href="/product/nintendo-switch-oled-white" class="product-link">
                    Nintendo Switch OLED Model - White
                </a>
            </h2>
            <div class="brand" data-brand="Nintendo">Nintendo</div>
            <div class="price-container">
                <span class="price-original">€349,99</span>
                <span class="price">€299,99</span>
                <span class="discount-percentage">-14%</span>
            </div>
            <div class="stock-status">Em stock</div>
            <div class="category" data-category="Gaming">Gaming</div>
        </div>

        <!-- Product 8 -->
        <div class="product-wrapper" data-ean="6677889900112">
            <h2 class="product-title">
                <a href="/product/bose-quietcomfort-45-headphones" class="product-link">
                    Bose QuietComfort 45 Wireless Headphones
                </a>
            </h2>
            <div class="brand" data-brand="Bose">Bose</div>
            <div class="price-container">
                <span class="price">€329,99</span>
            </div>
            <div class="stock-status">Esgotado</div>
            <div class="category" data-category="Audio">Audio</div>
        </div>

        <!-- Product 9 -->
        <div class="product-wrapper" data-ean="7788990011223">
            <h2 class="product-title">
                <a href="/product/samsung-qe65qn95b-65-neo-qled-8k-tv" class="product-link">
                    Samsung QE65QN95B 65" Neo QLED 8K TV
                </a>
            </h2>
            <div class="brand" data-brand="Samsung">Samsung</div>
            <div class="price-container">
                <span class="price-original">€3.999,99</span>
                <span class="price">€3.199,99</span>
                <span class="discount-percentage">-20%</span>
            </div>
            <div class="stock-status">Em stock</div>
            <div class="category" data-category="TVs">TVs</div>
        </div>

        <!-- Product 10 -->
        <div class="product-wrapper" data-ean="8899001122334">
            <h2 class="product-title">
                <a href="/product/apple-watch-series-9-gps-45mm" class="product-link">
                    Apple Watch Series 9 GPS 45mm - Midnight Aluminum
                </a>
            </h2>
            <div class="brand" data-brand="Apple">Apple</div>
            <div class="price-container">
                <span class="price">€449,99</span>
            </div>
            <div class="stock-status">Em stock</div>
            <div class="category" data-category="Wearables">Wearables</div>
        </div>
    </div>

    <!-- Pagination -->
    <div class="pagination">
        <a href="/pages/search-results-page?q=+&page=2" class="next-page">Next</a>
    </div>
</body>
</html>
"""

# Sample HTML for second page with 5 products (last page)
MEDIAMARKT_PAGE_2_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Search Results - MediaMarkt - Page 2</title>
</head>
<body>
    <div class="search-results">
        <!-- Product 11 -->
        <div class="product-wrapper" data-ean="9900112233445">
            <h2 class="product-title">
                <a href="/product/google-pixel-8-pro-128gb-obsidian" class="product-link">
                    Google Pixel 8 Pro (128GB) - Obsidian
                </a>
            </h2>
            <div class="brand" data-brand="Google">Google</div>
            <div class="price-container">
                <span class="price-original">€1.099,99</span>
                <span class="price">€899,99</span>
                <span class="discount-percentage">-18%</span>
            </div>
            <div class="stock-status">Em stock</div>
            <div class="category" data-category="Smartphones">Smartphones</div>
        </div>

        <!-- Product 12 -->
        <div class="product-wrapper" data-ean="0011223344556">
            <h2 class="product-title">
                <a href="/product/xbox-series-x-1tb-console" class="product-link">
                    Xbox Series X 1TB Console
                </a>
            </h2>
            <div class="brand" data-brand="Microsoft">Microsoft</div>
            <div class="price-container">
                <span class="price">€499,99</span>
            </div>
            <div class="stock-status">Em stock</div>
            <div class="category" data-category="Gaming">Gaming</div>
        </div>

        <!-- Product 13 -->
        <div class="product-wrapper" data-ean="1122334455667">
            <h2 class="product-title">
                <a href="/product/tesla-model-s-plaid-charger" class="product-link">
                    Tesla Model S Plaid Wall Connector
                </a>
            </h2>
            <div class="brand" data-brand="Tesla">Tesla</div>
            <div class="price-container">
                <span class="price-original">€599,99</span>
                <span class="price">€499,99</span>
                <span class="discount-percentage">-17%</span>
            </div>
            <div class="stock-status">Indisponível</div>
            <div class="category" data-category="Auto">Auto</div>
        </div>

        <!-- Product 14 -->
        <div class="product-wrapper" data-ean="2233445566778">
            <h2 class="product-title">
                <a href="/product/philips-hue-starter-kit-e27" class="product-link">
                    Philips Hue White and Color Ambiance Starter Kit E27
                </a>
            </h2>
            <div class="brand" data-brand="Philips">Philips</div>
            <div class="price-container">
                <span class="price">€199,99</span>
            </div>
            <div class="stock-status">Em stock</div>
            <div class="category" data-category="Smart Home">Smart Home</div>
        </div>

        <!-- Product 15 -->
        <div class="product-wrapper" data-ean="3344556677889">
            <h2 class="product-title">
                <a href="/product/airpods-pro-2nd-generation" class="product-link">
                    AirPods Pro (2nd Generation) with MagSafe Case
                </a>
            </h2>
            <div class="brand" data-brand="Apple">Apple</div>
            <div class="price-container">
                <span class="price-original">€279,99</span>
                <span class="price">€229,99</span>
                <span class="discount-percentage">-18%</span>
            </div>
            <div class="stock-status">Em stock</div>
            <div class="category" data-category="Audio">Audio</div>
        </div>
    </div>

    <!-- No pagination on last page -->
    <div class="pagination">
        <span class="current-page">Last page</span>
    </div>
</body>
</html>
"""

# Empty page HTML for testing edge cases
MEDIAMARKT_EMPTY_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>No Results - MediaMarkt</title>
</head>
<body>
    <div class="search-results">
        <div class="no-results">
            <p>No products found matching your search criteria.</p>
        </div>
    </div>
</body>
</html>
"""

# HTML with malformed/incomplete product data for error testing
MEDIAMARKT_MALFORMED_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Search Results - MediaMarkt</title>
</head>
<body>
    <div class="search-results">
        <!-- Product with missing price -->
        <div class="product-wrapper" data-ean="1111111111111">
            <h2 class="product-title">
                <a href="/product/incomplete-product" class="product-link">
                    Incomplete Product
                </a>
            </h2>
            <div class="brand" data-brand="Unknown">Unknown</div>
            <!-- No price information -->
            <div class="stock-status">Em stock</div>
        </div>

        <!-- Product with missing title -->
        <div class="product-wrapper" data-ean="2222222222222">
            <div class="brand" data-brand="Test">Test</div>
            <div class="price-container">
                <span class="price">€99,99</span>
            </div>
            <div class="stock-status">Em stock</div>
        </div>

        <!-- Product with malformed EAN -->
        <div class="product-wrapper" data-ean="invalid-ean">
            <h2 class="product-title">
                <a href="/product/invalid-ean-product" class="product-link">
                    Product with Invalid EAN
                </a>
            </h2>
            <div class="brand" data-brand="Test">Test</div>
            <div class="price-container">
                <span class="price">€199,99</span>
            </div>
            <div class="stock-status">Em stock</div>
        </div>
    </div>
</body>
</html>
"""

# Sample HTML with alternative selectors for testing robustness
MEDIAMARKT_ALTERNATIVE_SELECTORS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Alternative Selectors - MediaMarkt</title>
</head>
<body>
    <div class="search-results">
        <!-- Product using alternative CSS classes -->
        <div class="ProductItem" data-product-ean="9999888877776">
            <h3 class="ProductItem-title">
                <a href="/product/alternative-selector-product">
                    Alternative Selector Product
                </a>
            </h3>
            <div class="ProductItem-brand">Alternative Brand</div>
            <div class="ProductItem-price">€299,99</div>
            <div class="availability">Disponível</div>
        </div>

        <!-- Product using data-testid attributes -->
        <div class="product-card" data-gtin="5555444433332">
            <h2 data-testid="product-title">
                <a href="/product/testid-product">TestID Product</a>
            </h2>
            <div data-testid="brand">TestID Brand</div>
            <div data-testid="price">€399,99</div>
            <div data-testid="stock">Available</div>
        </div>
    </div>
</body>
</html>
"""

# Sample response for network error simulation
NETWORK_ERROR_RESPONSE = {
    "error": "NetworkError",
    "message": "Connection timeout",
    "status_code": 408
}

# Sample response for rate limiting
RATE_LIMIT_RESPONSE = {
    "error": "RateLimitExceeded", 
    "message": "Too many requests",
    "status_code": 429,
    "retry_after": 60
}

# Sample response for IP ban
IP_BAN_RESPONSE = {
    "error": "IPBlocked",
    "message": "Your IP has been temporarily blocked",
    "status_code": 403
} 