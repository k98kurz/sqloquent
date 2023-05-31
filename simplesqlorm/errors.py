def vert(condition: bool, error_message: str = '') -> None:
    if not condition:
        raise ValueError(error_message)

def tert(condition: bool, error_message: str = '') -> None:
    if not condition:
        raise TypeError(error_message)
