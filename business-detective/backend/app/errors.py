class ApiError(Exception):
    """An error whose message is safe to show to the customer."""

    def __init__(self, status: int, message: str, **extra):
        self.status, self.message, self.extra = status, message, extra
