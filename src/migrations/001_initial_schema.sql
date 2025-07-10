-- Initial database schema for Cross-Market Arbitrage Tool
-- Based on docs/dbscheme.md

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- Products table - stores scraped product data
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    ean VARCHAR(20),
    brand VARCHAR(100),
    category VARCHAR(100) NOT NULL,
    stock_status VARCHAR(20) NOT NULL,
    url VARCHAR(1000) NOT NULL,
    images TEXT[],
    specifications JSONB,
    scraped_at TIMESTAMP WITH TIME ZONE NOT NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'mediamarkt',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ASINs table - stores Amazon product catalog
CREATE TABLE asins (
    asin VARCHAR(10) PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    brand VARCHAR(100),
    category VARCHAR(100) NOT NULL,
    marketplace VARCHAR(5) NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Product-ASIN matches - stores matching results with confidence scores
CREATE TABLE product_asin_matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    asin VARCHAR(10) NOT NULL REFERENCES asins(asin) ON DELETE CASCADE,
    confidence_score DECIMAL(3,2) NOT NULL,
    match_method VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(product_id, asin)
);

-- Price alerts - stores generated arbitrage opportunities
CREATE TABLE price_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    asin VARCHAR(10) NOT NULL REFERENCES asins(asin) ON DELETE CASCADE,
    current_price DECIMAL(10,2) NOT NULL,
    average_price DECIMAL(10,2) NOT NULL,
    discount_percentage DECIMAL(5,2) NOT NULL,
    profit_potential DECIMAL(10,2) NOT NULL,
    confidence_score DECIMAL(3,2) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Keepa data - stores historical price data
CREATE TABLE keepa_data (
    asin VARCHAR(10) NOT NULL REFERENCES asins(asin) ON DELETE CASCADE,
    marketplace VARCHAR(5) NOT NULL,
    price_history JSONB NOT NULL,
    sales_rank_history JSONB,
    stats JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (asin, marketplace)
);

-- Scraping sessions - tracks scraping run status
CREATE TABLE scraping_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(50) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    products_scraped INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    error_details JSONB
);

-- System settings - stores configuration
CREATE TABLE system_settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_products_ean ON products(ean) WHERE ean IS NOT NULL;
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_scraped_at ON products(scraped_at);
CREATE INDEX idx_products_source ON products(source);
CREATE INDEX idx_products_price ON products(price);

CREATE INDEX idx_asins_marketplace ON asins(marketplace);
CREATE INDEX idx_asins_category ON asins(category);
CREATE INDEX idx_asins_brand ON asins(brand);

CREATE INDEX idx_product_asin_matches_product_id ON product_asin_matches(product_id);
CREATE INDEX idx_product_asin_matches_asin ON product_asin_matches(asin);
CREATE INDEX idx_product_asin_matches_confidence ON product_asin_matches(confidence_score);

CREATE INDEX idx_price_alerts_created_at ON price_alerts(created_at);
CREATE INDEX idx_price_alerts_severity ON price_alerts(severity);
CREATE INDEX idx_price_alerts_processed ON price_alerts(processed_at) WHERE processed_at IS NOT NULL;
CREATE INDEX idx_price_alerts_profit ON price_alerts(profit_potential);

CREATE INDEX idx_keepa_data_updated_at ON keepa_data(updated_at);

CREATE INDEX idx_scraping_sessions_status ON scraping_sessions(status);
CREATE INDEX idx_scraping_sessions_started_at ON scraping_sessions(started_at);

-- Full-text search indexes
CREATE INDEX idx_products_title_search ON products USING gin(to_tsvector('english', title));
CREATE INDEX idx_asins_title_search ON asins USING gin(to_tsvector('english', title));

-- Constraints and checks
ALTER TABLE products ADD CONSTRAINT chk_products_price_positive CHECK (price > 0);
ALTER TABLE price_alerts ADD CONSTRAINT chk_alerts_confidence_valid CHECK (confidence_score >= 0 AND confidence_score <= 1);
ALTER TABLE price_alerts ADD CONSTRAINT chk_alerts_discount_valid CHECK (discount_percentage >= 0);
ALTER TABLE product_asin_matches ADD CONSTRAINT chk_matches_confidence_valid CHECK (confidence_score >= 0 AND confidence_score <= 1);

-- Update trigger for products
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_settings_updated_at BEFORE UPDATE ON system_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); 