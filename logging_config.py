import logging
from config import *

def setup_logging():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        handlers=[
            logging.FileHandler('forwarder.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)
