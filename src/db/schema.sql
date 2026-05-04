-- Banners: the retail chains being tracked
CREATE TABLE banners 
(
    banner_id SERIAL PRIMARY KEY,
    banner_name TEXT NOT NULL,
    parent_company TEXT,
    province TEXT NOT NULL DEFAULT 'BC'
);

-- Products: ~50 staple items to track individually
CREATE TABLE products 
(
    product_id SERIAL PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    category TEXT NOT NULL,
    size_value NUMERIC,
    size_unit TEXT
);

-- Product aliases: maps canonical products to each banner's version
CREATE TABLE product_aliases 
(
    alias_id SERIAL PRIMARY KEY,
    product_id INT NOT NULL REFERENCES products(product_id),
    banner_id INT NOT NULL REFERENCES banners(banner_id),
    banner_sku TEXT,
    banner_product_name TEXT NOT NULL,
    scrape_url TEXT,
    UNIQUE(product_id, banner_id)
);

-- Price observations: the fact table, append-only
CREATE TABLE price_observations 
(
    observation_id BIGSERIAL PRIMARY KEY,
    product_id INT NOT NULL REFERENCES products(product_id),
    banner_id INT NOT NULL REFERENCES banners(banner_id),
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    regular_price NUMERIC(10,2) NOT NULL,
    sale_price NUMERIC(10,2),
    is_on_sale BOOLEAN NOT NULL DEFAULT FALSE,
    unit_price NUMERIC(10,4),
    unit_type TEXT,
    raw_payload JSONB
);

-- Index for time-series queries
CREATE INDEX idx_observations_product_banner_time
    ON price_observations(product_id, banner_id, observed_at DESC);

-- Seed banners
INSERT INTO banners (banner_name, parent_company) VALUES
    ('Save-On-Foods', 'Pattison'),
    ('Real Canadian Superstore', 'Loblaw'),
    ('Walmart Canada', 'Walmart');