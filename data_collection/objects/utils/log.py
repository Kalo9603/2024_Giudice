""" Modulo che configura il log che viene utilizzato in fase di elaborazione. """

import logging


def run():

    logging.getLogger("httpx").setLevel(logging.CRITICAL)
    logging.getLogger("pylast").setLevel(logging.CRITICAL)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('log.log', encoding='utf-8'),
            logging.StreamHandler() 
        ]
    )