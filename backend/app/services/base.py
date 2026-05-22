"""
Abstract base class for all services.
Every concrete service (chat, ingest, user, …) inherits from this
so we have a consistent place to inject shared dependencies later
(e.g. Supabase client, LangChain components).
"""
from abc import ABC


class BaseService(ABC):
    """Inherit and override to build a domain service."""
    pass
