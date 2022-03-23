import functools
import math
import random
import threading
import time

import arrow
import numpy
import socketio
import tenacity

from lokbot.client import LokBotApi
from lokbot import logger, builtin_logger
from lokbot.exceptions import OtherException
from lokbot.enum import *
from lokbot.util import get_resource_index_by_item_code, run_functions_in_random_order


# Ref: https://stackoverflow.com/a/16858283/6266737
def blockshaped(arr, nrows, ncols):
    """
    Return an array of shape (n, nrows, ncols) where
    n * nrows * ncols = arr.size

    If arr is a 2D array, the returned array should look like n subblocks with
    each subblock preserving the "physical" layout of arr.
    """
    h, w = arr.shape
    assert h % nrows == 0, f"{h} rows is not evenly divisible by {nrows}"
    assert w % ncols == 0, f"{w} cols is not evenly divisible by {ncols}"
    return (arr.reshape(h // nrows, nrows, -1, ncols)
            .swapaxes(1, 2)
            .reshape(-1, nrows, ncols))


# Ref: https://stackoverflow.com/a/432175/6266737
def ndindex(ndarray, item):
    if len(ndarray.shape) == 1:
        try:
            return [ndarray.tolist().index(item)]
        except:
            pass
    else:
        for i, subarray in enumerate(ndarray):
            try:
                return [i] + ndindex(subarray, item)
            except:
                pass


# Ref: https://stackoverflow.com/a/22550933/6266737
def neighbors(a, radius, row_number, column_number):
    return [[a[i][j] if 0 <= i < len(a) and 0 <= j < len(a[0]) else 0
             for j in range(column_number - 1 - radius, column_number + radius)]
            for i in range(row_number - 1 - radius, row_number + radius)]


class LokFarmer:
    def __init__(self, access_token, captcha_solver_config):
        self.kingdom_enter = None
        self.access_token = access_token
        self.api = LokBotApi(access_token, captcha_solver_config, self._request_callback)

        device_info = {
            "OS": "iOS 15.3.1",
            "country": "USA",
            "language": "English",
            "version": "1.1422.103.175",
            "platform": "ios",
            "build": "global"
        }

        self.kingdom_enter = self.api.kingdom_enter()

        # knock moved to schedule job
        self.api.auth_set_device_info(device_info)
        self.api.chat_logs(self.kingdom_enter.get('kingdom').get('worldId'))

        # [food, lumber, stone, gold]
        self.resources = self.kingdom_enter.get('kingdom').get('resources')
        self.buff_item_use_lock = threading.RLock()
        self.march_start_lock = threading.RLock()
        self.has_additional_building_queue = self.kingdom_enter.get('kingdom').get('vip', {}).get('level') >= 5
        self.troop_queue = []
        self.march_limit = 2
        self._update_march_limit()

    @staticmethod
    def calc_time_diff_in_seconds(expected_ended):
        time_diff = arrow.get(expected_ended) - arrow.utcnow()
        diff_in_seconds = int(time_diff.total_seconds())

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

    def _update_kingdom_enter_building(self, building):
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
                building = res.get('newBuilding', building)
            else:
                res = self.api.kingdom_building_upgrade(building)
                building = res.get('updateBuilding', building)
        except OtherException as error_code:
            if str(error_code) == 'full_task':
                logger.warning('building_farmer: full_task, quit')
                return 'break'

            logger.info(f'building upgrade failed: {building}')
            return 'continue'

        building['level'] += 1
        self._update_kingdom_enter_building(building)

        # TODO: it's necessary only when their server is not stable
        building['state'] = BUILDING_STATE_NORMAL
        threading.Timer(
            self.calc_time_diff_in_seconds(res.get('newTask').get('expectedEnded')) - 5,
            self._update_kingdom_enter_building,
            [building]
        )

        threading.Timer(
            self.calc_time_diff_in_seconds(res.get('newTask').get('expectedEnded')),
            self.building_farmer_thread,
            [task_code]
        ).start()

        return

    def _alliance_help_all(self):
        try:
            self.api.alliance_help_all()
        except OtherException:
            pass

    def _alliance_research_donate_all(self):
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

    def _alliance_shop_autobuy(self, item_code_list=(ITEM_CODE_VIP_100,)):
        try:
            shop_list = self.api.alliance_shop_list()
        except OtherException:
            return

        alliance_point = shop_list.get('alliancePoint')
        shop_items = shop_list.get('allianceShopItems')

        for each_shop_item in shop_items:
            code = each_shop_item.get('code')
            if code not in item_code_list:
                continue

            cost = each_shop_item.get('ap_1')  # or 'ap_2'?
            amount = each_shop_item.get('amount')

            minimum_buy_amount = int(alliance_point / cost)
            if minimum_buy_amount < 1:
                continue

            self.api.alliance_shop_buy(code, amount if amount < minimum_buy_amount else minimum_buy_amount)

    @functools.lru_cache()
    def _get_land_with_level(self):
        rank = self.api.field_worldmap_devrank().get('lands')

        land_with_level = [[], [], [], [], [], [], [], [], [], []]
        for index, level in enumerate(rank):
            # land id start from 100000
            land_with_level[int(level)].append(100000 + index)

        return land_with_level

    @staticmethod
    def _get_land_array():
        return numpy.arange(100000, 165536).reshape(256, 256)

    def _get_nearest_land(self, x, y, radius=64):
        land_array = self._get_land_array()
        # current_land_id = land_array[y // 8, x // 8]
        nearby_land_ids = neighbors(land_array, radius, y // 8 + 1, x // 8 + 1)
        nearby_land_ids = [item for sublist in nearby_land_ids for item in sublist if item != 0]
        land_with_level = self._get_land_with_level()

        lands = []
        for index, each_level in enumerate(reversed(land_with_level)):
            level = 10 - index

            if level < 3:
                continue

            lands += [(each_land_id, level) for each_land_id in each_level if each_land_id in nearby_land_ids]

        return lands

    def _get_top_leveled_land(self, limit=1024):
        land_with_level = self._get_land_with_level()

        lands = []
        for index, each_level in enumerate(reversed(land_with_level)):
            level = 10 - index

            if level < 2:
                continue

            if len(each_level) > limit:
                return lands + each_level[:limit]

            lands += [(each, level) for each in each_level]
            limit -= len(each_level)

        return lands

    def _get_zone_id_by_land_id(self, land_id):
        land_array = blockshaped(self._get_land_array(), 4, 4)

        return ndindex(land_array, land_id)[0]

    def _update_march_limit(self):
        troops = self.api.kingdom_profile_troops().get('troops')
        self.troop_queue = troops.get('field')
        self.march_limit = troops.get('info').get('marchLimit')

    def _is_march_limit_exceeded(self):
        if len(self.troop_queue) >= self.march_limit:
            return True

        return False

    @staticmethod
    def _calc_distance(from_loc, to_loc):
        return math.ceil(math.sqrt(math.pow(from_loc[1] - to_loc[1], 2) + math.pow(from_loc[2] - to_loc[2], 2)))

    def _start_march(self, to_loc, march_troops, march_type=MARCH_TYPE_GATHER):
        res = self.api.field_march_start({
            'fromId': self.kingdom_enter.get('kingdom').get('fieldObjectId'),
            'marchType': march_type,
            'toLoc': to_loc,
            'marchTroops': march_troops
        })

        new_task = res.get('newTask')
        new_task['endTime'] = new_task['expectedEnded']
        self.troop_queue.append(new_task)

    def _prepare_march_troops(self, each_obj, march_type=MARCH_TYPE_GATHER):
        march_info = self.api.field_march_info({
            'fromId': self.kingdom_enter.get('kingdom').get('fieldObjectId'),
            'toLoc': each_obj.get('loc')
        })

        if march_type == MARCH_TYPE_MONSTER:
            # check if monster is already dead
            if march_info.get('fo').get('code') != each_obj.get('code'):
                return []

        troops = march_info.get('troops')
        troops.sort(key=lambda x: x.get('code'), reverse=True)  # priority using high tier troops

        # todo: calc troops load
        need_troop_count = march_info.get('fo').get('param').get('value')
        if march_type == MARCH_TYPE_MONSTER:
            need_troop_count *= 2.5

        troop_count = sum([each_troop.get('amount') for each_troop in troops])

        # we don't care about insufficient troops when gathering
        if (march_type == MARCH_TYPE_MONSTER) and (need_troop_count > troop_count):
            return []

        # distance = self._calc_distance(from_loc, to_loc)
        distance = march_info.get('distance')
        logger.info(f'distance: {distance}, object: {each_obj}')

        march_troops = []
        for troop in troops:
            amount = troop.get('amount')
            code = troop.get('code')

            if amount >= need_troop_count:
                amount = need_troop_count
                need_troop_count = 0
            else:
                need_troop_count -= amount

            march_troops.append({
                'code': code,
                'amount': amount,
                'level': 0,
                'select': 0,
                'dead': 0,
                'wounded': 0,
                'seq': 0
            })

        return march_troops

    def _on_field_objects_gather(self, each_obj):
        if each_obj.get('occupied'):
            return

        to_loc = each_obj.get('loc')
        march_troops = self._prepare_march_troops(each_obj, MARCH_TYPE_GATHER)

        if not march_troops:
            return

        self._start_march(to_loc, march_troops, MARCH_TYPE_GATHER)

    def _on_field_objects_monster(self, each_obj):
        to_loc = each_obj.get('loc')
        march_troops = self._prepare_march_troops(each_obj, MARCH_TYPE_MONSTER)

        if not march_troops:
            return

        self._start_march(to_loc, march_troops, MARCH_TYPE_MONSTER)

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
            self._update_kingdom_enter_building(data)

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

                if not self.buff_item_use_lock.acquire(blocking=False):
                    return

                code = item_in_inventory[0].get('code')
                logger.info(f'activating buff: {buff_type}, code: {code}')
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
        world = self.kingdom_enter.get('kingdom').get('worldId')
        url = self.kingdom_enter.get('networks').get('fields')[0]
        from_loc = self.kingdom_enter.get('kingdom').get('loc')

        lands = self._get_nearest_land(from_loc[1], from_loc[2])
        # lands = self._get_top_leveled_land()
        zones = []
        for land_id, _ in lands:
            zone_id = self._get_zone_id_by_land_id(land_id)
            if zone_id not in zones:
                zones.append(zone_id)

        sio = socketio.Client(reconnection=False, logger=builtin_logger, engineio_logger=builtin_logger)

        @sio.on('/field/objects')
        def on_field_objects(data):
            objects = data.get('objects')
            for each_obj in objects:
                if self._is_march_limit_exceeded():
                    continue

                if not self.march_start_lock.acquire(blocking=False):
                    return

                code = each_obj.get('code')

                try:
                    if code in (
                            OBJECT_CODE_CRYSTAL_MINE,
                    ):
                        self._on_field_objects_gather(each_obj)

                    if code in (
                            OBJECT_CODE_GOBLIN,
                            OBJECT_CODE_GOLEM,
                            OBJECT_CODE_SKELETON,
                            OBJECT_CODE_ORC
                    ):
                        self._on_field_objects_monster(each_obj)
                except OtherException as error_code:
                    if str(error_code) in ('full_task', 'not_enough_troop'):
                        logger.warning(f'on_field_objects: {error_code}, skip')
                        return

                    raise

        sio.connect(url, transports=["websocket"])
        sio.emit('/field/enter', {'token': self.access_token})

        while self._is_march_limit_exceeded():
            nearest_end_time = sorted(self.troop_queue, key=lambda x: x.get('endTime'))[0].get('endTime')
            seconds = self.calc_time_diff_in_seconds(nearest_end_time)
            logger.info(f'_is_march_limit_exceeded: wait {seconds} seconds')
            time.sleep(seconds)
            self._update_march_limit()

        for zone_id in zones:
            if not sio.connected:
                logger.warning('socf_thread disconnected, reconnecting')
                raise tenacity.TryAgain()

            sio.emit('/zone/enter/list', {'world': world, 'zones': json.dumps([zone_id])})
            time.sleep(random.uniform(1, 2))
            sio.emit('/zone/leave/list', {'world': world, 'zones': json.dumps([zone_id])})

        logger.info('a loop is finished')
        sio.disconnect()
        sio.wait()

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(4),
        wait=tenacity.wait_random_exponential(multiplier=1, max=60),
        reraise=True
    )
    def socc_thread(self):
        url = self.kingdom_enter.get('networks').get('chats')[0]

        sio = socketio.Client(reconnection=False, logger=builtin_logger, engineio_logger=builtin_logger)

        sio.connect(url, transports=["websocket"])
        sio.emit('/chat/enter', {'token': self.access_token})

        # do nothing
        sio.wait()

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

        # event
        event_list = self.api.event_list()
        event_has_red_dot = [each for each in event_list.get('events') if each.get('reddot') > 0]
        for event in event_has_red_dot:
            event_info = self.api.event_info(event.get('_id'))
            finished_code = [
                each.get('code') for each in event_info.get('eventKingdom').get('events')
                if each.get('status') == STATUS_FINISHED
            ]

            if not finished_code:
                continue

            [self.api.event_claim(
                event_info.get('event').get('_id'), each.get('_id'), each.get('code')
            ) for each in event_info.get('event').get('events') if each.get('code') in finished_code]

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
        kingdom_level = [b for b in buildings if b.get('code') == BUILDING_CODE_MAP['castle']][0].get('level')

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
        if not self.kingdom_enter.get('kingdom', {}).get('allianceId'):
            return

        self._alliance_help_all()
        self._alliance_research_donate_all()
        self._alliance_shop_autobuy()

    def caravan_farmer(self):
        caravan = self.api.kingdom_caravan_list().get('caravan')

        if not caravan:
            return

        for each_item in caravan.get('items', []):
            if each_item.get('amount') < 1:
                continue

            if each_item.get('code') not in BUYABLE_CARAVAN_ITEM_CODE_LIST:
                continue

            if each_item.get('costItemCode') not in BUYABLE_CARAVAN_ITEM_CODE_LIST:
                continue

            resource_index = get_resource_index_by_item_code(each_item.get('costItemCode'))

            if resource_index == -1:
                continue

            if each_item.get('cost') > self.resources[resource_index]:
                continue

            self.api.kingdom_caravan_buy(each_item.get('_id'))

    def mail_claim(self):
        self.api.mail_claim_all()

    def wall_repair(self):
        wall_info = self.api.kingdom_wall_info()

        max_durability = wall_info.get('wall', {}).get('maxDurability')
        durability = wall_info.get('wall', {}).get('durability')
        last_repair_date = wall_info.get('wall', {}).get('lastRepairDate')

        if not last_repair_date:
            return

        last_repair_date = arrow.get(last_repair_date)
        last_repair_diff = arrow.utcnow() - last_repair_date

        if durability >= max_durability:
            return

        if int(last_repair_diff.total_seconds()) < 60 * 30:
            # 30 minute interval
            return

        self.api.kingdom_wall_repair()

    def hospital_recover(self):
        try:
            self.api.kingdom_hospital_recover()
        except OtherException:
            pass

    def keepalive_request(self):
        run_functions_in_random_order(
            self.api.kingdom_wall_info,
            self.api.quest_main,
            self.api.item_list,
            self.api.kingdom_treasure_list,
            self.api.event_list,
            self.api.event_cvc_open,
            self.api.event_roulette_open,
            self.api.pkg_recommend,
            self.api.pkg_list,
        )
