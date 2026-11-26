"""Domain error types (pure)."""


class UnsupportedFilter(Exception):
    """Raised when a search filter is not supported by the wired index (D85, §1.3.1)."""