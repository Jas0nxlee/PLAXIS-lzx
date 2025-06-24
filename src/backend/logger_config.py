import logging
import logging.handlers
import os

LOG_FILENAME = "plaxis_automation.log"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5

def setup_logging(log_level=logging.INFO, log_to_console=True, log_to_file=True):
    """
    Configures logging for the application.
    """
    logger = logging.getLogger() # Get root logger
    logger.setLevel(log_level) # Set root logger level

    # Prevent adding multiple handlers if called multiple times (e.g. in tests or reloads)
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s"
    )

    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if log_to_file:
        # Ensure log directory exists (optional, if logs are in a subfolder)
        # log_dir = "logs"
        # os.makedirs(log_dir, exist_ok=True)
        # log_file_path = os.path.join(log_dir, LOG_FILENAME)

        # For simplicity, log file in the current working directory or where the main script is run from
        log_file_path = LOG_FILENAME

        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.info("Logging setup complete.")

if __name__ == "__main__":
    setup_logging(log_level=logging.DEBUG)
    logging.debug("This is a debug message.")
    logging.info("This is an info message.")
    logging.warning("This is a warning message.")
    logging.error("This is an error message.")
    logging.critical("This is a critical message.")

    # Example from another module
    module_logger = logging.getLogger("MyModule")
    module_logger.info("Message from MyModule.")
