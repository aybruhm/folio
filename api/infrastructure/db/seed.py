import asyncio
import logging
import math
import random
from datetime import date, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import ProgrammingError

from infrastructure.db.models import (
    AssetModel,
    GoalModel,
    PortfolioModel,
    PriceHistoryModel,
    TradeModel,
    UserModel,
)
from infrastructure.db.session import async_session

_SEED_USER_ID = UUID("00000000-0000-0000-0000-000000000001")
_SEED_USER_EMAIL = "demo@example.com"

log = logging.getLogger(__name__)

_RNG_SEED = 42
_START = date(2024, 1, 2)
_END = date(2026, 4, 18)

_ASSETS = [
    dict(
        ticker="AAPL",
        name="Apple Inc.",
        asset_class="stock",
        exchange="NASDAQ",
        currency="USD",
        sector="Technology",
        industry="Consumer Electronics",
        country="US",
        base=185.2,
        drift=0.12,
        vol=0.22,
    ),
    dict(
        ticker="MSFT",
        name="Microsoft Corporation",
        asset_class="stock",
        exchange="NASDAQ",
        currency="USD",
        sector="Technology",
        industry="Software",
        country="US",
        base=374.0,
        drift=0.14,
        vol=0.20,
    ),
    dict(
        ticker="GOOGL",
        name="Alphabet Inc.",
        asset_class="stock",
        exchange="NASDAQ",
        currency="USD",
        sector="Technology",
        industry="Internet Services",
        country="US",
        base=140.5,
        drift=0.11,
        vol=0.21,
    ),
    dict(
        ticker="AMZN",
        name="Amazon.com Inc.",
        asset_class="stock",
        exchange="NASDAQ",
        currency="USD",
        sector="Consumer Cyclical",
        industry="E-Commerce",
        country="US",
        base=180.0,
        drift=0.13,
        vol=0.24,
    ),
    dict(
        ticker="VOO",
        name="Vanguard S&P 500 ETF",
        asset_class="etf",
        exchange="NYSE",
        currency="USD",
        sector=None,
        industry=None,
        country="US",
        base=449.8,
        drift=0.10,
        vol=0.16,
    ),
    dict(
        ticker="BND",
        name="Vanguard Total Bond Market ETF",
        asset_class="etf",
        exchange="NYSE",
        currency="USD",
        sector=None,
        industry=None,
        country="US",
        base=73.5,
        drift=0.04,
        vol=0.05,
    ),
    dict(
        ticker="VEA",
        name="Vanguard FTSE Developed Markets ETF",
        asset_class="etf",
        exchange="NYSE",
        currency="USD",
        sector=None,
        industry=None,
        country="US",
        base=47.2,
        drift=0.09,
        vol=0.17,
    ),
    dict(
        ticker="BTC-USD",
        name="Bitcoin",
        asset_class="crypto",
        exchange="Crypto",
        currency="USD",
        sector=None,
        industry=None,
        country=None,
        base=43000.0,
        drift=0.60,
        vol=0.65,
    ),
]

_CASH_ASSETS = [
    dict(
        ticker="HYSA",
        name="High-Yield Savings Account",
        asset_class="cash",
        exchange=None,
        currency="USD",
        sector=None,
        industry=None,
        country="US",
    ),
]


# ---------------------------------------------------------------------------
# Price generation
# ---------------------------------------------------------------------------


def _weekdays(start: date, end: date) -> list[date]:
    days, d = [], start
    while d <= end:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def _gbm_prices(
    base: float, drift: float, vol: float, days: list[date], rng: random.Random
) -> dict[date, int]:
    """Geometric Brownian Motion discretised at daily frequency. Returns price ×100 as int."""
    dt = 1 / 252
    price = base
    result: dict[date, int] = {}
    for d in days:
        result[d] = round(price * 100)
        price *= math.exp(
            (drift - 0.5 * vol**2) * dt + vol * math.sqrt(dt) * rng.gauss(0, 1)
        )
    return result


def _price_on(prices: dict[date, int], d: date) -> int:
    """Last available close price (×100) on or before date d."""
    while d >= _START:
        if d in prices:
            return prices[d]
        d -= timedelta(days=1)
    return list(prices.values())[0]


# ---------------------------------------------------------------------------
# Trade schedule
# ---------------------------------------------------------------------------


def _build_trades(
    portfolio_id,
    asset_map: dict[str, UUID],
    price_map: dict[str, dict[date, int]],
) -> list[dict]:

    trades: list[dict] = []

    def _t(ticker, ttype, d: date, qty, fee_dollars: float = 4.95):
        price = _price_on(price_map[ticker], d)  # already ×100
        trades.append(
            dict(
                id=uuid4(),
                portfolio_id=portfolio_id,
                asset_id=asset_map[ticker],
                ticker=ticker,
                trade_type=ttype,
                trade_date=datetime(d.year, d.month, d.day, 9, 30),
                quantity=round(qty * 10000),
                price=price,
                trade_currency="USD",
                fees=round(fee_dollars * 100),
                source="manual",
            )
        )

    def buy(ticker, d, qty):
        _t(ticker, "buy", d, qty)

    def sell(ticker, d, qty):
        _t(ticker, "sell", d, qty)

    def div(ticker, d, qty, amt):
        _t(ticker, "dividend", d, qty, fee_dollars=amt)

    def deposit(ticker, d, amount_dollars):
        # Cash: quantity = dollar amount (each "share" = $1.00)
        trades.append(
            dict(
                id=uuid4(),
                portfolio_id=portfolio_id,
                asset_id=asset_map[ticker],
                ticker=ticker,
                trade_type="buy",
                trade_date=datetime(d.year, d.month, d.day, 9, 30),
                quantity=round(amount_dollars * 10000),
                price=100,  # $1.00 × 100
                trade_currency="USD",
                fees=0,
                source="manual",
            )
        )

    # ── 2024 Q1 — initial positions ──────────────────────────────────────
    buy("VOO", date(2024, 1, 5), 10)
    buy("BND", date(2024, 1, 5), 30)
    buy("AAPL", date(2024, 1, 10), 15)
    buy("MSFT", date(2024, 1, 10), 8)
    buy("VEA", date(2024, 1, 15), 25)
    buy("GOOGL", date(2024, 2, 1), 20)
    buy("AMZN", date(2024, 2, 1), 10)

    # ── 2024 Q2 — DCA ────────────────────────────────────────────────────
    buy("VOO", date(2024, 4, 3), 5)
    buy("AAPL", date(2024, 4, 10), 10)
    buy("MSFT", date(2024, 4, 15), 5)
    buy("BND", date(2024, 5, 1), 20)

    # ── 2024 Q3 ───────────────────────────────────────────────────────────
    buy("VOO", date(2024, 7, 1), 5)
    buy("GOOGL", date(2024, 7, 15), 15)
    buy("AMZN", date(2024, 8, 1), 8)
    sell("VEA", date(2024, 8, 20), 10)  # rebalance: trim intl

    # ── 2024 Q4 ───────────────────────────────────────────────────────────
    buy("AAPL", date(2024, 10, 1), 10)
    buy("VOO", date(2024, 10, 15), 5)
    buy("MSFT", date(2024, 11, 1), 5)
    div("VOO", date(2024, 12, 20), 20, 1.82)
    div("BND", date(2024, 12, 20), 50, 0.24)

    # ── 2025 Q1 ───────────────────────────────────────────────────────────
    buy("VOO", date(2025, 1, 6), 5)
    buy("AAPL", date(2025, 1, 15), 8)
    buy("AMZN", date(2025, 2, 3), 6)
    buy("GOOGL", date(2025, 3, 3), 10)

    # ── 2025 Q2 ───────────────────────────────────────────────────────────
    buy("VOO", date(2025, 4, 1), 5)
    buy("MSFT", date(2025, 4, 10), 4)
    buy("BND", date(2025, 5, 1), 15)
    div("VOO", date(2025, 6, 20), 35, 1.90)

    # ── 2025 Q3 ───────────────────────────────────────────────────────────
    buy("VOO", date(2025, 7, 1), 5)
    buy("AAPL", date(2025, 7, 15), 8)
    sell("BND", date(2025, 8, 15), 15)  # rotate bonds → equities

    # ── 2025 Q4 ───────────────────────────────────────────────────────────
    buy("VOO", date(2025, 10, 1), 5)
    buy("AMZN", date(2025, 10, 15), 5)
    buy("MSFT", date(2025, 11, 3), 4)
    div("BND", date(2025, 12, 19), 50, 0.25)
    div("VOO", date(2025, 12, 19), 40, 1.95)

    # ── 2026 Q1 ───────────────────────────────────────────────────────────
    buy("VOO", date(2026, 1, 6), 5)
    buy("AAPL", date(2026, 1, 15), 5)
    buy("GOOGL", date(2026, 2, 3), 8)

    # ── BTC-USD — crypto position ─────────────────────────────────────────
    buy("BTC-USD", date(2024, 1, 12), 0.10)  # initial entry ~$43k
    buy("BTC-USD", date(2024, 5, 10), 0.05)  # add after halving
    buy("BTC-USD", date(2024, 11, 12), 0.10)  # post-election rally
    buy("BTC-USD", date(2025, 1, 20), 0.05)  # DCA
    sell("BTC-USD", date(2025, 5, 15), 0.05)  # partial profit-taking
    buy("BTC-USD", date(2026, 1, 15), 0.05)  # buy the dip

    # ── HYSA — cash savings ───────────────────────────────────────────────
    deposit("HYSA", date(2024, 1, 3), 5000)  # initial deposit
    deposit("HYSA", date(2024, 4, 1), 2000)
    deposit("HYSA", date(2024, 7, 1), 2000)
    deposit("HYSA", date(2024, 10, 1), 2000)
    deposit("HYSA", date(2025, 1, 6), 2000)
    deposit("HYSA", date(2025, 4, 1), 2000)
    deposit("HYSA", date(2025, 7, 1), 2000)
    deposit("HYSA", date(2025, 10, 1), 2000)
    deposit("HYSA", date(2026, 1, 6), 2000)

    return trades


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def seed() -> None:
    try:
        async with async_session() as session:
            existing = await session.execute(
                select(PortfolioModel).where(PortfolioModel.name == "Demo Portfolio")
            )
            if existing.scalar_one_or_none():
                log.info("Demo data already present — skipping seed.")
                return

            log.info("Seeding demo data…")

            # Ensure seed user exists (may have been pre-created by a migration
            # with a placeholder password and is_active=False).  Upsert handles
            # both create and overwrite in a single statement.
            import bcrypt
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            hashed = bcrypt.hashpw(b"demo1234", bcrypt.gensalt()).decode("utf-8")
            stmt = (
                pg_insert(UserModel)
                .values(
                    id=_SEED_USER_ID,
                    email=_SEED_USER_EMAIL,
                    hashed_password=hashed,
                    is_active=True,
                )
                .on_conflict_do_update(
                    index_elements=["id"],
                    set_=dict(
                        email=_SEED_USER_EMAIL,
                        hashed_password=hashed,
                        is_active=True,
                    ),
                )
            )
            await session.execute(stmt)
            await session.flush()

            # Portfolio
            portfolio_id = uuid4()
            session.add(
                PortfolioModel(
                    id=portfolio_id,
                    user_id=_SEED_USER_ID,
                    name="Demo Portfolio",
                    description="A sample portfolio — replace with your own trades to get started.",
                    base_currency="USD",
                )
            )

            # Assets + price history
            rng = random.Random(_RNG_SEED)
            weekdays = _weekdays(_START, _END)
            price_map: dict[str, dict[date, int]] = {}
            asset_map: dict[str, UUID] = {}

            for a in _ASSETS:
                asset_id = uuid4()
                session.add(
                    AssetModel(
                        id=asset_id,
                        ticker=a["ticker"],
                        name=a["name"],
                        asset_class=a["asset_class"],
                        exchange=a["exchange"],
                        currency=a["currency"],
                        sector=a["sector"],
                        industry=a["industry"],
                        country=a["country"],
                    )
                )
                asset_map[a["ticker"]] = asset_id

                prices = _gbm_prices(a["base"], a["drift"], a["vol"], weekdays, rng)
                price_map[a["ticker"]] = prices

                for d, close in prices.items():
                    session.add(
                        PriceHistoryModel(
                            id=uuid4(),
                            asset_id=asset_id,
                            date=d,
                            close=close,
                            currency=a["currency"],
                        )
                    )
                log.info(f"  {a['ticker']}  {len(prices)} price records")

            # Cash assets (no price history — market value = cost basis)
            for c in _CASH_ASSETS:
                asset_id = uuid4()
                session.add(
                    AssetModel(
                        id=asset_id,
                        ticker=c["ticker"],
                        name=c["name"],
                        asset_class=c["asset_class"],
                        exchange=c.get("exchange"),
                        currency=c["currency"],
                        sector=c.get("sector"),
                        industry=c.get("industry"),
                        country=c.get("country"),
                    )
                )
                asset_map[c["ticker"]] = asset_id
                log.info(f"  {c['ticker']}  cash asset")

            # Trades
            trade_rows = _build_trades(portfolio_id, asset_map, price_map)
            for t in trade_rows:
                session.add(TradeModel(**t))
            log.info(f"  {len(trade_rows)} trades")

            # FIRE goal
            session.add(
                GoalModel(
                    id=uuid4(),
                    user_id=_SEED_USER_ID,
                    name="FIRE by 2040",
                    target_net_worth=200000000,  # $2,000,000 × 100
                    target_net_worth_currency="USD",
                    target_date=date(2040, 1, 1),
                    monthly_savings=300000,  # $3,000 × 100
                    monthly_savings_currency="USD",
                    expected_annual_return=7,  # 7% × 100 = 7 (÷100 → 0.07)
                )
            )

            await session.commit()
            log.info("Demo data seeded successfully.")

    except ProgrammingError:
        # Tables don't exist yet (pre-migration). Skip silently.
        log.warning("Seed skipped: database tables not ready yet.")
    except Exception as exc:
        log.warning(f"Seed skipped: {exc}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    asyncio.run(seed())
