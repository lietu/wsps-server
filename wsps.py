import logging
from logging import NullHandler
from time import sleep
from wspsserver import Server
import settings


def _get_logger():
    # Disable logging from Tornado
    tornado = logging.getLogger("tornado")
    tornado.addHandler(NullHandler())
    tornado.propagate = False

    logger = logging.getLogger("wsps")

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    ch.setFormatter(
        logging.Formatter('%(asctime)s [%(levelname)8s] %(message)s')
    )

    logger.addHandler(ch)
    logger.setLevel(logging.DEBUG)

    return logger


if __name__ == "__main__":
    logger = _get_logger()


    server = Server(settings, logger)

    # TODO: Figure out why the hell I need a thread + this to stop IOLoop
    try:
        server.start()
        while True:
            sleep(0.05)
    except:
        server.stop()
