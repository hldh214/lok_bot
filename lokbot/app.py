import asyncio
import functools
import threading
import time

import schedule

import lokbot.util
from lokbot import project_root, logger, config
from lokbot.async_farmer import AsyncLokFarmer
from lokbot.exceptions import NoAuthException
from lokbot.farmer import LokFarmer


def find_alliance(farmer: LokFarmer):
    while True:
        alliance = farmer.api.alliance_recommend().get('alliance')

        if alliance.get('numMembers') < alliance.get('maxMembers'):
            farmer.api.alliance_join(alliance.get('_id'))
            break

        time.sleep(60 * 5)


thread_map = {}


def run_threaded(name, job_func):
    if name in thread_map and thread_map[name].is_alive():
        return

    job_thread = threading.Thread(target=job_func, name=name, daemon=True)
    thread_map[name] = job_thread
    job_thread.start()


def async_main(token):
    async_farmer = AsyncLokFarmer(token)

    asyncio.run(async_farmer.parallel_buy_caravan())


def main(token, captcha_solver_config=None):
    # async_main(token)
    # exit()

    if captcha_solver_config is None:
        captcha_solver_config = {}

    _id = lokbot.util.decode_jwt(token).get('_id')
    token_file = project_root.joinpath(f'data/{_id}.token')
    if token_file.exists():
        token_from_file = token_file.read_text()
        logger.info(f'Using token: {token_from_file} from file: {token_file}')
        try:
            farmer = LokFarmer(token_from_file, captcha_solver_config)
        except NoAuthException:
            logger.info('Token is invalid, using token from command line')
            farmer = LokFarmer(token, captcha_solver_config)
    else:
        farmer = LokFarmer(token, captcha_solver_config)

    threading.Thread(target=farmer.sock_thread, daemon=True).start()
    threading.Thread(target=farmer.socc_thread, daemon=True).start()

    farmer.keepalive_request()

    for job in config.get('main').get('jobs'):
        if not job.get('enabled'):
            continue

        name = job.get('name')

        schedule.every(
            job.get('interval').get('start')
        ).to(
            job.get('interval').get('end')
        ).minutes.do(run_threaded, name, functools.partial(getattr(farmer, name), **job.get('kwargs', {})))

    schedule.run_all()

    # schedule.every(15).to(20).minutes.do(farmer.keepalive_request)

    for thread in config.get('main').get('threads'):
        if not thread.get('enabled'):
            continue

        threading.Thread(target=getattr(farmer, thread.get('name')), kwargs=thread.get('kwargs'), daemon=True).start()

    while True:
        schedule.run_pending()
        time.sleep(1)
