from server import app, LOGGER
import logging
import sys

logging.basicConfig(stream=sys.stdout,level=logging.INFO)
LOGGER.info("starting server")

