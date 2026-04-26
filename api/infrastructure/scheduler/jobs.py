from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from datetime import date, timedelta
import logging

from infrastructure.config import settings
from adapters.outbound.persistence.trade_repository import TradeRepository
from adapters.outbound.persistence.price_repository import PriceHistoryRepository
from adapters.outbound.market_data.yfinance_adapter import YFinanceAdapter
from infrastructure.db.session import engine

logger = logging.getLogger(__name__)

scheduler = None


def get_scheduler():
    global scheduler
    return scheduler


async def init_scheduler():
    global scheduler

    job_stores = {
        "default": SQLAlchemyJobStore(engine=engine, tablename="apscheduler_jobs")
    }

    scheduler = AsyncIOScheduler(jobstores=job_stores)

    if settings.SCHEDULER_ENABLED:
        scheduler.add_job(
            refresh_prices_job,
            "cron",
            hour=18,
            minute=0,
            id="refresh_prices",
            name="Refresh EOD prices for all holdings",
            replace_existing=True,
        )

        scheduler.add_job(
            refresh_fx_rates_job,
            "cron",
            hour=18,
            minute=30,
            id="refresh_fx_rates",
            name="Refresh FX rates for all portfolio currencies",
            replace_existing=True,
        )

        scheduler.add_job(
            refresh_benchmarks_job,
            "cron",
            hour=18,
            minute=0,
            id="refresh_benchmarks",
            name="Refresh benchmark prices",
            replace_existing=True,
        )

        scheduler.start()
        logger.info("Scheduler initialized and started")


async def shutdown_scheduler():
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")


async def refresh_prices_job():
    logger.info("Starting price refresh job")
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from infrastructure.db.session import async_session

        async with async_session() as session:
            yfinance = YFinanceAdapter()

            trade_repo = TradeRepository(session)
            trades, _ = await trade_repo.list_by_portfolio(None, skip=0, limit=10000)

            tickers = set(t.ticker for t in trades)
            price_repo = PriceHistoryRepository(session)

            for ticker in tickers:
                try:
                    current_date = date.today()
                    price_data = await yfinance.get_current_price(ticker)

                    if price_data:
                        await price_repo.add(
                            asset_id=None,
                            date_val=current_date,
                            close=price_data[1],
                            currency=None,
                        )
                    logger.info(f"Updated price for {ticker}")
                except Exception as e:
                    logger.error(f"Error updating price for {ticker}: {e}")

            await session.commit()
        logger.info("Price refresh job completed")
    except Exception as e:
        logger.error(f"Price refresh job failed: {e}")


async def refresh_fx_rates_job():
    logger.info("Starting FX refresh job")
    try:
        from infrastructure.db.session import async_session
        from domain.value_objects.money import Currency

        async with async_session() as session:
            yfinance = YFinanceAdapter()
            fx_repo = FxRateRepository(session)

            currencies = [Currency.USD, Currency.GBP, Currency.EUR, Currency.JPY]
            base = Currency.USD

            for target in currencies:
                if target == base:
                    continue

                try:
                    rate = await yfinance.get_current_rate(base, target)
                    if rate:
                        await fx_repo.add(base, target, date.today(), rate)
                        logger.info(f"Updated FX rate {base}/{target}: {rate}")
                except Exception as e:
                    logger.error(f"Error updating FX rate {base}/{target}: {e}")

            await session.commit()
        logger.info("FX refresh job completed")
    except Exception as e:
        logger.error(f"FX refresh job failed: {e}")


async def refresh_benchmarks_job():
    logger.info("Starting benchmark refresh job")
    try:
        from infrastructure.db.session import async_session

        async with async_session() as session:
            yfinance = YFinanceAdapter()
            price_repo = PriceHistoryRepository(session)

            benchmarks = ["^GSPC", "IWDA.L", "^NDX"]

            for ticker in benchmarks:
                try:
                    current_date = date.today()
                    price_data = await yfinance.get_current_price(ticker)

                    if price_data:
                        await price_repo.add(
                            asset_id=None,
                            date_val=current_date,
                            close=price_data[1],
                            currency=None,
                        )
                    logger.info(f"Updated benchmark price for {ticker}")
                except Exception as e:
                    logger.error(f"Error updating benchmark {ticker}: {e}")

            await session.commit()
        logger.info("Benchmark refresh job completed")
    except Exception as e:
        logger.error(f"Benchmark refresh job failed: {e}")
