"""Safe inert entry point used to document and validate plugin packaging."""


def register_noop(sdk) -> None:
    """Register nothing; loading still requires explicit project allowlisting."""
