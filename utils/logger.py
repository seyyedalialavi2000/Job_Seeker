import logging


def setup_logging():
    """
    Configures the logging for the entire application.
    Should be called once at application startup.
    """
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Gets a logger instance with the specified name.
    
    Args:
        name: The name for the logger (typically __name__)
    
    Returns:
        A configured logger instance.
    """
    return logging.getLogger(name)
