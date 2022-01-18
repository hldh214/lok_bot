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

# 任务状态
STATUS_PENDING = 1  # 未完成任务
STATUS_FINISHED = 2  # 已完成待领取奖励
STATUS_CLAIMED = 3  # 已领取奖励

# 建筑类型 code
CODE_CORN = 40100202  # 玉米
CODE_TIMBER = 40100203  # 木材
CODE_STONE = 40100204  # 石材
CODE_COIN = 40100205  # 黄金
CODE_ACADEMY = 40100105  # 学院
HARVESTABLE_CODE = [CODE_CORN, CODE_TIMBER, CODE_STONE, CODE_COIN]

# 任务类型 code
TASK_CODE_SILVER_HAMMER = 1  # 免费建筑工
TASK_CODE_GOLD_HAMMER = 8  # 黄金建筑工
TASK_CODE_CAMP = 3  # 军营
TASK_CODE_ACADEMY = 6  # 学院

# 建筑位置 position
POSITION_ACADEMY = 5  # 学院
POSITION_UNION = 7  # 联盟中心

BUILDING_UPGRADE_BLACKLIST = (POSITION_UNION,)

RESEARCH_CODE_BATTLE = 30101001  # 战斗
RESEARCH_CODE_FARM = 30102001  # 生产

ITEM_CODE_CORN_1K = 10101013  # 1K 玉米
ITEM_CODE_CORN_5K = 10101014  # 5K 玉米
ITEM_CODE_CORN_10K = 10101015  # 10K 玉米
ITEM_CODE_CORN_50K = 10101016  # 50K 玉米
ITEM_CODE_CORN_100K = 10101017  # 100K 玉米
ITEM_CODE_CORN_500K = 10101018  # 500K 玉米
ITEM_CODE_CORN_1M = 10101019  # 1M 玉米

ITEM_CODE_TIMBER_1K = 10101022  # 1K 木材
ITEM_CODE_TIMBER_5K = 10101023  # 5K 木材
ITEM_CODE_TIMBER_10K = 10101024  # 10K 木材
ITEM_CODE_TIMBER_50K = 10101025  # 50K 木材
ITEM_CODE_TIMBER_100K = 10101026  # 100K 木材
ITEM_CODE_TIMBER_500K = 10101027  # 500K 木材
ITEM_CODE_TIMBER_1M = 10101028  # 1M 木材

ITEM_CODE_STONE_1K = 10101031  # 1K 石材
ITEM_CODE_STONE_5K = 10101032  # 5K 石材
ITEM_CODE_STONE_10K = 10101033  # 10K 石材
ITEM_CODE_STONE_50K = 10101034  # 50K 石材
ITEM_CODE_STONE_100K = 10101035  # 100K 石材
ITEM_CODE_STONE_500K = 10101036  # 500K 石材
ITEM_CODE_STONE_1M = 10101037  # 1M 石材

ITEM_CODE_COIN_1K = 10101040  # 1K 黄金
ITEM_CODE_COIN_5K = 10101041  # 5K 黄金
ITEM_CODE_COIN_10K = 10101042  # 10K 黄金
ITEM_CODE_COIN_50K = 10101043  # 50K 黄金
ITEM_CODE_COIN_100K = 10101044  # 100K 黄金
ITEM_CODE_COIN_500K = 10101045  # 500K 黄金
ITEM_CODE_COIN_1M = 10101046  # 1M 黄金

USABLE_ITEM_CODE_LIST = (
    ITEM_CODE_CORN_1K, ITEM_CODE_CORN_5K, ITEM_CODE_CORN_10K, ITEM_CODE_CORN_50K, ITEM_CODE_CORN_100K,
    ITEM_CODE_CORN_500K, ITEM_CODE_CORN_1M,

    ITEM_CODE_TIMBER_1K, ITEM_CODE_TIMBER_5K, ITEM_CODE_TIMBER_10K, ITEM_CODE_TIMBER_50K, ITEM_CODE_TIMBER_100K,
    ITEM_CODE_TIMBER_500K, ITEM_CODE_TIMBER_1M,

    ITEM_CODE_STONE_1K, ITEM_CODE_STONE_5K, ITEM_CODE_STONE_10K, ITEM_CODE_STONE_50K, ITEM_CODE_STONE_100K,
    ITEM_CODE_STONE_500K, ITEM_CODE_STONE_1M,

    ITEM_CODE_COIN_1K, ITEM_CODE_COIN_5K, ITEM_CODE_COIN_10K, ITEM_CODE_COIN_50K, ITEM_CODE_COIN_100K,
    ITEM_CODE_COIN_500K, ITEM_CODE_COIN_1M,
)


class ApiException(Exception):
    pass


class NoAuthException(ApiException):
    pass


class NeedCaptchaException(ApiException):
    pass


class OtherException(ApiException):
    pass


class LokBotApi:
    def __init__(self, access_token):
        self.opener = httpx.Client(
            headers={
                'accept': '*/*',
                'accept-encoding': 'gzip, deflate, br',
                'accept-language': 'zh-CN,zh;q=0.9',
                'origin': 'https://play.leagueofkingdoms.com',
                'referer': 'https://play.leagueofkingdoms.com',
                'sec-ch-ua': '" Not;A Brand";v="99", "Google Chrome";v="97", "Chromium";v="97"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-site',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/97.0.4692.71 Safari/537.36',
                'x-access-token': access_token
            },
            http2=True,
            base_url='https://api-lok-live.leagueofkingdoms.com/api/'
        )

    @tenacity.retry(
        wait=tenacity.wait_random_exponential(multiplier=1, max=60),
        retry=tenacity.retry_if_exception_type((httpx.HTTPError, ratelimit.RateLimitException)),
        reraise=True
    )
    @ratelimit.limits(calls=1, period=1)
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

        raise OtherException(response.text)

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

    def kingdom_vip_claim(self):
        """
        领取VIP奖励
        daily
        :return:
        """
        return self.post('kingdom/vip/claim')

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

        # daily vip chest claim
        vip_last_claim_time = self.kingdom_enter.get('kingdom', {}).get('vip', {}).get('lastClaimTime')
        vip_time_delta = arrow.now() - arrow.get(vip_last_claim_time)
        if vip_time_delta.days >= 1:
            self.api.kingdom_vip_claim()

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
        quest_list_daily = self.api.quest_list_daily().get('dailyQuest')

        [self.api.quest_claim(q) for q in quest_list.get('mainQuests') if q.get('status') == STATUS_FINISHED]
        [self.api.quest_claim(q) for q in quest_list.get('sideQuests') if q.get('status') == STATUS_FINISHED]
        [self.api.quest_claim_daily(q) for q in quest_list_daily.get('quests') if q.get('status') == STATUS_FINISHED]
        [self.api.quest_claim_daily_level(q) for q in quest_list_daily.get('rewards') if
         q.get('status') == STATUS_FINISHED]

    def building_farmer(self, refresh=False):
        """
        左侧任务 farmer
        :return:
        """
        if refresh:
            self.refresh_kingdom_task_all()
            self.refresh_kingdom_enter()

        current_tasks = self.kingdom_task_all.get('kingdomTasks', [])

        worker_used = [t for t in current_tasks if t.get('code') == TASK_CODE_SILVER_HAMMER]

        if worker_used:
            threading.Timer(
                self.calc_time_diff_in_seconds(worker_used[0].get('expectedEnded')),
                self.building_farmer,
                [True]
            ).start()
            return

        buildings = self.kingdom_enter.get('kingdom', {}).get('buildings', [])

        if not buildings:
            logger.warning('没有可以升级的建筑')
            return

        building_sort_by_level = sorted(
            [b for b in buildings if b.get('position') > 100],
            key=lambda x: x.get('level')
        )

        for each_building in building_sort_by_level:
            try:
                res = self.api.kingdom_building_upgrade(each_building)
            except OtherException:
                logger.warning(f'建筑升级失败, 尝试下一个建筑, 当前建筑: {each_building}')
                time.sleep(random.randint(1, 3))
                continue

            threading.Timer(
                self.calc_time_diff_in_seconds(res.get('newTask').get('expectedEnded')),
                self.building_farmer,
                [True]
            ).start()
            return

        logger.warning('没有可以升级的建筑, 等待两小时')
        threading.Timer(2 * 3600, self.building_farmer, [True]).start()
        return

    def academy_farmer(self, refresh=False):
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

        lowest_level_research = sorted(
            filter(lambda x: x.get('code') >= RESEARCH_CODE_FARM, researches),
            key=lambda x: x.get('level')
        )[0]
        res = self.api.kingdom_academy_research(lowest_level_research)
        threading.Timer(
            self.calc_time_diff_in_seconds(res.get('newTask').get('expectedEnded')),
            self.academy_farmer,
            [True]
        ).start()

    def free_chest(self):
        """
        领取免费宝箱
        :return:
        """
        try:
            self.api.item_free_chest()
        except OtherException:
            return

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


def main(token):
    # todo: integrate with websockets and live update for "kingdom_enter"
    farmer = LokFarmer(token)

    schedule.every(60).to(120).minutes.do(farmer.alliance_helper)
    schedule.every(30).to(60).minutes.do(farmer.harvester)
    schedule.every(60).to(120).minutes.do(farmer.quest_monitor)
    schedule.every(120).to(240).minutes.do(farmer.free_chest)

    # schedule.every(120).to(240).minutes.do(farmer.use_resource_in_item_list)

    threading.Thread(target=farmer.building_farmer).start()
    threading.Thread(target=farmer.academy_farmer).start()

    # schedule.run_all()
    # exit()

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    fire.Fire(main)
