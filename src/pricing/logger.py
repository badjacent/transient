import logging

def setup_logger():
    if logging.getLogger().handlers:
        return
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
