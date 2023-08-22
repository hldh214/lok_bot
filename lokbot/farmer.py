import base64
import functools
import gzip
import math
import random
import threading
import time

import arrow
import numpy
import socketio
import tenacity

import lokbot.util
from lokbot import logger, socf_logger, sock_logger, socc_logger
from lokbot.client import LokBotApi
from lokbot.enum import *
from lokbot.exceptions import OtherException, FatalApiException

ws_headers = {
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9',
    'Cache-Control': 'no-cache',
    'Origin': 'https://play.leagueofkingdoms.com',
    'Pragma': 'no-cache',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0'
}


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
# noinspection PyBroadException
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
    def __init__(self, token, captcha_solver_config):
        self.kingdom_enter = None
        self.token = token
        self.api = LokBotApi(token, captcha_solver_config, self._request_callback)

        auth_res = self.api.auth_connect({"deviceInfo": {"build": "global"}})
        self.api.protected_api_list = json.loads(base64.b64decode(auth_res.get('lstProtect')).decode())
        self.api.protected_api_list = [str(api).split('/api/').pop() for api in self.api.protected_api_list]
        logger.debug(f'protected_api_list: {self.api.protected_api_list}')
        self.api.xor_password = json.loads(base64.b64decode(auth_res.get('regionHash')).decode()).split('-')[1]
        logger.debug(f'xor_password: {self.api.xor_password}')
        self.token = auth_res.get('token')
        self._id = lokbot.util.decode_jwt(token).get('_id')
        project_root.joinpath(f'data/{self._id}.token').write_text(self.token)

        self.kingdom_enter = self.api.kingdom_enter()
        self.alliance_id = self.kingdom_enter.get('kingdom', {}).get('allianceId')

        self.api.auth_set_device_info({
            "build": "global",
            "OS": "Windows 10",
            "country": "USA",
            "language": "English",
            "bundle": "",
            "version": "1.1660.143.221",
            "platform": "web",
            "pushId": ""
        })

        self.api.chat_logs(f'w{self.kingdom_enter.get("kingdom").get("worldId")}')
        if self.alliance_id:
            self.api.chat_logs(f'a{self.alliance_id}')

        # [food, lumber, stone, gold]
        self.resources = self.kingdom_enter.get('kingdom').get('resources')
        self.buff_item_use_lock = threading.Lock()
        self.hospital_recover_lock = threading.Lock()
        self.has_additional_building_queue = self.kingdom_enter.get('kingdom').get('vip', {}).get('level') >= 5
        self.troop_queue = []
        self.march_limit = 2
        self.march_size = 10000
        self.level = self.kingdom_enter.get('kingdom').get('level')
        self.socf_entered = False
        self.socf_world_id = None
        self.field_object_processed = False
        self.started_at = time.time()
        self.building_queue_available = threading.Event()
        self.research_queue_available = threading.Event()
        self.train_queue_available = threading.Event()
        self.kingdom_tasks = []
        self.zones = []
        self.available_dragos = self._get_available_dragos()
        self.drago_action_point = self.kingdom_enter.get('kingdom').get('dragoActionPoint', {}).get('value', 0)

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

        if building.get('code') == BUILDING_CODE_MAP['barrack']:
            for t in self.kingdom_tasks:
                if t.get('code') == TASK_CODE_CAMP:
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
        if building.get('code') == BUILDING_CODE_MAP['hospital']:
            if building.get('param', {}).get('wounded', []):
                logger.info('hospital has wounded troops, try to recover')
                self.hospital_recover()

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

    def _get_optimal_speedups(self, need_seconds, speedup_type):
        current_map = ITEM_CODE_SPEEDUP_MAP.get(speedup_type)

        assert current_map, f'invalid speedup type: {speedup_type}'

        items = self.api.item_list().get('items', [])
        items = [item for item in items if item.get('code') in current_map.keys()]

        if not items:
            logger.info(f'no speedup item found for {speedup_type}')
            return False

        # build `{code, amount, second}` map
        speedups = []
        for item in items:
            speedups.append({
                'code': item.get('code'),
                'amount': item.get('amount'),
                'second': current_map.get(item.get('code'))
            })

        # sort by speedup second desc
        speedups = sorted(speedups, key=lambda x: x.get('second'), reverse=True)

        counts = {each.get('code'): 0 for each in speedups}

        remaining_seconds = need_seconds
        used_seconds = 0
        for each in speedups:
            while remaining_seconds >= each.get('second') and counts.get(each.get('code')) < each.get('amount'):
                remaining_seconds -= each.get('second')
                counts[each.get('code')] += 1
                used_seconds += each.get('second')

        if speedup_type == 'recover':
            # greedy mode
            speedups_asc = sorted(speedups, key=lambda x: x.get('second'))
            for each in speedups_asc:
                while remaining_seconds >= 0 and counts.get(each.get('code')) < each.get('amount'):
                    remaining_seconds -= each.get('second')
                    counts[each.get('code')] += 1
                    used_seconds += each.get('second')

        counts = {k: v for k, v in counts.items() if v > 0}

        if not counts:
            logger.info(f'cannot find optimal speedups for {speedup_type}')
            return False

        return {
            'counts': counts,
            'used_seconds': used_seconds
        }

    def do_speedup(self, expected_ended, task_id, speedup_type):
        need_seconds = self.calc_time_diff_in_seconds(expected_ended)

        if need_seconds > 60 * 5 or speedup_type == 'recover':
            # try speedup only when need_seconds > 5 minutes
            speedups = self._get_optimal_speedups(need_seconds, speedup_type)
            if speedups:
                counts = speedups.get('counts')
                used_seconds = speedups.get('used_seconds')

                # using speedup items
                logger.info(f'need_seconds: {need_seconds}, using speedups: {counts}, saved {used_seconds} seconds')
                for code, count in counts.items():
                    if speedup_type == 'recover':
                        self.api.kingdom_heal_speedup(code, count)
                    else:
                        self.api.kingdom_task_speedup(task_id, code, count)
                    time.sleep(random.randint(1, 3))

    def _upgrade_building(self, building, buildings, speedup):
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

        building['state'] = BUILDING_STATE_UPGRADING
        self._update_kingdom_enter_building(building)

        if speedup:
            self.do_speedup(res.get('newTask').get('expectedEnded'), res.get('newTask').get('_id'), 'building')

    def _alliance_gift_claim_all(self):
        try:
            self.api.alliance_gift_claim_all()
        except OtherException:
            pass

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
            alliance_point -= cost * amount

    @functools.lru_cache()
    def _get_land_with_level(self):
        rank = self.api.field_worldmap_devrank().get('lands')

        land_with_level = [[], [], [], [], [], [], [], [], [], []]
        for index, level in enumerate(rank):
            # land id start from 100000
            land_with_level[int(level)].append(100000 + index)

        return land_with_level

    @staticmethod
    @functools.lru_cache()
    def _get_land_array():
        return numpy.arange(100000, 165536).reshape(256, 256)

    @functools.lru_cache()
    def _get_land_array_4_by_4(self):
        return blockshaped(self._get_land_array(), 4, 4)

    @staticmethod
    @functools.lru_cache()
    def _get_zone_array():
        return numpy.arange(0, 4096).reshape(64, 64)

    @functools.lru_cache()
    def _get_nearest_land(self, x, y, radius=32):
        land_array = self._get_land_array()
        # current_land_id = land_array[y // 8, x // 8]
        nearby_land_ids = neighbors(land_array, radius, y // 8 + 1, x // 8 + 1)
        nearby_land_ids = [item for sublist in nearby_land_ids for item in sublist if item != 0]
        land_with_level = self._get_land_with_level()

        lands = []
        for index, each_level in enumerate(reversed(land_with_level)):
            level = 10 - index

            # if level < 3:
            #     continue

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

    @functools.lru_cache()
    def _get_zone_id_by_land_id(self, land_id):
        land_array = self._get_land_array_4_by_4()

        return ndindex(land_array, land_id)[0]

    @functools.lru_cache()
    def _get_nearest_zone(self, x, y, radius=16):
        lands = self._get_nearest_land(x, y, radius)
        zones = []
        for land_id, _ in lands:
            zone_id = self._get_zone_id_by_land_id(land_id)
            if zone_id not in zones:
                zones.append(zone_id)

        return zones

    def _get_nearest_zone_ng(self, x, y, radius=8):
        current_zone_id = lokbot.util.get_zone_id_by_coords(x, y)

        idx = ndindex(self._get_zone_array(), current_zone_id)

        nearby_zone_ids = neighbors(self._get_zone_array(), radius, idx[0] + 1, idx[1] + 1)
        nearby_zone_ids = [item.item() for sublist in nearby_zone_ids for item in sublist if item != 0]

        return nearby_zone_ids

    def _update_march_limit(self):
        troops = self.api.kingdom_profile_troops().get('troops')
        self.troop_queue = troops.get('field')
        self.march_limit = troops.get('info').get('marchLimit')
        self.march_size = troops.get('info').get('marchSize')

    def _is_march_limit_exceeded(self):
        if len(self.troop_queue) >= self.march_limit:
            return True

        return False

    @staticmethod
    def _calc_distance(from_loc, to_loc):
        return math.ceil(math.sqrt(math.pow(from_loc[1] - to_loc[1], 2) + math.pow(from_loc[2] - to_loc[2], 2)))

    def _start_march(self, to_loc, march_troops, march_type=MARCH_TYPE_GATHER, drago_id=None):
        data = {
            'fromId': self.kingdom_enter.get('kingdom').get('fieldObjectId'),
            'marchType': march_type,
            'toLoc': to_loc,
            'marchTroops': march_troops
        }

        if drago_id:
            data['dragoId'] = drago_id

        res = self.api.field_march_start(data)

        new_task = res.get('newTask')
        new_task['endTime'] = new_task['expectedEnded']
        self.troop_queue.append(new_task)

    def _prepare_march_troops(self, each_obj, march_type=MARCH_TYPE_GATHER):
        march_info = self.api.field_march_info({
            'fromId': self.kingdom_enter.get('kingdom').get('fieldObjectId'),
            'toLoc': each_obj.get('loc')
        })

        expired_ts = arrow.get(march_info.get('fo').get('expired')).timestamp()
        if expired_ts < arrow.now().timestamp():
            logger.info(f'Expired: {march_info}')
            return []

        if march_type == MARCH_TYPE_MONSTER:
            # check if monster is already dead
            if march_info.get('fo').get('code') != each_obj.get('code'):
                return []

        troops = march_info.get('troops')
        troops.sort(key=lambda x: x.get('code'), reverse=True)  # priority using high tier troops

        need_troop_count = march_info.get('fo').get('param').get('value')
        if march_type == MARCH_TYPE_MONSTER:
            need_troop_count *= 2.5

        if not need_troop_count:
            # "value": 0, means no more resources or monster
            return []

        troop_count = sum([each_troop.get('amount') for each_troop in troops])
        # we don't care about insufficient troops when gathering
        if (march_type == MARCH_TYPE_MONSTER) and (need_troop_count > troop_count):
            logger.info(f'Insufficient troops: {troop_count} < {need_troop_count}: {each_obj}')
            return []

        march_troops = []
        for troop in troops:
            code = troop.get('code')
            amount = troop.get('amount')

            # todo: calc troops load for MARCH_TYPE_MONSTER
            load = 1
            if march_type == MARCH_TYPE_GATHER:
                load = TROOP_LOAD_MAP.get(code, 1)

            total_load = amount * load

            if total_load >= need_troop_count:
                if need_troop_count == 0:
                    amount = 0
                else:
                    amount = math.ceil(need_troop_count / load)
                    need_troop_count = 0
            else:
                need_troop_count -= total_load

            march_troops.append({
                'code': code,
                'level': 0,
                'select': 0,
                'amount': int(amount),
                'dead': 0,
                'wounded': 0,
                'hp': 0,
                'attack': 0,
                'defense': 0,
                'seq': 0
            })

        march_troop_count = sum([each_troop.get('amount') for each_troop in march_troops])
        if march_troop_count > self.march_size:
            logger.info(f'Troop count exceeded: {march_troop_count} > {self.march_size}: {each_obj}')
            return []

        distance = march_info.get('distance')
        logger.info(f'distance: {distance}, object: {each_obj}')

        march_troops.sort(key=lambda x: x.get('code'))  # sort by code asc

        return march_troops

    def _get_available_dragos(self):
        drago_lair_list = self.api.drago_lair_list()
        dragos = drago_lair_list.get('dragos')
        available_dragos = [each for each in dragos if each['lair']['status'] == DRAGO_LAIR_STATUS_STANDBY]

        return available_dragos

    def _on_field_objects_gather(self, each_obj):
        if each_obj.get('occupied'):
            return

        if each_obj.get('code') == OBJECT_CODE_CRYSTAL_MINE and self.level < 11:
            return

        to_loc = each_obj.get('loc')
        march_troops = self._prepare_march_troops(each_obj, MARCH_TYPE_GATHER)

        if not march_troops:
            return

        if each_obj.get('code') == OBJECT_CODE_DRAGON_SOUL_CAVERN:
            self._start_march(to_loc, march_troops, MARCH_TYPE_GATHER, self.available_dragos[0]['_id'])
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
        retry=tenacity.retry_if_not_exception_type(FatalApiException),
        reraise=True
    )
    def sock_thread(self, join_rally_code_list=(OBJECT_CODE_DEATHKAR,)):
        """
        websocket connection of the kingdom
        :return:
        """
        url = self.kingdom_enter.get('networks').get('kingdoms')[0]

        sio = socketio.Client(reconnection=False, logger=sock_logger, engineio_logger=sock_logger)

        @sio.on('/building/update')
        def on_building_update(data):
            logger.debug(data)
            self._update_kingdom_enter_building(data)

        @sio.on('/resource/upgrade')
        def on_resource_update(data):
            logger.debug(data)
            self.resources[data.get('resourceIdx')] = data.get('value')

        @sio.on('/buff/list')
        def on_buff_list(data):
            logger.debug(f'on_buff_list: {data}')

            self.has_additional_building_queue = len([
                item for item in data if item.get('param', {}).get('itemCode') == ITEM_CODE_GOLDEN_HAMMER
            ]) > 0

            while self.started_at + 10 > time.time():
                logger.info(f'started at {arrow.get(self.started_at).humanize()}, wait 10 seconds to activate buff')
                time.sleep(4)

            item_list = self.api.item_list().get('items')

            for buff_type, item_code_list in USABLE_BOOST_CODE_MAP.items():
                already_activated = [item for item in data if item.get('param', {}).get('itemCode') in item_code_list]

                if already_activated:
                    continue

                item_in_inventory = [item for item in item_list if item.get('code') in item_code_list]

                if not item_in_inventory:
                    continue

                if self.buff_item_use_lock.locked():
                    return

                with self.buff_item_use_lock:
                    code = item_in_inventory[0].get('code')
                    logger.info(f'activating buff: {buff_type}, code: {code}')
                    self.api.item_use(code)

                    if code == ITEM_CODE_GOLDEN_HAMMER:
                        self.has_additional_building_queue = True

        @sio.on('/alliance/rally/new')
        def on_alliance_rally_new(data):
            logger.debug(data)
            code = data.get('code')
            if code not in join_rally_code_list:
                logger.info(f'ignore rally: {code}')
                return
            # battles = self.api.alliance_battle_list_v2().get('battles')
            # TODO: what does `state` mean?

        @sio.on('/task/update')
        def on_task_update(data):
            logger.debug(data)
            if data.get('status') == STATUS_FINISHED:
                if data.get('code') in (TASK_CODE_SILVER_HAMMER, TASK_CODE_GOLD_HAMMER):
                    self.building_queue_available.set()

            if data.get('status') == STATUS_CLAIMED:
                if data.get('code') == TASK_CODE_ACADEMY:
                    self.research_queue_available.set()
                if data.get('code') == TASK_CODE_CAMP:
                    self.train_queue_available.set()

        sio.connect(f'{url}?token={self.token}', transports=["websocket"], headers=ws_headers)
        sio.emit('/kingdom/enter', {'token': self.token})

        sio.wait()
        logger.warning('sock_thread disconnected, reconnecting')
        raise tenacity.TryAgain()

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(4),
        wait=tenacity.wait_random_exponential(multiplier=1, max=60),
        retry=tenacity.retry_if_not_exception_type(FatalApiException),
        reraise=True
    )
    def socf_thread(self, radius, targets, share_to=None):
        """
        websocket connection of the field
        :return:
        """
        while self.api.last_requested_at + 16 > time.time():
            # if last request is less than 16 seconds ago, wait
            # when we are in the field, we should not be doing anything else
            logger.info(f'last requested at {arrow.get(self.api.last_requested_at).humanize()}, waiting...')
            time.sleep(4)

        self._update_march_limit()

        while self._is_march_limit_exceeded():
            nearest_end_time = sorted(
                self.troop_queue,
                key=lambda x: x.get('endTime') if x.get('endTime') else '9999-99-99T99:99:99.999Z'
            )[0].get('endTime')
            seconds = self.calc_time_diff_in_seconds(nearest_end_time)
            logger.info(f'_is_march_limit_exceeded: wait {seconds} seconds')
            time.sleep(seconds)
            self._update_march_limit()

        self.socf_entered = False
        self.socf_world_id = self.kingdom_enter.get('kingdom').get('worldId')
        url = self.kingdom_enter.get('networks').get('fields')[0]
        from_loc = self.kingdom_enter.get('kingdom').get('loc')

        if not self.zones:
            logger.info('getting nearest zone')
            self.zones = self._get_nearest_zone_ng(from_loc[1], from_loc[2], radius)

        sio = socketio.Client(reconnection=False, logger=socf_logger, engineio_logger=socf_logger)

        @sio.on('/field/objects/v4')
        def on_field_objects(data):
            packs = data.get('packs')
            gzip_decompress = gzip.decompress(bytearray(packs))
            data_decoded = self.api.b64xor_dec(gzip_decompress)
            objects = data_decoded.get('objects')
            target_code_set = set([target['code'] for target in targets])

            logger.debug(f'Processing {len(objects)} objects')
            for each_obj in objects:
                if self._is_march_limit_exceeded():
                    continue

                code = each_obj.get('code')
                level = each_obj.get('level')
                loc = each_obj.get('loc')

                level_whitelist = [target['level'] for target in targets if target['code'] == code]
                if not level_whitelist:
                    # not the one we are looking for
                    continue

                if share_to and share_to.get('chat_channels'):
                    for chat_channel in share_to.get('chat_channels'):
                        self.api.chat_new(chat_channel, CHAT_TYPE_LOC, f'Lv.{level}?fo_{code}', {'loc': loc})

                if code == OBJECT_CODE_DRAGON_SOUL_CAVERN:
                    if self.drago_action_point < 1:
                        logger.info(f'no_drago_action_point, ignore: {each_obj}')
                        continue
                    if not self.available_dragos:
                        logger.info(f'not_available_drago, ignore: {each_obj}')
                        continue

                level_whitelist = level_whitelist[0]
                if level_whitelist and level not in level_whitelist:
                    logger.info(f'level not in whitelist, ignore: {each_obj}')
                    continue

                try:
                    if code in set(OBJECT_MINE_CODE_LIST).intersection(target_code_set):
                        self._on_field_objects_gather(each_obj)

                    if code in set(OBJECT_MONSTER_CODE_LIST).intersection(target_code_set):
                        self._on_field_objects_monster(each_obj)
                except OtherException as error_code:
                    if str(error_code) in (
                            'full_task', 'not_enough_troop', 'insufficient_actionpoint', 'not_open_gate',
                            'no_drago_action_point', 'no_drago', 'exceed_crystal_daily_quota',
                            'not_available_drago'
                    ):
                        logger.warning(f'on_field_objects: {error_code}, skip')
                        self.field_object_processed = True
                        return

                    raise

            self.field_object_processed = True

        @sio.on('/field/enter/v3')
        def on_field_enter(data):
            data_decoded = self.api.b64xor_dec(data)
            logger.debug(data_decoded)
            self.socf_world_id = data_decoded.get('loc')[0]  # in case of cvc event world map

            # knock
            sio.emit('/zone/leave/list/v2', {'world': self.socf_world_id, 'zones': '[]'})
            default_zones = '[0,64,1,65]'
            sio.emit('/zone/enter/list/v4', self.api.b64xor_enc({'world': self.socf_world_id, 'zones': default_zones}))
            sio.emit('/zone/leave/list/v2', {'world': self.socf_world_id, 'zones': default_zones})

            self.socf_entered = True

        sio.connect(f'{url}?token={self.token}', transports=["websocket"], headers=ws_headers)
        logger.debug(f'entering field: {self.zones}')
        sio.emit('/field/enter/v3', self.api.b64xor_enc({'token': self.token}))

        while not self.socf_entered:
            time.sleep(1)

        step = 9
        grace = 7  # 9 times enter-leave action will cause ban
        index = 0
        while self.zones:
            if index >= grace:
                logger.info('socf_thread grace exceeded, break')
                break

            index += 1
            zone_ids = []
            for _ in range(step):
                if not self.zones:
                    break

                zone_ids.append(self.zones.pop(0))

            if len(zone_ids) < step:
                logger.info(f'len(zone_ids) < {step}, break')
                self.zones = []
                break

            if not sio.connected:
                logger.warning('socf_thread disconnected, reconnecting')
                raise tenacity.TryAgain()

            message = {'world': self.socf_world_id, 'zones': json.dumps(zone_ids, separators=(',', ':'))}
            encoded_message = self.api.b64xor_enc(message)

            sio.emit('/zone/enter/list/v4', encoded_message)
            self.field_object_processed = False
            logger.debug(f'entering zone: {zone_ids} and waiting for processing')
            while not self.field_object_processed:
                time.sleep(1)
            sio.emit('/zone/leave/list/v2', message)

        logger.info('a loop is finished')
        sio.disconnect()
        sio.wait()

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(4),
        wait=tenacity.wait_random_exponential(multiplier=1, max=60),
        retry=tenacity.retry_if_not_exception_type(FatalApiException),
        reraise=True
    )
    def socc_thread(self):
        """
        websocket connection of the chat
        :return:
        """
        url = self.kingdom_enter.get('networks').get('chats')[0]

        sio = socketio.Client(reconnection=False, logger=socc_logger, engineio_logger=socc_logger)

        # no token needed in query string, yet
        sio.connect(url, transports=["websocket"], headers=ws_headers)
        sio.emit('/chat/enter', {'token': self.token})

        sio.wait()
        logger.warning('socc_thread disconnected, reconnecting')
        raise tenacity.TryAgain()

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

    def _building_farmer_worker(self, speedup=False):
        buildings = self.kingdom_enter.get('kingdom', {}).get('buildings', [])
        buildings.sort(key=lambda x: x.get('level'))
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

                res = self._upgrade_building(building, buildings, speedup)

                if res == 'continue':
                    continue
                if res == 'break':
                    break

                return True

        # Then check if there is any upgradeable building
        for building in buildings:
            res = self._upgrade_building(building, buildings, speedup)

            if res == 'continue':
                continue
            if res == 'break':
                break

            return True

        return False

    def building_farmer_thread(self, speedup=False):
        """
        building farmer
        :param speedup:
        :return:
        """
        self.kingdom_tasks = self.api.kingdom_task_all().get('kingdomTasks', [])

        silver_in_use = [t for t in self.kingdom_tasks if t.get('code') == TASK_CODE_SILVER_HAMMER]
        gold_in_use = [t for t in self.kingdom_tasks if t.get('code') == TASK_CODE_GOLD_HAMMER]

        if not silver_in_use or (self.has_additional_building_queue and not gold_in_use):
            if not self._building_farmer_worker(speedup):
                logger.info(f'no building to upgrade, sleep for 2h')
                threading.Timer(7200, self.building_farmer_thread).start()
                return

        self.building_queue_available.wait()  # wait for building queue available from `sock_thread`
        self.building_queue_available.clear()
        threading.Thread(target=self.building_farmer_thread, args=[speedup]).start()

    def academy_farmer_thread(self, to_max_level=False, speedup=False):
        """
        research farmer
        :param to_max_level:
        :param speedup:
        :return:
        """
        self.kingdom_tasks = self.api.kingdom_task_all().get('kingdomTasks', [])

        worker_used = [t for t in self.kingdom_tasks if t.get('code') == TASK_CODE_ACADEMY]

        if worker_used:
            if worker_used[0].get('status') != STATUS_CLAIMED:
                self.research_queue_available.wait()  # wait for research queue available from `sock_thread`
                self.research_queue_available.clear()
                threading.Thread(target=self.academy_farmer_thread, args=[to_max_level, speedup]).start()
                return

            # 如果已完成, 则领取奖励并继续
            self.api.kingdom_task_claim(BUILDING_POSITION_MAP['academy'])

        exist_researches = self.api.kingdom_academy_research_list().get('researches', [])
        buildings = self.kingdom_enter.get('kingdom', {}).get('buildings', [])
        academy_level = [b for b in buildings if b.get('code') == BUILDING_CODE_MAP['academy']][0].get('level')

        for category_name, each_category in RESEARCH_CODE_MAP.items():
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

                if speedup:
                    self.do_speedup(res.get('newTask').get('expectedEnded'), res.get('newTask').get('_id'), 'research')

                self.research_queue_available.wait()  # wait for research queue available from `sock_thread`
                self.research_queue_available.clear()
                threading.Thread(target=self.academy_farmer_thread, args=[to_max_level, speedup]).start()
                return

        logger.info('academy_farmer: no research to do, sleep for 2h')
        threading.Timer(2 * 3600, self.academy_farmer_thread, [to_max_level]).start()
        return

    def _troop_training_capacity(self):
        """
        return total troop training capacity of all barracks
        """
        buildings = self.kingdom_enter.get('kingdom', {}).get('buildings', [])
        troop_training_capacity = 0
        for building in buildings:
            if building['code'] == BUILDING_CODE_MAP['barrack']:
                troop_training_capacity += BARRACK_LEVEL_TROOP_TRAINING_RATE_MAP[int(building['level'])]

        return troop_training_capacity

    def _total_troops_capacity_according_to_resources(self, troop_code):
        """
        return maximum number of troops according to resources
        """
        req_resources = TRAIN_TROOP_RESOURCE_REQUIREMENT[troop_code]

        amount = None
        for req_resource, resource in zip(req_resources, self.resources):
            if req_resource == 0:
                continue

            if amount is None or resource // req_resource <= amount:
                amount = resource // req_resource

        return amount if amount is not None else 0

    def _random_choice_building(self, building_code):
        """
        return a random building object with the building_code
        """
        buildings = self.kingdom_enter.get('kingdom', {}).get('buildings', [])
        return random.choice([building for building in buildings if building['code'] == building_code])

    def train_troop_thread(self, troop_code, speedup=False, interval=3600):
        """
        train troop
        :param interval:
        :param troop_code:
        :param speedup:
        :return:
        """
        while self.api.last_requested_at + 4 > time.time():
            # attempt to prevent `insufficient_resources` due to race conditions
            logger.info(f'last requested at {arrow.get(self.api.last_requested_at).humanize()}, waiting...')
            time.sleep(4)

        self.kingdom_tasks = self.api.kingdom_task_all().get('kingdomTasks', [])

        worker_used = [t for t in self.kingdom_tasks if t.get('code') == TASK_CODE_CAMP]

        troop_training_capacity = self._troop_training_capacity()

        if worker_used:
            if worker_used[0].get('status') == STATUS_CLAIMED:
                self.api.kingdom_task_claim(self._random_choice_building(BUILDING_CODE_MAP['barrack'])['position'])
                logger.info(f'train_troop: one loop completed, sleep for {interval} seconds')
                threading.Timer(interval, self.train_troop_thread, [troop_code, speedup, interval]).start()
                return

            if worker_used[0].get('status') == STATUS_PENDING:
                self.train_queue_available.wait()  # wait for train queue available from `sock_thread`
                self.train_queue_available.clear()
                threading.Thread(target=self.train_troop_thread, args=[troop_code, speedup, interval]).start()
                return

        # if there is not enough resource, train how much possible
        total_troops_capacity_according_to_resources = self._total_troops_capacity_according_to_resources(troop_code)
        if troop_training_capacity > total_troops_capacity_according_to_resources:
            troop_training_capacity = total_troops_capacity_according_to_resources

        if not troop_training_capacity:
            logger.info('train_troop: no resource, sleep for 1h')
            threading.Timer(3600, self.train_troop_thread, [troop_code, speedup, interval]).start()
            return

        res = self.api.train_troop(troop_code, troop_training_capacity)

        if speedup:
            self.do_speedup(res.get('newTask').get('expectedEnded'), res.get('newTask').get('_id'), 'train')

        self.train_queue_available.wait()  # wait for train queue available from `sock_thread`
        self.train_queue_available.clear()
        threading.Thread(target=self.train_troop_thread, args=[troop_code, speedup, interval]).start()

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

        next_dict = {
            0: arrow.get(res.get('freeChest', {}).get('silver', {}).get('next')),
            1: arrow.get(res.get('freeChest', {}).get('gold', {}).get('next')),
            2: arrow.get(res.get('freeChest', {}).get('platinum', {}).get('next')),
        }
        next_type = min(next_dict, key=next_dict.get)

        threading.Timer(
            self.calc_time_diff_in_seconds(next_dict[next_type]),
            self.free_chest_farmer_thread, [next_type]
        ).start()

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

    def alliance_farmer(self, gift_claim=True, help_all=True, research_donate=True, shop_auto_buy_item_code_list=None):
        if not self.alliance_id:
            return

        if gift_claim:
            self._alliance_gift_claim_all()

        if help_all:
            self._alliance_help_all()

        if research_donate:
            self._alliance_research_donate_all()

        if shop_auto_buy_item_code_list and type(shop_auto_buy_item_code_list) == list:
            self._alliance_shop_autobuy(shop_auto_buy_item_code_list)

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

            resource_index = lokbot.util.get_resource_index_by_item_code(each_item.get('costItemCode'))

            if resource_index == -1:
                continue

            if each_item.get('cost') > self.resources[resource_index]:
                continue

            self.api.kingdom_caravan_buy(each_item.get('_id'))

    def mail_claim(self):
        self.api.mail_claim_all(1)  # report
        time.sleep(random.randint(4, 6))
        self.api.mail_claim_all(2)  # alliance
        time.sleep(random.randint(4, 6))
        self.api.mail_claim_all(3)  # system

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
        if self.hospital_recover_lock.locked():
            logger.info('another hospital_recover is running, skip')
            return

        with self.hospital_recover_lock:
            wounded = self.api.kingdom_hospital_wounded().get('wounded', [])

            estimated_end_time = None
            for each_batch in wounded:
                if estimated_end_time is None:
                    estimated_end_time = arrow.get(each_batch[0].get('startTime'))
                time_total = sum([each.get('time') for each in each_batch])
                estimated_end_time = estimated_end_time.shift(seconds=time_total)

            if estimated_end_time and estimated_end_time > arrow.utcnow():
                self.do_speedup(estimated_end_time, 'dummy_task_id', 'recover')

            self.api.kingdom_hospital_recover()

    def keepalive_request(self):
        try:
            lokbot.util.run_functions_in_random_order(
                self.api.kingdom_wall_info,
                self.api.quest_main,
                self.api.item_list,
                self.api.kingdom_treasure_list,
                self.api.event_list,
                self.api.event_cvc_open,
                self.api.event_roulette_open,
                self.api.drago_lair_list,
                self.api.pkg_recommend,
                self.api.pkg_list,
            )
        except OtherException:
            pass
