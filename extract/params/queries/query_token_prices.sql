With prices as (
  SELECT
    Date_trunc('day', "HOUR") as "DAY",
    TOKEN_ADDRESS,
    SYMBOL,
    DECIMALS,
    PRICE
  FROM
    ethereum.price.ez_prices_hourly
  WHERE
    "BLOCKCHAIN" = 'ethereum'
    AND TOKEN_ADDRESS in {TOKEN_ADDRESSES}
    AND Date_trunc('day', "HOUR") >= DATEADD(Year, -5, '2025-01-01')
),
Prices_Agg as (
  SELECT
    "DAY",
    TOKEN_ADDRESS,
    SYMBOL,
    DECIMALS,
    AVG(PRICE) as avg_daily_price
  from
    prices
  group by
    "DAY",
    TOKEN_ADDRESS,
    SYMBOL,
    DECIMALS
)
SELECT
  "DAY",
  TOKEN_ADDRESS,
  SYMBOL,
  DECIMALS,
  avg_daily_price,

from
  Prices_Agg