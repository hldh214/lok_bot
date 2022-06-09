import base64
import json

import httpx
import ratelimit
import tenacity

import lokbot.enum
from lokbot.exceptions import *
from lokbot import logger

BASE64ENCODE_URL_WHITELIST = (
    'kingdom/enter',
    'auth/setDeviceInfo',
    'chat/logs',
    'item/list',
    'mail/claim/all',
    'field/march/info',

    'kingdom/wall/info',
    'kingdom/treasure/list',
    'kingdom/task/claim',
    'kingdom/task/all',
    'kingdom/wall/repair',
    'kingdom/profile/troops',
    'kingdom/vip/info',
    'kingdom/arcademy/research',
    'kingdom/arcademy/research/list',
    'kingdom/caravan/list',
    'kingdom/caravan/buy',
    'kingdom/treasure/equip',
    'kingdom/treasure/page',
    'kingdom/building/build',
    'kingdom/barrack/train',

    'quest/main',
    'quest/claim/daily',
    'quest/claim/daily/level',
    'quest/list',
    'quest/list/daily',

    'event/list',
    'event/info',
    'event/claim',
    'event/cvc/open',
    'event/roulette/open',

    'pkg/recommend',
    'pkg/list',

    'alliance/help/all',
    'alliance/research/list',
    'alliance/research/donateAll',
    'alliance/research/donate',
    'alliance/research/info',
    'alliance/shop/list',
    'alliance/shop/buy',
    'alliance/join',
)


class LokBotApi:
    def __init__(self, access_token, captcha_solver_config, request_callback=None):
        self.opener = httpx.Client(
            headers={
                'User-Agent': 'BestHTTP',
                'x-access-token': access_token
            },
            http2=True,
            base_url=lokbot.enum.API_BASE_URL
        )
        self.request_callback = request_callback

        self.captcha_solver = None
        if 'ttshitu' in captcha_solver_config:
            from lokbot.captcha_solver import Ttshitu
            self.captcha_solver = Ttshitu(**captcha_solver_config['ttshitu'])

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(4),
        wait=tenacity.wait_random_exponential(multiplier=1, max=60),
        # general http error or json decode error
        retry=tenacity.retry_if_exception_type((httpx.HTTPError, json.JSONDecodeError)),
        reraise=True
    )
    @tenacity.retry(
        wait=tenacity.wait_fixed(2),
        retry=tenacity.retry_if_exception_type(DuplicatedException),  # server-side rate limiter(wait 2s)
    )
    @tenacity.retry(
        wait=tenacity.wait_fixed(3600),
        retry=tenacity.retry_if_exception_type(ExceedLimitPacketException),  # server-side rate limiter(wait 1h)
    )
    @tenacity.retry(
        wait=tenacity.wait_fixed(1),
        retry=tenacity.retry_if_exception_type(ratelimit.RateLimitException),
    )
    @ratelimit.limits(calls=1, period=0.1)
    def post(self, url, json_data=None):
        if json_data is None:
            json_data = {}

        post_data = json.dumps(json_data)
        if url not in BASE64ENCODE_URL_WHITELIST:
            post_data = base64.b64encode(post_data.encode()).decode()

        response = self.opener.post(url, data={'json': post_data})

        log_data = {
            'url': url,
            'data': json_data,
            'elapsed': response.elapsed.total_seconds(),
        }

        try:
            if url not in BASE64ENCODE_URL_WHITELIST and response.text[0] != '{':
                json_response = json.loads(base64.b64decode(response.text).decode())
            else:
                json_response = response.json()
        except json.JSONDecodeError:
            log_data.update({'res': response.text})
            logger.error(log_data)

            raise

        log_data.update({'res': json_response})

        logger.debug(json.dumps(log_data))

        if json_response.get('result'):
            if callable(self.request_callback):
                self.request_callback(json_response)

            return json_response

        err = json_response.get('err')
        code = err.get('code')

        if code == 'no_auth':
            raise NoAuthException()

        if code == 'need_captcha':
            if not self.captcha_solver:
                raise NeedCaptchaException()

            self._solve_captcha()

            raise DuplicatedException()

        if code == 'duplicated':
            raise DuplicatedException()

        if code == 'exceed_limit_packet':
            raise ExceedLimitPacketException()

        raise OtherException(code)

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(4),
        wait=tenacity.wait_random_exponential(multiplier=1, max=60)
    )
    def _solve_captcha(self):
        def get_picture_base64_func():
            return base64.b64encode(self.auth_captcha().content).decode()

        def captcha_confirm_func(_captcha):
            res = self.auth_captcha_confirm(_captcha)

            return res.get('valid')

        if not self.captcha_solver.solve(get_picture_base64_func, captcha_confirm_func):
            raise tenacity.TryAgain()

    def auth_captcha(self):
        return self.opener.get('auth/captcha')

    @tenacity.retry(
        wait=tenacity.wait_fixed(1),
        retry=tenacity.retry_if_exception_type(ratelimit.RateLimitException),
    )
    @ratelimit.limits(calls=1, period=2)
    def auth_captcha_confirm(self, value):
        return self.post('auth/captcha/confirm', {'value': value})

    def auth_connect(self):
        res = self.post('auth/connect')

        self.opener.headers['x-access-token'] = res['token']

        return res

    def auth_set_device_info(self, device_info):
        return self.post('auth/setDeviceInfo', {'deviceInfo': device_info})

    def alliance_research_list(self):
        return self.post('alliance/research/list')

    def alliance_research_donate_all(self, code):
        return self.post('alliance/research/donateAll', {'code': code})

    def alliance_shop_list(self):
        return self.post('alliance/shop/list')

    def alliance_shop_buy(self, code, amount):
        return self.post('alliance/shop/buy', {'code': code, 'amount': amount})

    def alliance_gift_claim_all(self):
        return self.post('alliance/gift/claim/all')

    def chat_logs(self, chat_channel):
        return self.post('chat/logs', {'chatChannel': chat_channel})

    def quest_main(self):
        return self.post('quest/main')

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

    @tenacity.retry(
        wait=tenacity.wait_fixed(1),
        retry=tenacity.retry_if_exception_type(ratelimit.RateLimitException),
    )
    @ratelimit.limits(calls=1, period=1)
    def quest_claim(self, quest):
        """
        领取任务奖励
        :param quest:
        :return:
        """
        return self.post('quest/claim', {'questId': quest.get('_id'), 'code': quest.get('code')})

    @tenacity.retry(
        wait=tenacity.wait_fixed(1),
        retry=tenacity.retry_if_exception_type(ratelimit.RateLimitException),
    )
    @ratelimit.limits(calls=1, period=1)
    def quest_claim_daily(self, quest):
        """
        领取日常任务奖励
        :param quest:
        :return:
        """
        return self.post('quest/claim/daily', {'questId': quest.get('_id'), 'code': quest.get('code')})

    @tenacity.retry(
        wait=tenacity.wait_fixed(1),
        retry=tenacity.retry_if_exception_type(ratelimit.RateLimitException),
    )
    @ratelimit.limits(calls=1, period=4)
    def quest_claim_daily_level(self, reward):
        """
        领取日常任务上方进度条奖励
        :param reward:
        :return:
        """
        return self.post('quest/claim/daily/level', {'level': reward.get('level')})

    def pkg_recommend(self):
        return self.post('pkg/recommend')

    def pkg_list(self):
        return self.post('pkg/list')

    def event_roulette_open(self):
        return self.post('event/roulette/open')

    def event_cvc_open(self):
        return self.post('event/cvc/open')

    def event_list(self):
        """
        获取活动列表
        :return:
        """
        return self.post('event/list')

    @tenacity.retry(
        wait=tenacity.wait_fixed(1),
        retry=tenacity.retry_if_exception_type(ratelimit.RateLimitException),
    )
    @ratelimit.limits(calls=1, period=2)
    def event_info(self, root_event_id):
        """
        获取活动信息
        :return:
        """
        return self.post('event/info', {'rootEventId': root_event_id})

    @tenacity.retry(
        wait=tenacity.wait_fixed(1),
        retry=tenacity.retry_if_exception_type(ratelimit.RateLimitException),
    )
    @ratelimit.limits(calls=1, period=4)
    def event_claim(self, event_id, event_target_id, code):
        """
        领取活动奖励
        :return:
        """
        return self.post('event/claim', {'eventId': event_id, 'eventTargetId': event_target_id, 'code': code})

    def train_troop(self, troop_code, amount):
        return self.post('kingdom/barrack/train', {'troopCode': troop_code, 'amount': amount})

    def kingdom_wall_info(self):
        return self.post('kingdom/wall/info')

    def kingdom_wall_repair(self):
        return self.post('kingdom/wall/repair')

    def kingdom_treasure_list(self):
        return self.post('kingdom/treasure/list')

    def kingdom_enter(self):
        """
        获取基础信息
        :return:
        """
        res = self.post('kingdom/enter')

        captcha = res.get('captcha')
        if captcha and captcha.get('next'):
            if not self.captcha_solver:
                raise NeedCaptchaException()

            self._solve_captcha()

        return res

    def kingdom_task_all(self):
        """
        获取当前任务执行状态(左侧建筑x2/招募/研究)
        :return:
        """
        return self.post('kingdom/task/all')

    @tenacity.retry(
        wait=tenacity.wait_fixed(1),
        retry=tenacity.retry_if_exception_type(ratelimit.RateLimitException),
    )
    @ratelimit.limits(calls=1, period=4)
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

    def kingdom_hospital_wounded(self):
        return self.post('kingdom/hospital/wounded')

    @tenacity.retry(
        wait=tenacity.wait_fixed(1),
        retry=tenacity.retry_if_exception_type(ratelimit.RateLimitException),
    )
    @ratelimit.limits(calls=1, period=4)
    def kingdom_resource_harvest(self, position):
        """
        收获资源
        :param position:
        :return:
        """
        return self.post('kingdom/resource/harvest', {'position': position})

    @tenacity.retry(
        wait=tenacity.wait_fixed(1),
        retry=tenacity.retry_if_exception_type(ratelimit.RateLimitException),  # client-side rate limiter
    )
    @ratelimit.limits(calls=1, period=6)
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

    @tenacity.retry(
        wait=tenacity.wait_fixed(1),
        retry=tenacity.retry_if_exception_type(ratelimit.RateLimitException),
    )
    @ratelimit.limits(calls=1, period=6)
    def kingdom_building_build(self, building, instant=0):
        """
        建筑建造
        :param building:
        :param instant:
        :return:
        """
        return self.post('kingdom/building/build', {
            'position': building.get('position'),
            'buildingCode': building.get('code'),
            'instant': instant
        })

    @tenacity.retry(
        wait=tenacity.wait_fixed(1),
        retry=tenacity.retry_if_exception_type(ratelimit.RateLimitException),
    )
    @ratelimit.limits(calls=1, period=6)
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

    def kingdom_caravan_list(self):
        return self.post('kingdom/caravan/list')

    @tenacity.retry(
        wait=tenacity.wait_fixed(1),
        retry=tenacity.retry_if_exception_type(ratelimit.RateLimitException),
    )
    @ratelimit.limits(calls=1, period=4)
    def kingdom_caravan_buy(self, caravan_item_id):
        return self.post('kingdom/caravan/buy', {'caravanItemId': caravan_item_id})

    def kingdom_profile_troops(self):
        return self.post('kingdom/profile/troops')

    def kingdom_vipshop_buy(self, code, amount):
        return self.post('kingdom/vipshop/buy', {'code': code, 'amount': amount})

    def alliance_help_all(self):
        """
        帮助全部
        :return:
        """
        return self.post('alliance/help/all')

    def alliance_recommend(self):
        """
        获取推荐的联盟, 配合加入联盟一起使用
        :return:
        """
        return self.post('alliance/recommend')

    def alliance_join(self, alliance_id):
        """
        加入联盟
        :return:
        """
        return self.post('alliance/join', {'allianceId': alliance_id})

    def item_list(self):
        """
        获取道具列表
        :return:
        """
        return self.post('item/list')

    @tenacity.retry(
        wait=tenacity.wait_fixed(1),
        retry=tenacity.retry_if_exception_type(ratelimit.RateLimitException),
    )
    @ratelimit.limits(calls=1, period=4)
    def item_use(self, code, amount=1):
        """
        使用道具
        :param code:
        :param amount:
        :return:
        """
        return self.post('item/use', {'code': code, 'amount': amount})

    @tenacity.retry(
        wait=tenacity.wait_fixed(1),
        retry=tenacity.retry_if_exception_type(ratelimit.RateLimitException),
    )
    @ratelimit.limits(calls=1, period=4)
    def item_free_chest(self, _type=0):
        """
        领取免费宝箱
        :type _type: int 0: silver 1: gold
        :return:
        """
        return self.post('item/freechest', {'type': _type})

    @tenacity.retry(
        wait=tenacity.wait_fixed(1),
        retry=tenacity.retry_if_exception_type(ratelimit.RateLimitException),
    )
    @ratelimit.limits(calls=1, period=2)
    def event_roulette_spin(self):
        """
        转轮抽奖
        daily
        :return:
        """
        return self.post('event/roulette/spin')

    def mail_list_check(self):
        return self.post('mail/list/check')

    @tenacity.retry(
        wait=tenacity.wait_fixed(1),
        retry=tenacity.retry_if_exception_type(ratelimit.RateLimitException),
    )
    @ratelimit.limits(calls=1, period=2)
    def mail_claim_all(self, category=1):
        return self.post('mail/claim/all', {'category': category})

    def field_worldmap_devrank(self):
        """
        Returns the land rank (length: 65535)
        level: 0~9 for lvl 1-10
        {"result": true, "lands": "000000011122334455 ..."}
        :return:
        """
        return self.post('field/worldmap/devrank')

    def field_march_info(self, data):
        return self.post('field/march/info', data)

    @tenacity.retry(
        wait=tenacity.wait_fixed(1),
        retry=tenacity.retry_if_exception_type(ratelimit.RateLimitException),
    )
    @ratelimit.limits(calls=1, period=4)
    def field_march_start(self, data):
        return self.post('field/march/start', data)


def get_version():
    first = 1
    second = 1419
    third = httpx.get('https://play.leagueofkingdoms.com/json/version-live.json').json().get('table')
    fourth = httpx.get(f'https://play.leagueofkingdoms.com/bundles/webgl/kingdominfo_{second}').json()
    fourth = [each for each in fourth if each.get('name') == 'ui'][0].get('version')

    return f'{first}.{second}.{third}.{fourth}'
