from infrastructure.config.env import _asyncpg_url


def test_asyncpg_url_converts_postgres_scheme():
    assert (
        _asyncpg_url("postgres://user:pass@localhost:5432/db")
        == "postgresql+asyncpg://user:pass@localhost:5432/db"
    )


def test_asyncpg_url_converts_postgresql_scheme():
    assert (
        _asyncpg_url("postgresql://user:pass@localhost:5432/db")
        == "postgresql+asyncpg://user:pass@localhost:5432/db"
    )


def test_asyncpg_url_keeps_non_postgres_schemes_unchanged():
    url = "sqlite:///tmp/test.db"
    assert _asyncpg_url(url) == url
