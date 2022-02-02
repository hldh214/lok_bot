import io
import json
import logging
import random
import threading
import time

import arrow
import fire
import httpx
import ratelimit
import schedule
import socketio
import tenacity

from loguru import logger
from PIL import Image

API_BASE_URL = 'https://api-lok-live.leagueofkingdoms.com/api/'

TUTORIAL_CODE_INTRO = 'Intro'  # 过场动画结束后

# 任务状态
STATUS_PENDING = 1  # 未完成任务
STATUS_FINISHED = 2  # 已完成待领取奖励
STATUS_CLAIMED = 3  # 已领取奖励

BUILDING_STATE_NORMAL = 1  # 正常
BUILDING_STATE_UPGRADING = 2  # 升级中

# 建筑类型 code
CODE_FOOD = 40100202  # 玉米
CODE_LUMBER = 40100203  # 木材
CODE_STONE = 40100204  # 石材
CODE_GOLD = 40100205  # 黄金
CODE_ACADEMY = 40100105  # 学院
HARVESTABLE_CODE = [CODE_FOOD, CODE_LUMBER, CODE_STONE, CODE_GOLD]

# 任务类型 code
TASK_CODE_SILVER_HAMMER = 1  # 免费建筑工
TASK_CODE_GOLD_HAMMER = 8  # 黄金建筑工
TASK_CODE_CAMP = 3  # 军营
TASK_CODE_ACADEMY = 6  # 学院

# 建筑位置 position
POSITION_CASTLE = 1  # 城堡
POSITION_ACADEMY = 5  # 学院
POSITION_UNION = 7  # 联盟中心

POSITION_101 = 101
POSITION_102 = 102
POSITION_103 = 103

POSITION_104 = 104
POSITION_105 = 105
POSITION_106 = 106
POSITION_107 = 107
POSITION_108 = 108
POSITION_109 = 109
POSITION_110 = 110
POSITION_111 = 111

POSITION_114 = 114

POSITION_115 = 115
POSITION_116 = 116
POSITION_117 = 117
POSITION_118 = 118

POSITION_112 = 112
POSITION_113 = 113
POSITION_119 = 119
POSITION_120 = 120

# 初始获得的建筑位置
POSITION_INITIAL = (
    POSITION_104, POSITION_105, POSITION_106, POSITION_107, POSITION_108, POSITION_109, POSITION_110, POSITION_111
)

# 5 级解锁的建筑位置
POSITION_UNLOCKED_AT_LEVEL_5 = (
    POSITION_115, POSITION_116, POSITION_117, POSITION_118
)

# 10 级解锁的建筑位置
POSITION_UNLOCKED_AT_LEVEL_10 = (
    POSITION_101, POSITION_102, POSITION_103, POSITION_114
)

# 15 级解锁的建筑位置
POSITION_UNDER_LEVEL_15 = (
    POSITION_112, POSITION_113, POSITION_119, POSITION_120
)

BUILDING_UPGRADE_BLACKLIST = (POSITION_UNION,)

RESEARCH_CODE = {
    'battle': [
        {'name': 'infantry_hp_1', 'code': 30101001, 'minimum_required_level': 2, 'max_level': 5},
        {'name': 'archery_hp_1', 'code': 30101002, 'minimum_required_level': 2, 'max_level': 5},
        {'name': 'cavalry_hp_1', 'code': 30101003, 'minimum_required_level': 2, 'max_level': 5},

        {'name': 'infantry_defense_1', 'code': 30101004, 'minimum_required_level': 2, 'max_level': 5},
        {'name': 'archery_defense_1', 'code': 30101005, 'minimum_required_level': 2, 'max_level': 5},
        {'name': 'cavalry_defense_1', 'code': 30101006, 'minimum_required_level': 2, 'max_level': 5},

        {'name': 'infantry_attack_1', 'code': 30101007, 'minimum_required_level': 2, 'max_level': 5},
        {'name': 'archery_attack_1', 'code': 30101008, 'minimum_required_level': 2, 'max_level': 5},
        {'name': 'cavalry_attack_1', 'code': 30101009, 'minimum_required_level': 2, 'max_level': 5},

        {'name': 'infantry_speed_1', 'code': 30101010, 'minimum_required_level': 2, 'max_level': 5},
        {'name': 'archery_speed_1', 'code': 30101011, 'minimum_required_level': 2, 'max_level': 5},
        {'name': 'cavalry_speed_1', 'code': 30101012, 'minimum_required_level': 2, 'max_level': 5},

        {'name': 'troops_load', 'code': 30101013, 'minimum_required_level': 2, 'max_level': 5},
    ],
    'production': [
        {'name': 'food_production_1', 'code': 30102001, 'minimum_required_level': 2, 'max_level': 5},
        {'name': 'lumber_production_1', 'code': 30102002, 'minimum_required_level': 2, 'max_level': 5},
        {'name': 'stone_production_1', 'code': 30102003, 'minimum_required_level': 2, 'max_level': 5},

        {'name': 'gold_production_1', 'code': 30102004, 'minimum_required_level': 2, 'max_level': 5},

        {'name': 'food_capacity_1', 'code': 30102005, 'minimum_required_level': 2, 'max_level': 5},
        {'name': 'lumber_capacity_1', 'code': 30102006, 'minimum_required_level': 2, 'max_level': 5},
        {'name': 'stone_capacity_1', 'code': 30102007, 'minimum_required_level': 2, 'max_level': 5},

        {'name': 'gold_capacity_1', 'code': 30102008, 'minimum_required_level': 2, 'max_level': 5},

        {'name': 'food_gathering_speed_1', 'code': 30102009, 'minimum_required_level': 2, 'max_level': 5},
        {'name': 'lumber_gathering_speed_1', 'code': 30102010, 'minimum_required_level': 2, 'max_level': 5},
        {'name': 'stone_gathering_speed_1', 'code': 30102011, 'minimum_required_level': 2, 'max_level': 5},

        {'name': 'gold_gathering_speed_1', 'code': 30102012, 'minimum_required_level': 2, 'max_level': 5},

        {'name': 'crystal_gathering_speed_1', 'code': 30102013, 'minimum_required_level': 2, 'max_level': 5},

        {'name': 'infantry_storage', 'code': 30102014, 'minimum_required_level': 2, 'max_level': 5},
        {'name': 'archery_storage', 'code': 30102015, 'minimum_required_level': 2, 'max_level': 5},
        {'name': 'cavalry_storage', 'code': 30102016, 'minimum_required_level': 2, 'max_level': 5},

        {'name': 'research_speed_1', 'code': 30102017, 'minimum_required_level': 2, 'max_level': 5},

        {'name': 'construct_speed_1', 'code': 30102018, 'minimum_required_level': 2, 'max_level': 5},

        {'name': 'resource_protect', 'code': 30102019, 'minimum_required_level': 2, 'max_level': 5},
    ],
    'advanced': [],
}

ITEM_CODE_FOOD_1K = 10101013
ITEM_CODE_FOOD_5K = 10101014
ITEM_CODE_FOOD_10K = 10101015
ITEM_CODE_FOOD_50K = 10101016
ITEM_CODE_FOOD_100K = 10101017
ITEM_CODE_FOOD_500K = 10101018
ITEM_CODE_FOOD_1M = 10101019

ITEM_CODE_LUMBER_1K = 10101022
ITEM_CODE_LUMBER_5K = 10101023
ITEM_CODE_LUMBER_10K = 10101024
ITEM_CODE_LUMBER_50K = 10101025
ITEM_CODE_LUMBER_100K = 10101026
ITEM_CODE_LUMBER_500K = 10101027
ITEM_CODE_LUMBER_1M = 10101028

ITEM_CODE_STONE_1K = 10101031
ITEM_CODE_STONE_5K = 10101032
ITEM_CODE_STONE_10K = 10101033
ITEM_CODE_STONE_50K = 10101034
ITEM_CODE_STONE_100K = 10101035
ITEM_CODE_STONE_500K = 10101036
ITEM_CODE_STONE_1M = 10101037

ITEM_CODE_GOLD_1K = 10101040
ITEM_CODE_GOLD_5K = 10101041
ITEM_CODE_GOLD_10K = 10101042
ITEM_CODE_GOLD_50K = 10101043
ITEM_CODE_GOLD_100K = 10101044
ITEM_CODE_GOLD_500K = 10101045
ITEM_CODE_GOLD_1M = 10101046

USABLE_ITEM_CODE_LIST = (
    ITEM_CODE_FOOD_1K, ITEM_CODE_FOOD_5K, ITEM_CODE_FOOD_10K, ITEM_CODE_FOOD_50K, ITEM_CODE_FOOD_100K,

    ITEM_CODE_LUMBER_1K, ITEM_CODE_LUMBER_5K, ITEM_CODE_LUMBER_10K, ITEM_CODE_LUMBER_50K, ITEM_CODE_LUMBER_100K,

    ITEM_CODE_STONE_1K, ITEM_CODE_STONE_5K, ITEM_CODE_STONE_10K, ITEM_CODE_STONE_50K, ITEM_CODE_STONE_100K,

    ITEM_CODE_GOLD_1K, ITEM_CODE_GOLD_5K, ITEM_CODE_GOLD_10K, ITEM_CODE_GOLD_50K, ITEM_CODE_GOLD_100K,
)

builtin_logger = logging.getLogger(__name__)
builtin_logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

file_channel = logging.FileHandler('../builtin_logger.log')
file_channel.setFormatter(formatter)

builtin_logger.addHandler(file_channel)

logger.add('loguru.log')


class ApiException(Exception):
    pass


class NoAuthException(ApiException):
    pass


class NeedCaptchaException(ApiException):
    pass


class DuplicatedException(ApiException):
    pass


class ExceedLimitPacketException(ApiException):
    pass


class OtherException(ApiException):
    pass


class LokBotApi:
    def __init__(self, access_token):
        self.opener = httpx.Client(
            headers={
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Origin': 'https://play.leagueofkingdoms.com',
                'Referer': 'https://play.leagueofkingdoms.com',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:96.0) Gecko/20100101 Firefox/96.0',
                'x-access-token': access_token
            },
            http2=True,
            base_url=API_BASE_URL
        )

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(4),
        wait=tenacity.wait_random_exponential(multiplier=1, max=60),
        retry=tenacity.retry_if_exception_type(httpx.HTTPError),  # general http error
        reraise=True
    )
    @tenacity.retry(
        wait=tenacity.wait_fixed(1),
        retry=tenacity.retry_if_exception_type(ratelimit.RateLimitException),  # client-side rate limiter
    )
    @tenacity.retry(
        wait=tenacity.wait_random_exponential(multiplier=1, max=60),
        retry=tenacity.retry_if_exception_type(DuplicatedException),  # server-side rate limiter(wait ~2s)
    )
    @tenacity.retry(
        wait=tenacity.wait_fixed(3600),
        retry=tenacity.retry_if_exception_type(ExceedLimitPacketException),  # server-side rate limiter(wait 1h)
    )
    @ratelimit.limits(calls=1, period=2)
    def post(self, url, json_data=None):
        if json_data is None:
            json_data = {}

        response = self.opener.post(url, data={'json': json.dumps(json_data)})

        json_response = response.json()

        logger.debug(json.dumps({
            'url': url,
            'data': json_data,
            'res': json_response,
            'elapsed': response.elapsed.total_seconds()
        }))

        if json_response.get('result'):
            return json_response

        err = json_response.get('err')
        code = err.get('code')

        if code == 'no_auth':
            raise NoAuthException()

        if code == 'need_captcha':
            raise NeedCaptchaException()

        if code == 'duplicated':
            raise DuplicatedException()

        if code == 'exceed_limit_packet':
            raise ExceedLimitPacketException()

        raise OtherException(code)

    def auth_captcha(self):
        return self.opener.get('auth/captcha')

    def auth_captcha_confirm(self, value):
        return self.post('auth/captcha/confirm', {'value': value})

    def alliance_research_list(self):
        return self.post('alliance/research/list')

    def alliance_research_donate_all(self, code):
        return self.post('alliance/research/donateAll', {'code': code})

    def quest_list(self):
        """
        获取任务列表
        :return:
        """
        return self.post('quest/list')

    def quest_list_daily(self):
        """
        获取日常任务列表
        :return:
        """
        return self.post('quest/list/daily')

    def quest_claim(self, quest):
        """
        领取任务奖励
        :param quest:
        :return:
        """
        return self.post('quest/claim', {'questId': quest.get('_id'), 'code': quest.get('code')})

    def quest_claim_daily(self, quest):
        """
        领取日常任务奖励
        :param quest:
        :return:
        """
        return self.post('quest/claim/daily', {'questId': quest.get('_id'), 'code': quest.get('code')})

    def quest_claim_daily_level(self, reward):
        """
        领取日常任务上方进度条奖励
        :param reward:
        :return:
        """
        return self.post('quest/claim/daily/level', {'level': reward.get('level')})

    def kingdom_enter(self):
        """
        获取基础信息
        :return:
        """
        return self.post('kingdom/enter')

    def kingdom_task_all(self):
        """
        获取当前任务执行状态(左侧建筑x2/招募/研究)
        :return:
        """
        return self.post('kingdom/task/all')

    def kingdom_task_claim(self, position):
        """
        领取任务奖励
        :return:
        """
        return self.post('kingdom/task/claim', {'position': position})

    def kingdom_tutorial_finish(self, code):
        """
        完成教程
        :return:
        """
        return self.post('kingdom/tutorial/finish', {'code': code})

    def kingdom_academy_research_list(self):
        """
        获取研究列表
        :return:
        """
        return self.post('kingdom/arcademy/research/list')

    def kingdom_hospital_recover(self):
        """
        医院恢复
        :return:
        """
        return self.post('kingdom/hospital/recover')

    def kingdom_resource_harvest(self, position):
        """
        收获资源
        :param position:
        :return:
        """
        return self.post('kingdom/resource/harvest', {'position': position})

    def kingdom_building_upgrade(self, building, instant=0):
        """
        建筑升级
        :param building:
        :param instant:
        :return:
        """
        return self.post('kingdom/building/upgrade', {
            'position': building.get('position'),
            'level': building.get('level'),
            'instant': instant
        })

    def kingdom_academy_research(self, research, instant=0):
        """
        学院研究升级
        :param research:
        :param instant:
        :return:
        """
        return self.post('kingdom/arcademy/research', {
            'researchCode': research.get('code'),
            'instant': instant
        })

    def kingdom_vip_info(self):
        """
        获取VIP信息
        :return:
        """
        return self.post('kingdom/vip/info')

    def kingdom_vip_claim(self):
        """
        领取VIP奖励
        daily
        :return:
        """
        return self.post('kingdom/vip/claim')

    def kingdom_world_change(self, world_id):
        """
        切换世界
        :param world_id:
        :return:
        """
        return self.post('kingdom/world/change', {'worldId': world_id})

    def alliance_help_all(self):
        """
        帮助全部
        :return:
        """
        return self.post('alliance/help/all')

    def item_list(self):
        """
        获取道具列表
        :return:
        """
        return self.post('item/list')

    def item_use(self, code, amount=1):
        """
        使用道具
        :param code:
        :param amount:
        :return:
        """
        return self.post('item/use', {'code': code, 'amount': amount})

    def item_free_chest(self, _type=0):
        """
        领取免费宝箱
        :type _type: int 0: silver 1: gold
        :return:
        """
        return self.post('item/freechest', {'type': _type})

    def event_roulette_spin(self):
        """
        转轮抽奖
        daily
        :return:
        """
        return self.post('event/roulette/spin')


class LokFarmer:
    def __init__(self, access_token):
        self.access_token = access_token
        self.api = LokBotApi(access_token)
        self.kingdom_enter = self.api.kingdom_enter()

        captcha = self.kingdom_enter.get('captcha')
        if captcha and captcha.get('next'):
            logger.critical('需要验证码: {}'.format(captcha.get('next')))
            exit(1)

    @staticmethod
    def calc_time_diff_in_seconds(expected_ended):
        time_diff = arrow.get(expected_ended) - arrow.utcnow()

        return time_diff.seconds + random.randint(10, 20)

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(4),
        wait=tenacity.wait_random_exponential(multiplier=1, max=60),
        reraise=True
    )
    def sock_thread(self, url='https://sock-lok-live.leagueofkingdoms.com/socket.io/'):
        """
        websocket connection of the kingdom
        :return:
        """
        sio = socketio.Client(reconnection=False, logger=builtin_logger, engineio_logger=builtin_logger)

        @sio.on('/building/update')
        def on_building_update(data):
            logger.info(f'on_building_update: {data}')
            buildings = self.kingdom_enter.get('kingdom', {}).get('buildings', [])

            if not buildings:
                return

            self.kingdom_enter['kingdom']['buildings'] = [
                                                             building for building in buildings if
                                                             building.get('position') != data.get('position')
                                                         ] + [data]

            return

        sio.connect(url, transports=["websocket"])

        sio.emit('/kingdom/enter', {'token': self.access_token})

        sio.wait()

    def socf_thread(self):
        """
        websocket connection of the field
        :return:
        """
        pass

    def alliance_helper(self):
        """
        帮助联盟
        :return:
        """
        self.api.alliance_help_all()

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

    def quest_monitor(self):
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
            threading.Thread(target=self.quest_monitor).start()
            return

        quest_list_daily = self.api.quest_list_daily().get('dailyQuest')

        # daily quest(max 5)
        if len([self.api.quest_claim_daily(q) for q in quest_list_daily.get('quests') if
                q.get('status') == STATUS_FINISHED]) >= 5:
            # 若五个均为已完成, 则翻页
            threading.Thread(target=self.quest_monitor).start()
            return

        # daily quest reward
        [self.api.quest_claim_daily_level(q) for q in quest_list_daily.get('rewards') if
         q.get('status') == STATUS_FINISHED]

        logger.info('所有任务奖励领取完毕, 等待一小时')
        threading.Timer(3600, self.quest_monitor).start()
        return

    def building_farmer(self, task_code=TASK_CODE_SILVER_HAMMER):
        """
        building farmer
        :param task_code:
        :return:
        """
        current_tasks = self.api.kingdom_task_all().get('kingdomTasks', [])

        worker_used = [t for t in current_tasks if t.get('code') == task_code]

        if worker_used:
            threading.Timer(
                self.calc_time_diff_in_seconds(worker_used[0].get('expectedEnded')),
                self.building_farmer,
                [task_code]
            ).start()
            return

        buildings = self.kingdom_enter.get('kingdom', {}).get('buildings', [])

        if not buildings:
            logger.warning('没有可以升级的建筑')
            return

        buildings = filter(
            lambda b:
            b.get('position') not in BUILDING_UPGRADE_BLACKLIST and
            b.get('state') == BUILDING_STATE_NORMAL,
            buildings
        )
        building_sorted_by_level = sorted(buildings, key=lambda x: x.get('level'))
        building_position_lt_100 = [b for b in building_sorted_by_level if b.get('position') < 100]
        building_position_gt_100 = [b for b in building_sorted_by_level if b.get('position') > 100]

        for each_building in building_position_gt_100 + building_position_lt_100:
            try:
                res = self.api.kingdom_building_upgrade(each_building)
            except OtherException as error_code:
                if str(error_code) == 'full_task':
                    logger.warning('任务已满, 可能是因为没有黄金工人, 线程结束')
                    return

                logger.info(f'建筑升级失败, 尝试下一个建筑, 当前建筑: {each_building}')
                time.sleep(random.randint(1, 3))
                continue

            threading.Timer(
                self.calc_time_diff_in_seconds(res.get('newTask').get('expectedEnded')),
                self.building_farmer,
                [task_code]
            ).start()
            return

        logger.info('没有可以升级的建筑, 等待两小时')
        threading.Timer(2 * 3600, self.building_farmer, [task_code]).start()
        return

    def academy_farmer(self, to_max_level=False):
        """
        research farmer
        :param to_max_level:
        :return:
        """
        max_level_flag = 'max_level' if to_max_level else 'minimum_required_level'

        current_tasks = self.api.kingdom_task_all().get('kingdomTasks', [])

        worker_used = [t for t in current_tasks if t.get('code') == TASK_CODE_ACADEMY]

        if worker_used:
            if worker_used[0].get('status') != STATUS_CLAIMED:
                threading.Timer(
                    self.calc_time_diff_in_seconds(worker_used[0].get('expectedEnded')),
                    self.academy_farmer,
                    [to_max_level]
                ).start()
                return

            # 如果已完成, 则领取奖励并继续
            self.api.kingdom_task_claim(POSITION_ACADEMY)

        current_researches = self.api.kingdom_academy_research_list().get('researches', [])

        for category_name, each_category in RESEARCH_CODE.items():
            logger.info(f'开始 {category_name} 分类下的研究')
            for each_research in each_category:
                current_research = [each for each in current_researches if
                                    each.get('code') == each_research.get('code')]

                if current_research and current_research[0].get('level') >= each_research.get(max_level_flag):
                    continue

                try:
                    res = self.api.kingdom_academy_research(each_research)
                except OtherException as error_code:
                    if str(error_code) == 'not_enough_condition':
                        logger.warning(f'分类 {category_name} 下的研究已达到目前可升级的最大等级, 尝试下一个分类')
                        break

                    logger.info(f'研究升级失败, 尝试下一个研究, 当前研究: {each_research}')
                    time.sleep(random.randint(1, 3))
                    continue

                threading.Timer(
                    self.calc_time_diff_in_seconds(res.get('newTask').get('expectedEnded')),
                    self.academy_farmer,
                    [to_max_level]
                ).start()
                return

        logger.info('没有可以升级的研究, 等待两小时')
        threading.Timer(2 * 3600, self.academy_farmer, [to_max_level]).start()
        return

    def free_chest_farmer(self, _type=0):
        """
        领取免费宝箱
        :return:
        """
        try:
            res = self.api.item_free_chest(_type)
        except OtherException as error_code:
            if str(error_code) == 'free_chest_not_yet':
                logger.info('免费宝箱还没有开启, 等待两小时')
                threading.Timer(2 * 3600, self.free_chest_farmer).start()
                return

            raise

        next_gold = arrow.get(res.get('freeChest', {}).get('gold', {}).get('next'))
        next_silver = arrow.get(res.get('freeChest', {}).get('silver', {}).get('next'))

        if next_gold < next_silver:
            threading.Timer(self.calc_time_diff_in_seconds(next_gold), self.free_chest_farmer, [1]).start()
        else:
            threading.Timer(self.calc_time_diff_in_seconds(next_silver), self.free_chest_farmer, [0]).start()

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
        research_list = self.api.alliance_research_list()

        code = research_list.get('recommendResearch')

        if not code:
            code = 31101003  # 骑兵攻击力 1

        try:
            self.api.alliance_research_donate_all(code)
        except OtherException:
            pass

    def captcha_solver(self):
        captcha = Image.open(io.BytesIO(self.api.auth_captcha().content))
        captcha.save('captcha4.png')


def main(token):
    farmer = LokFarmer(token)

    schedule.every(120).to(200).minutes.do(farmer.alliance_helper)
    schedule.every(40).to(80).minutes.do(farmer.harvester)
    schedule.every(180).to(240).minutes.do(farmer.vip_chest_claim)
    schedule.every(120).to(240).minutes.do(farmer.use_resource_in_item_list)
    schedule.every(120).to(240).minutes.do(farmer.alliance_farmer)

    threading.Thread(target=farmer.sock_thread).start()

    threading.Thread(target=farmer.free_chest_farmer).start()

    threading.Thread(target=farmer.quest_monitor).start()

    threading.Thread(target=farmer.building_farmer, args=(TASK_CODE_SILVER_HAMMER,)).start()
    threading.Thread(target=farmer.building_farmer, args=(TASK_CODE_GOLD_HAMMER,)).start()

    threading.Thread(target=farmer.academy_farmer).start()

    schedule.run_all()

    # exit()

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    fire.Fire(main)
