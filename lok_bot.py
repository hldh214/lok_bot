import io
import json
import random
import threading
import time

import arrow
import fire
import httpx
import ratelimit
import schedule
import tenacity

from loguru import logger
from PIL import Image

# 任务状态
STATUS_PENDING = 1  # 未完成任务
STATUS_FINISHED = 2  # 已完成待领取奖励
STATUS_CLAIMED = 3  # 已领取奖励

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

RESEARCH_CODE_BATTLE = 30101001
RESEARCH_CODE_FARM = 30102001

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
    ITEM_CODE_FOOD_500K, ITEM_CODE_FOOD_1M,

    ITEM_CODE_LUMBER_1K, ITEM_CODE_LUMBER_5K, ITEM_CODE_LUMBER_10K, ITEM_CODE_LUMBER_50K, ITEM_CODE_LUMBER_100K,
    ITEM_CODE_LUMBER_500K, ITEM_CODE_LUMBER_1M,

    ITEM_CODE_STONE_1K, ITEM_CODE_STONE_5K, ITEM_CODE_STONE_10K, ITEM_CODE_STONE_50K, ITEM_CODE_STONE_100K,
    ITEM_CODE_STONE_500K, ITEM_CODE_STONE_1M,

    ITEM_CODE_GOLD_1K, ITEM_CODE_GOLD_5K, ITEM_CODE_GOLD_10K, ITEM_CODE_GOLD_50K, ITEM_CODE_GOLD_100K,
    ITEM_CODE_GOLD_500K, ITEM_CODE_GOLD_1M,
)


class ApiException(Exception):
    pass


class NoAuthException(ApiException):
    pass


class NeedCaptchaException(ApiException):
    pass


class DuplicatedException(ApiException):
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
            base_url='https://api-lok-live.leagueofkingdoms.com/api/'
        )

    @tenacity.retry(
        wait=tenacity.wait_random_exponential(multiplier=1, max=60),
        retry=tenacity.retry_if_exception_type((
                httpx.HTTPError,  # general http error
                ratelimit.RateLimitException,  # client-side rate limiter
                DuplicatedException  # server-side rate limiter
        )),
        reraise=True
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
    research_code_blacklist = set()

    def __init__(self, access_token):
        self.kingdom_enter = {}
        self.kingdom_task_all = {}
        self.api = LokBotApi(access_token)

        self.refresh_kingdom_enter()
        self.refresh_kingdom_task_all()

    @staticmethod
    def calc_time_diff_in_seconds(expected_ended):
        time_diff = arrow.get(expected_ended) - arrow.utcnow()

        return time_diff.seconds + random.randint(10, 20)

    def refresh_kingdom_enter(self):
        self.kingdom_enter = self.api.kingdom_enter()

        captcha = self.kingdom_enter.get('captcha')
        if captcha and captcha.get('next'):
            logger.critical('需要验证码: {}'.format(captcha.get('next')))

    def refresh_kingdom_task_all(self):
        self.kingdom_task_all = self.api.kingdom_task_all()

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

    def building_farmer(self, refresh=False, task_code=TASK_CODE_SILVER_HAMMER):
        """
        building farmer
        :return:
        """
        if refresh:
            self.refresh_kingdom_task_all()
            self.refresh_kingdom_enter()

        current_tasks = self.kingdom_task_all.get('kingdomTasks', [])

        worker_used = [t for t in current_tasks if t.get('code') == task_code]

        if worker_used:
            threading.Timer(
                self.calc_time_diff_in_seconds(worker_used[0].get('expectedEnded')),
                self.building_farmer,
                [True, task_code]
            ).start()
            return

        buildings = self.kingdom_enter.get('kingdom', {}).get('buildings', [])

        if not buildings:
            logger.warning('没有可以升级的建筑')
            return

        buildings = filter(lambda b: b.get('position') not in BUILDING_UPGRADE_BLACKLIST, buildings)
        building_sorted_by_level = sorted(buildings, key=lambda x: x.get('level'))

        for each_building in building_sorted_by_level:
            try:
                res = self.api.kingdom_building_upgrade(each_building)
            except OtherException:
                logger.info(f'建筑升级失败, 尝试下一个建筑, 当前建筑: {each_building}')
                time.sleep(random.randint(1, 3))
                continue

            threading.Timer(
                self.calc_time_diff_in_seconds(res.get('newTask').get('expectedEnded')),
                self.building_farmer,
                [True, task_code]
            ).start()
            return

        logger.info('没有可以升级的建筑, 等待两小时')
        threading.Timer(2 * 3600, self.building_farmer, [True, task_code]).start()
        return

    def academy_farmer(self, refresh=False):
        """
        research farmer
        :param refresh:
        :return:
        """
        if refresh:
            self.refresh_kingdom_task_all()
            self.refresh_kingdom_enter()

        current_tasks = self.kingdom_task_all.get('kingdomTasks', [])

        worker_used = [t for t in current_tasks if t.get('code') == TASK_CODE_ACADEMY]

        if worker_used:
            if worker_used[0].get('status') != STATUS_CLAIMED:
                threading.Timer(
                    self.calc_time_diff_in_seconds(worker_used[0].get('expectedEnded')),
                    self.academy_farmer,
                    [True]
                ).start()
                return

            # 如果已完成, 则领取奖励并继续
            self.api.kingdom_task_claim(POSITION_ACADEMY)

        researches = self.api.kingdom_academy_research_list().get('researches', [])

        if not researches:
            logger.warning('没有可以研究的科技')
            return

        research_sorted_by_level = sorted(
            # filter(lambda x: x.get('code') >= RESEARCH_CODE_FARM, researches),
            researches,
            key=lambda x: x.get('level')
        )

        for each_research in research_sorted_by_level:
            if each_research.get('code') in self.research_code_blacklist:
                continue

            try:
                res = self.api.kingdom_academy_research(each_research)
            except OtherException as error_code:
                if str(error_code) in ('max_level',):
                    self.research_code_blacklist.add(each_research.get('code'))

                logger.info(f'研究升级失败, 尝试下一个研究, 当前研究: {each_research}')
                time.sleep(random.randint(1, 3))
                continue

            threading.Timer(
                self.calc_time_diff_in_seconds(res.get('newTask').get('expectedEnded')),
                self.academy_farmer,
                [True]
            ).start()
            return

        logger.info('没有可以升级的研究, 等待两小时')
        threading.Timer(2 * 3600, self.academy_farmer, [True]).start()
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


def main(token, building_farmer=True, academy_farmer=False):
    # todo: integrate with websockets and live update for "kingdom_enter"
    farmer = LokFarmer(token)

    schedule.every(120).to(200).minutes.do(farmer.alliance_helper)
    schedule.every(40).to(80).minutes.do(farmer.harvester)
    schedule.every(180).to(240).minutes.do(farmer.vip_chest_claim)
    schedule.every(120).to(240).minutes.do(farmer.use_resource_in_item_list)
    schedule.every(120).to(240).minutes.do(farmer.alliance_farmer)

    threading.Thread(target=farmer.free_chest_farmer).start()

    threading.Thread(target=farmer.quest_monitor).start()

    if building_farmer:
        threading.Thread(target=farmer.building_farmer).start()

    if academy_farmer:
        threading.Thread(target=farmer.academy_farmer).start()

    # schedule.run_all()
    # exit()

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    fire.Fire(main)
