-- Migration to update products table schema
-- Adds original_price, discount_percentage, asin fields
-- Removes images column to optimize performance

-- Add new columns
ALTER TABLE products 
ADD COLUMN original_price DECIMAL(10,2),
ADD COLUMN discount_percentage REAL,
ADD COLUMN asin VARCHAR(10);

-- Drop images column (no longer needed for arbitrage)
ALTER TABLE products DROP COLUMN IF EXISTS images;

-- Drop specifications column (no longer needed for arbitrage)
ALTER TABLE products DROP COLUMN IF EXISTS specifications;

-- Add constraints
ALTER TABLE products ADD CONSTRAINT chk_products_original_price_positive 
    CHECK (original_price IS NULL OR original_price > 0);

ALTER TABLE products ADD CONSTRAINT chk_products_discount_valid 
    CHECK (discount_percentage IS NULL OR (discount_percentage >= 0 AND discount_percentage <= 100));

ALTER TABLE products ADD CONSTRAINT chk_products_asin_format 
    CHECK (asin IS NULL OR LENGTH(asin) = 10);

-- Add indexes for new fields
CREATE INDEX idx_products_original_price ON products(original_price) WHERE original_price IS NOT NULL;
CREATE INDEX idx_products_discount_percentage ON products(discount_percentage) WHERE discount_percentage IS NOT NULL;
CREATE INDEX idx_products_asin ON products(asin) WHERE asin IS NOT NULL;

-- Add constraint to ensure original_price >= price when both exist
ALTER TABLE products ADD CONSTRAINT chk_products_discount_logic 
    CHECK (original_price IS NULL OR price IS NULL OR original_price >= price);

-- Update the updated_at trigger to handle the new columns
-- (The existing trigger already works for all columns) 