BEGIN;

-- 1. 合法的 Non-Rest record
INSERT INTO agri_prices (
    trade_date,
    category_code,
    crop_code,
    crop_name,
    market_code,
    market_name,
    upper_price,
    middle_price,
    lower_price,
    avg_price,
    volume
)
VALUES (
    '2099-01-01',
    NULL,
    'TEST001',
    '測試作物',
    'M001',
    '測試市場',
    10,
    9,
    8,
    9,
    100
);

-- 應成功
SELECT *
FROM agri_prices
WHERE trade_date = '2099-01-01';


-- 2. 測試 Non-Rest Business Key 重複
DO $$
BEGIN
    INSERT INTO agri_prices (
        trade_date,
        category_code,
        crop_code,
        crop_name,
        market_code,
        market_name,
        upper_price,
        middle_price,
        lower_price,
        avg_price,
        volume
    )
    VALUES (
        '2099-01-01',
        'N99',
        'TEST001',
        '另一個名稱',
        'M001',
        '另一市場名稱',
        20,
        18,
        16,
        18,
        200
    );

    RAISE EXCEPTION 'Non-Rest duplicate test failed: duplicate was accepted';

EXCEPTION
    WHEN unique_violation THEN
        RAISE NOTICE 'PASS: Non-Rest duplicate rejected';
END $$;


-- 3. 合法的 Rest record
INSERT INTO agri_prices (
    trade_date,
    category_code,
    crop_code,
    crop_name,
    market_code,
    market_name,
    upper_price,
    middle_price,
    lower_price,
    avg_price,
    volume
)
VALUES (
    '2099-01-01',
    'N01',
    'rest',
    '休市',
    'M002',
    '測試市場',
    0,
    0,
    0,
    0,
    0
);


-- 4. 測試 Rest Business Key 重複
DO $$
BEGIN
    INSERT INTO agri_prices (
        trade_date,
        category_code,
        crop_code,
        crop_name,
        market_code,
        market_name,
        upper_price,
        middle_price,
        lower_price,
        avg_price,
        volume
    )
    VALUES (
        '2099-01-01',
        'N01',
        'rest',
        '休市',
        'M002',
        '另一市場名稱',
        0,
        0,
        0,
        0,
        0
    );

    RAISE EXCEPTION 'Rest duplicate test failed: duplicate was accepted';

EXCEPTION
    WHEN unique_violation THEN
        RAISE NOTICE 'PASS: Rest duplicate rejected';
END $$;


-- 5. Rest 的 category_code 不可為 NULL
DO $$
BEGIN
    INSERT INTO agri_prices (
        trade_date,
        category_code,
        crop_code,
        crop_name,
        market_code,
        market_name,
        upper_price,
        middle_price,
        lower_price,
        avg_price,
        volume
    )
    VALUES (
        '2099-01-01',
        NULL,
        'rest',
        '休市',
        'M003',
        '測試市場',
        0,
        0,
        0,
        0,
        0
    );

    RAISE EXCEPTION 'Rest NULL category test failed: invalid row was accepted';

EXCEPTION
    WHEN check_violation THEN
        RAISE NOTICE 'PASS: Rest NULL category_code rejected';
END $$;


-- 6. 數值不可小於 0
DO $$
BEGIN
    INSERT INTO agri_prices (
        trade_date,
        category_code,
        crop_code,
        crop_name,
        market_code,
        market_name,
        upper_price,
        middle_price,
        lower_price,
        avg_price,
        volume
    )
    VALUES (
        '2099-01-01',
        NULL,
        'TEST002',
        '測試作物',
        'M004',
        '測試市場',
        -1,
        9,
        8,
        9,
        100
    );

    RAISE EXCEPTION 'Negative value test failed: invalid row was accepted';

EXCEPTION
    WHEN check_violation THEN
        RAISE NOTICE 'PASS: Negative numeric value rejected';
END $$;


ROLLBACK;

SELECT *
FROM agri_prices
WHERE trade_date = '2099-01-01';