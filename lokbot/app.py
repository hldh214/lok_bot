import threading
import time

import schedule

from lokbot.farmer import LokFarmer, TASK_CODE_SILVER_HAMMER, TASK_CODE_GOLD_HAMMER


def find_alliance(farmer: LokFarmer):
    while True:
        alliance = farmer.api.alliance_recommend().get('alliance')

        if alliance.get('numMembers') < alliance.get('maxMembers'):
            farmer.api.alliance_join(alliance.get('_id'))
            break

        time.sleep(60 * 5)


def main(token, captcha_solver_config):
    farmer = LokFarmer(token, captcha_solver_config)

    threading.Thread(target=farmer.sock_thread).start()

    schedule.every(120).to(240).minutes.do(farmer.alliance_helper)
    schedule.every(60).to(120).minutes.do(farmer.harvester)
    schedule.every(200).to(300).minutes.do(farmer.vip_chest_claim)
    schedule.every(120).to(240).minutes.do(farmer.use_resource_in_item_list)
    schedule.every(120).to(240).minutes.do(farmer.alliance_farmer)

    schedule.run_all()

    threading.Thread(target=farmer.free_chest_farmer_thread).start()

    threading.Thread(target=farmer.quest_monitor_thread).start()

    threading.Thread(target=farmer.building_farmer_thread, args=(TASK_CODE_SILVER_HAMMER,)).start()
    threading.Thread(target=farmer.building_farmer_thread, args=(TASK_CODE_GOLD_HAMMER,)).start()

    threading.Thread(target=farmer.academy_farmer_thread).start()

    while True:
        schedule.run_pending()
        time.sleep(1)
