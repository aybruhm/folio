import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from adapters.outbound.market_data.ngnmarket_adapter import NgnMarketAdapter
from adapters.outbound.market_data.tiingo_adapter import TiingoAdapter
from adapters.outbound.market_data.tradingview_adapter import TradingviewAdapter
from adapters.outbound.market_data.yfinance_adapter import YFinanceAdapter
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

    scheduler = AsyncIOScheduler(timezone="Europe/London")

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
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")


async def warm_cache_prices_job():
    """
    Refresh current prices in the Valkey cache for all portfolio assets,
    routing each asset to its stored market_data_provider.
    """

    logger.info("Starting cache warm (prices)")
    try:
        from adapters.outbound.persistence.asset_repository import AssetRepository
        from domain.value_objects.money import AssetClass
        from infrastructure.db.session import async_session

        async with async_session() as session:
            yfinance = YFinanceAdapter()
            tiingo = TiingoAdapter()
            tradingview = TradingviewAdapter()
            ngnmarket = NgnMarketAdapter()
            asset_repo = AssetRepository(session)

            assets = await asset_repo.list_all()
            warmed = 0

            for asset in assets:
                if asset.asset_class == AssetClass.CASH:
                    continue

                ticker = asset.ticker
                provider = (asset.market_data_provider or "yfinance").strip().lower()
                try:
                    if provider == "tiingo":
                        await tiingo.get_current_price(ticker)
                    elif provider == "tradingview":
                        await tradingview.get_current_price(ticker)
                    elif provider == "ngnmarket":
                        await ngnmarket.get_index_chart(ticker)
                    else:
                        await yfinance.get_current_price(ticker)

                    warmed += 1
                    logger.debug(f"Cache warmed for {ticker} via {provider}")
                except Exception as exc:
                    logger.warning(f"Cache warm failed for {ticker} ({provider}): {exc}")

        logger.info(f"Cache warm (prices) completed — {warmed} assets")
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
