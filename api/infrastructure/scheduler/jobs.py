import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from adapters.outbound.market_data.yfinance_adapter import YFinanceAdapter
from adapters.outbound.persistence.trade_repository import TradeRepository
from infrastructure.config import settings

logging.basicConfig()
logging.getLogger("apscheduler").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

scheduler = None


def get_scheduler():
    global scheduler
    return scheduler


async def init_scheduler():
    global scheduler

    scheduler = AsyncIOScheduler()

    if settings.SCHEDULER_ENABLED:
        scheduler.add_job(
            warm_cache_prices_job,
            "interval",
            minutes=45,
            id="warm_cache_prices",
            name="Warm Valkey cache with current prices",
            replace_existing=True,
        )

        scheduler.add_job(
            warm_cache_fx_job,
            "interval",
            minutes=45,
            id="warm_cache_fx",
            name="Warm Valkey cache with current FX rates",
            replace_existing=True,
        )

        scheduler.start()


async def shutdown_scheduler():
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)


async def warm_cache_prices_job():
    """
    Refresh current prices in the Valkey cache for all portfolio tickers.

    Calls YFinanceAdapter.get_current_price() which reads-through / writes-through
    the Valkey cache automatically.  This job just ensures the cache stays warm
    so that holdings reads are fast.
    """

    logger.info("Starting cache warm (prices)")
    try:
        from infrastructure.db.session import async_session

        async with async_session() as session:
            yfinance = YFinanceAdapter()
            trade_repo = TradeRepository(session)

            tickers = await trade_repo.list_all_tickers()

            for ticker in sorted(tickers):
                try:
                    await yfinance.get_current_price(ticker)
                    logger.debug(f"Cache warmed for {ticker}")
                except Exception as exc:
                    logger.warning(f"Cache warm failed for {ticker}: {exc}")

        logger.info(f"Cache warm (prices) completed — {len(tickers)} tickers")
    except Exception as e:
        logger.error(f"Cache warm (prices) failed: {e}")


async def warm_cache_fx_job():
    """
    Refresh current FX rates in the Valkey cache for all active currencies.

    Calls YFinanceAdapter.get_current_rate() which reads-through / writes-through
    the Valkey cache automatically.
    """

    logger.info("Starting cache warm (FX)")
    try:
        from adapters.outbound.persistence.portfolio_repository import (
            PortfolioRepository,
        )
        from domain.value_objects.money import Currency
        from infrastructure.db.session import async_session

        async with async_session() as session:
            yfinance = YFinanceAdapter()
            portfolio_repo = PortfolioRepository(session)

            portfolios = await portfolio_repo.list_all()
            base_currencies = {
                p.base_currency.value for p in portfolios if p.base_currency
            }

            to_currencies = set(base_currencies)
            from_currency = Currency.USD

            for target in sorted(to_currencies):
                if target == from_currency.value:
                    continue

                try:
                    await yfinance.get_current_rate(from_currency, Currency(target))
                    logger.debug(f"Cache warmed for FX {from_currency.value}/{target}")
                except Exception as exc:
                    logger.warning(
                        f"Cache warm FX {from_currency.value}/{target} failed: {exc}"
                    )

        logger.info(f"Cache warm (FX) completed — {len(to_currencies)} pairs")
    except Exception as e:
        logger.error(f"Cache warm (FX) failed: {e}")
