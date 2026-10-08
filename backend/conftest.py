"""Root conftest with shared test fixtures."""

import pytest
from django.test import RequestFactory


@pytest.fixture
def request_factory():
    """Provide a Django RequestFactory instance."""
    return RequestFactory()


@pytest.fixture
def api_client():
    """Provide a DRF APIClient instance with clean cache."""
    from django.core.cache import cache
    from rest_framework.test import APIClient

    cache.clear()
    return APIClient()
