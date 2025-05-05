import logging
import sys

def setup_session_logger(filename):
    """Configure logging for a new session"""
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # File handler for saving logs to file
    log_handler = logging.FileHandler(filename, mode='a')
    log_handler.setFormatter(log_formatter)

    # Get root logger
    root_logger = logging.getLogger()
    
    # Remove existing handlers to avoid duplicate logs if restarting
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
        h.close()  # Close the handler properly
    
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(log_handler)

    # Also log to console for debugging
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

    return log_handler