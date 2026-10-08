"""Custom renderers for consistent API response format."""

from rest_framework.renderers import JSONRenderer


class StandardJSONRenderer(JSONRenderer):
    """Standard JSON renderer. Can be extended for envelope pattern."""

    pass
