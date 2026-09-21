CREATE TABLE agri_prices (
    trade_date DATE NOT NULL,

    category_code TEXT,
    crop_code TEXT NOT NULL,
    crop_name TEXT,

    market_code TEXT NOT NULL,
    market_name TEXT NOT NULL,

    upper_price DOUBLE PRECISION NOT NULL CHECK (upper_price >= 0),
    middle_price DOUBLE PRECISION NOT NULL CHECK (middle_price >= 0),
    lower_price DOUBLE PRECISION NOT NULL CHECK (lower_price >= 0),
    avg_price DOUBLE PRECISION NOT NULL CHECK (avg_price >= 0),
    volume DOUBLE PRECISION NOT NULL CHECK (volume >= 0),

    CONSTRAINT chk_rest_category_code
        CHECK (
            crop_code <> 'rest'
            OR category_code IS NOT NULL
        )
);


CREATE UNIQUE INDEX uq_agri_prices_non_rest
ON agri_prices (
    trade_date,
    crop_code,
    market_code
)
WHERE crop_code <> 'rest';


CREATE UNIQUE INDEX uq_agri_prices_rest
ON agri_prices (
    trade_date,
    category_code,
    market_code
)
WHERE crop_code = 'rest';
