def vert(condition: bool, error_message: str = '') -> None:
    """If condition is true, raises a ValueError with the given message."""
    if not condition:
        raise ValueError(error_message)

def tert(condition: bool, error_message: str = '') -> None:
    """If condition is true, raises a TypeError with the given message."""
    if not condition:
        raise TypeError(error_message)
