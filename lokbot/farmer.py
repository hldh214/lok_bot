import random
import threading
import time

import arrow
import socketio
import tenacity

from lokbot.client import LokBotApi
from lokbot import logger, builtin_logger
from lokbot.exceptions import OtherException
from lokbot.enum import *


class LokFarmer:
    def __init__(self, access_token, captcha_solver_config):
        self.access_token = access_token
        self.api = LokBotApi(access_token, captcha_solver_config, self._request_callback)
        self.kingdom_enter = self.api.kingdom_enter()
        # [food, lumber, stone, gold]
        self.resources = self.kingdom_enter.get('kingdom').get('resources')
        self.buff_item_use_lock = threading.RLock()
        self.has_additional_building_queue = self.kingdom_enter.get('kingdom').get('vip', {}).get('level') >= 5

    @staticmethod
    def calc_time_diff_in_seconds(expected_ended):
        time_diff = arrow.get(expected_ended) - arrow.utcnow()
        diff_in_seconds = time_diff.seconds

        if diff_in_seconds < 0:
            diff_in_seconds = 0

        return diff_in_seconds + random.randint(5, 10)

    def _is_building_upgradeable(self, building, buildings):
        if building.get('state') != BUILDING_STATE_NORMAL:
            return False

        # 暂时忽略联盟中心
        if building.get('code') == BUILDING_CODE_MAP['hall_of_alliance']:
            return False

        building_level = building.get('level')
        current_building_json = building_json.get(building.get('code'))

        if not current_building_json:
            return False

        next_level_building_json = current_building_json.get(str(building_level + 1))
        for requirement in next_level_building_json.get('requirements'):
            req_level = requirement.get('level')
            req_type = requirement.get('type')
            req_code = BUILDING_CODE_MAP.get(req_type)

            if not [b for b in buildings if b.get('code') == req_code and b.get('level') >= req_level]:
                return False

        for res_requirement in next_level_building_json.get('resources'):
            req_value = res_requirement.get('value')
            req_type = res_requirement.get('type')

            if self.resources[RESOURCE_IDX_MAP[req_type]] < req_value:
                return False

        return True

    def _is_researchable(self, academy_level, category_name, research_name, exist_researches, to_max_level=False):
        research_category = RESEARCH_CODE_MAP.get(category_name)
        research_code = research_category.get(research_name)

        exist_research = [each for each in exist_researches if each.get('code') == research_code]
        current_research_json = research_json.get(research_code)

        # already finished
        if exist_research and exist_research[0].get('level') >= int(current_research_json[-1].get('level')):
            return False

        # minimum required level only
        if not to_max_level and \
                exist_research and \
                exist_research[0].get('level') >= RESEARCH_MINIMUM_LEVEL_MAP.get(category_name).get(research_name, 0):
            return False

        next_level_research_json = current_research_json[0]
        if exist_research:
            next_level_research_json = current_research_json[exist_research[0].get('level')]

        for requirement in next_level_research_json.get('requirements'):
            req_level = int(requirement.get('level'))
            req_type = requirement.get('type')

            # 判断学院等级
            if req_type == 'academy' and req_level > academy_level:
                return False

            # 判断前置研究是否完成
            if req_type != 'academy' and not [each for each in exist_researches if
                                              each.get('code') == research_category.get(req_type)
                                              and each.get('level') >= req_level]:
                return False

        for res_requirement in next_level_research_json.get('resources'):
            req_value = int(res_requirement.get('value'))
            req_type = res_requirement.get('type')

            if self.resources[RESOURCE_IDX_MAP[req_type]] < req_value:
                return False

        return True

    def _update_building(self, building):
        buildings = self.kingdom_enter.get('kingdom', {}).get('buildings', [])

        self.kingdom_enter['kingdom']['buildings'] = [
                                                         b for b in buildings if
                                                         b.get('position') != building.get('position')
                                                     ] + [building]

    def _request_callback(self, json_response):
        resources = json_response.get('resources')

        if resources and len(resources) == 4:
            logger.info(f'resources updated: {resources}')
            self.resources = resources

    def _upgrade_building(self, building, buildings, task_code):
        if not self._is_building_upgradeable(building, buildings):
            return 'continue'

        try:
            if building.get('level') == 0:
                res = self.api.kingdom_building_build(building)
            else:
                res = self.api.kingdom_building_upgrade(building)
        except OtherException as error_code:
            if str(error_code) == 'full_task':
                logger.warning('building_farmer: full_task, quit')
                return 'break'

            logger.info(f'building upgrade failed: {building}')
            return 'continue'

        building['state'] = BUILDING_STATE_UPGRADING
        self._update_building(building)

        threading.Timer(
            self.calc_time_diff_in_seconds(res.get('newTask').get('expectedEnded')),
            self.building_farmer_thread,
            [task_code]
        ).start()

        return

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(4),
        wait=tenacity.wait_random_exponential(multiplier=1, max=60),
        reraise=True
    )
    def sock_thread(self):
        """
        websocket connection of the kingdom
        :return:
        """
        url = self.kingdom_enter.get('networks').get('kingdoms')[0]

        sio = socketio.Client(reconnection=False, logger=builtin_logger, engineio_logger=builtin_logger)

        @sio.on('/building/update')
        def on_building_update(data):
            logger.info(f'on_building_update: {data}')
            self._update_building(data)

        @sio.on('/resource/upgrade')
        def on_resource_update(data):
            logger.info(f'on_resource_update: {data}')
            self.resources[data.get('resourceIdx')] = data.get('value')

        @sio.on('/buff/list')
        def on_buff_list(data):
            logger.info(f'on_buff_list: {data}')

            self.has_additional_building_queue = len([
                item for item in data if item.get('param', {}).get('itemCode') == ITEM_CODE_GOLDEN_HAMMER
            ]) > 0

            item_list = self.api.item_list().get('items')

            for buff_type, item_code_list in USABLE_BOOST_CODE_MAP.items():
                already_activated = [item for item in data if item.get('param', {}).get('itemCode') in item_code_list]

                if already_activated:
                    continue

                item_in_inventory = [item for item in item_list if item.get('code') in item_code_list]

                if not item_in_inventory:
                    continue

                code = item_in_inventory[0].get('code')
                logger.info(f'activating buff: {buff_type}, code: {code}')
                if not self.buff_item_use_lock.acquire(blocking=False):
                    return
                self.api.item_use(code)

                if code == ITEM_CODE_GOLDEN_HAMMER:
                    self.has_additional_building_queue = True

                self.buff_item_use_lock.release()

        sio.connect(url, transports=["websocket"])
        sio.emit('/kingdom/enter', {'token': self.access_token})
        sio.wait()

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(4),
        wait=tenacity.wait_random_exponential(multiplier=1, max=60),
        reraise=True
    )
    def socf_thread(self):
        """
        websocket connection of the field
        :return:
        """
        url = self.kingdom_enter.get('networks').get('fields')[0]

        sio = socketio.Client(reconnection=False, logger=builtin_logger, engineio_logger=builtin_logger)

        sio.connect(url, transports=["websocket"])
        sio.emit('/field/enter', {'token': self.access_token})

        # todo: 遍历整个地图
        sio.wait()

    def alliance_helper(self):
        """
        帮助联盟
        :return:
        """
        try:
            self.api.alliance_help_all()
        except OtherException:
            pass

    def harvester(self):
        """
        收获资源
        :return:
        """
        buildings = self.kingdom_enter.get('kingdom', {}).get('buildings', [])

        random.shuffle(buildings)

        harvested_code = set()
        for building in buildings:
            code = building.get('code')
            position = building.get('position')

            if code not in HARVESTABLE_CODE:
                continue

            # 每个种类只需要收获一次, 就会自动收获整个种类下所有资源
            if code in harvested_code:
                continue

            harvested_code.add(code)

            self.api.kingdom_resource_harvest(position)

    def quest_monitor_thread(self):
        """
        任务监控
        :return:
        """
        quest_list = self.api.quest_list()

        # main quest(currently only one)
        [self.api.quest_claim(q) for q in quest_list.get('mainQuests') if q.get('status') == STATUS_FINISHED]

        # side quest(max 5)
        if len([self.api.quest_claim(q) for q in quest_list.get('sideQuests') if
                q.get('status') == STATUS_FINISHED]) >= 5:
            # 若五个均为已完成, 则翻页
            threading.Thread(target=self.quest_monitor_thread).start()
            return

        quest_list_daily = self.api.quest_list_daily().get('dailyQuest')

        # daily quest(max 5)
        if len([self.api.quest_claim_daily(q) for q in quest_list_daily.get('quests') if
                q.get('status') == STATUS_FINISHED]) >= 5:
            # 若五个均为已完成, 则翻页
            threading.Thread(target=self.quest_monitor_thread).start()
            return

        # daily quest reward
        [self.api.quest_claim_daily_level(q) for q in quest_list_daily.get('rewards') if
         q.get('status') == STATUS_FINISHED]

        logger.info('quest_monitor: done, sleep for 1h')
        threading.Timer(3600, self.quest_monitor_thread).start()
        return

    def building_farmer_thread(self, task_code=TASK_CODE_SILVER_HAMMER):
        """
        building farmer
        :param task_code:
        :return:
        """
        if task_code == TASK_CODE_GOLD_HAMMER and not self.has_additional_building_queue:
            return

        current_tasks = self.api.kingdom_task_all().get('kingdomTasks', [])

        worker_used = [t for t in current_tasks if t.get('code') == task_code]

        if worker_used:
            threading.Timer(
                self.calc_time_diff_in_seconds(worker_used[0].get('expectedEnded')),
                self.building_farmer_thread,
                [task_code]
            ).start()
            return

        buildings = self.kingdom_enter.get('kingdom', {}).get('buildings', [])
        kingdom_level = buildings[0].get('level')

        # First check if there is any empty position available for building
        for level_requirement, positions in BUILD_POSITION_UNLOCK_MAP.items():
            if kingdom_level < level_requirement:
                continue

            for position in positions:
                if position.get('position') in [building.get('position') for building in buildings]:
                    continue

                building = {
                    'code': position.get('code'),
                    'position': position.get('position'),
                    'level': 0,
                    'state': BUILDING_STATE_NORMAL,
                }

                res = self._upgrade_building(building, buildings, task_code)

                if res == 'continue':
                    continue
                if res == 'break':
                    break

                return

        # Then check if there is any upgradeable building
        for building in buildings:
            res = self._upgrade_building(building, buildings, task_code)

            if res == 'continue':
                continue
            if res == 'break':
                break

            return

        logger.info('building_farmer: no building to upgrade, sleep for 2h')
        threading.Timer(2 * 3600, self.building_farmer_thread, [task_code]).start()
        return

    def academy_farmer_thread(self, to_max_level=False):
        """
        research farmer
        :param to_max_level:
        :return:
        """
        current_tasks = self.api.kingdom_task_all().get('kingdomTasks', [])

        worker_used = [t for t in current_tasks if t.get('code') == TASK_CODE_ACADEMY]

        if worker_used:
            if worker_used[0].get('status') != STATUS_CLAIMED:
                threading.Timer(
                    self.calc_time_diff_in_seconds(worker_used[0].get('expectedEnded')),
                    self.academy_farmer_thread,
                    [to_max_level]
                ).start()
                return

            # 如果已完成, 则领取奖励并继续
            self.api.kingdom_task_claim(BUILDING_POSITION_MAP['academy'])

        exist_researches = self.api.kingdom_academy_research_list().get('researches', [])
        buildings = self.kingdom_enter.get('kingdom', {}).get('buildings', [])
        academy_level = [b for b in buildings if b.get('code') == BUILDING_CODE_MAP['academy']][0].get('level')

        for category_name, each_category in RESEARCH_CODE_MAP.items():
            logger.info(f'start researching category: {category_name}')
            for research_name, research_code in each_category.items():
                if not self._is_researchable(
                        academy_level, category_name, research_name, exist_researches, to_max_level
                ):
                    continue

                try:
                    res = self.api.kingdom_academy_research({'code': research_code})
                except OtherException as error_code:
                    if str(error_code) == 'not_enough_condition':
                        logger.warning(f'category {category_name} reached max level')
                        break

                    logger.info(f'research failed, try next one, current: {research_name}({research_code})')
                    continue

                threading.Timer(
                    self.calc_time_diff_in_seconds(res.get('newTask').get('expectedEnded')),
                    self.academy_farmer_thread,
                    [to_max_level]
                ).start()
                return

        logger.info('academy_farmer: no research to do, sleep for 2h')
        threading.Timer(2 * 3600, self.academy_farmer_thread, [to_max_level]).start()
        return

    def free_chest_farmer_thread(self, _type=0):
        """
        领取免费宝箱
        :return:
        """
        try:
            res = self.api.item_free_chest(_type)
        except OtherException as error_code:
            if str(error_code) == 'free_chest_not_yet':
                logger.info('free_chest_farmer: free_chest_not_yet, sleep for 2h')
                threading.Timer(2 * 3600, self.free_chest_farmer_thread).start()
                return

            raise

        next_gold = arrow.get(res.get('freeChest', {}).get('gold', {}).get('next'))
        next_silver = arrow.get(res.get('freeChest', {}).get('silver', {}).get('next'))

        if next_gold < next_silver:
            threading.Timer(self.calc_time_diff_in_seconds(next_gold), self.free_chest_farmer_thread, [1]).start()
        else:
            threading.Timer(self.calc_time_diff_in_seconds(next_silver), self.free_chest_farmer_thread, [0]).start()

    def use_resource_in_item_list(self):
        """

        :return:
        """
        item_list = self.api.item_list().get('items', [])

        if not item_list:
            return

        usable_item_list = filter(lambda x: x.get('code') in USABLE_ITEM_CODE_LIST, item_list)

        for each_item in usable_item_list:
            self.api.item_use(each_item.get('code'), each_item.get('amount'))
            time.sleep(random.randint(1, 3))

    def vip_chest_claim(self):
        """
        领取vip宝箱
        daily
        :return:
        """
        vip_info = self.api.kingdom_vip_info()

        if vip_info.get('vip', {}).get('isClaimed'):
            return

        self.api.kingdom_vip_claim()

    def alliance_farmer(self):
        try:
            research_list = self.api.alliance_research_list()
        except OtherException:
            return

        code = research_list.get('recommendResearch')

        if not code:
            code = 31101003  # 骑兵攻击力 1

        try:
            self.api.alliance_research_donate_all(code)
        except OtherException:
            pass
