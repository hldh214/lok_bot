import json
import os.path
import threading
import time

import schedule

from lokbot.farmer import LokFarmer
from lokbot import project_root


def find_alliance(farmer: LokFarmer):
    while True:
        alliance = farmer.api.alliance_recommend().get('alliance')

        if alliance.get('numMembers') < alliance.get('maxMembers'):
            farmer.api.alliance_join(alliance.get('_id'))
            break

        time.sleep(60 * 5)


def load_config():
    os.chdir(project_root)

    if os.path.exists('config.json'):
        return json.load(open('config.json'))

    if os.path.exists('config.example.json'):
        return json.load(open('config.example.json'))

    return {}


def main(token, captcha_solver_config=None):
    if captcha_solver_config is None:
        captcha_solver_config = {}

    config = load_config()

    farmer = LokFarmer(token, captcha_solver_config)
    farmer.keepalive_request()
    # find_alliance(farmer)
    # exit()

    threading.Thread(target=farmer.sock_thread).start()
    # threading.Thread(target=farmer.socc_thread).start()

    for job in config.get('main').get('jobs'):
        if not job.get('enabled'):
            continue

        schedule.every(
            job.get('interval').get('start')
        ).to(
            job.get('interval').get('end')
        ).minutes.do(getattr(farmer, job.get('name')))

    schedule.run_all()

    schedule.every(15).to(30).minutes.do(farmer.keepalive_request)
    # schedule.every(1).to(3).minutes.do(farmer.socf_thread)

    for thread in config.get('main').get('threads'):
        if not thread.get('enabled'):
            continue

        threading.Thread(target=getattr(farmer, thread.get('name')), args=thread.get('args', [])).start()

    while True:
        schedule.run_pending()
        time.sleep(1)
