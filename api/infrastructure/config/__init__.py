from .env import get_environ_settings

settings = get_environ_settings()
__all__ = ["settings"]
