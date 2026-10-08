"""Standard pagination classes for the API."""

from rest_framework.pagination import PageNumberPagination


class StandardPageNumberPagination(PageNumberPagination):
    """Standard page-number pagination with configurable page size."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
