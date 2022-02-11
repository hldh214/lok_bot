import threading
import time

import schedule

from lokbot.farmer import LokFarmer, TASK_CODE_SILVER_HAMMER, TASK_CODE_GOLD_HAMMER


def main(token, captcha_solver_config):
    farmer = LokFarmer(token, captcha_solver_config)

    schedule.every(120).to(200).minutes.do(farmer.alliance_helper)
    schedule.every(60).to(100).minutes.do(farmer.harvester)
    schedule.every(180).to(240).minutes.do(farmer.vip_chest_claim)
    schedule.every(120).to(240).minutes.do(farmer.use_resource_in_item_list)
    schedule.every(120).to(240).minutes.do(farmer.alliance_farmer)

    schedule.run_all()

    threading.Thread(target=farmer.sock_thread).start()

    threading.Thread(target=farmer.free_chest_farmer).start()

    threading.Thread(target=farmer.quest_monitor).start()

    threading.Thread(target=farmer.building_farmer, args=(TASK_CODE_SILVER_HAMMER,)).start()
    threading.Thread(target=farmer.building_farmer, args=(TASK_CODE_GOLD_HAMMER,)).start()

    threading.Thread(target=farmer.academy_farmer).start()

    while True:
        schedule.run_pending()
        time.sleep(1)
