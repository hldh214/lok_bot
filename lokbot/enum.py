import json

from lokbot import project_root

API_BASE_URL = 'https://api-lok-live.leagueofkingdoms.com/api/'

# 刚进游戏
TUTORIAL_CODE_INTRO = 'Intro'
# 完成改名字主线后, 弹出 "学徒的板条箱 $0.99" 购买按钮
TUTORIAL_CODE_START = 'TutorialStart'

# 任务状态
STATUS_PENDING = 1  # 未完成任务
STATUS_FINISHED = 2  # 已完成待领取奖励
STATUS_CLAIMED = 3  # 已领取奖励

# 任务类型 code
TASK_CODE_SILVER_HAMMER = 1  # 免费建筑工
TASK_CODE_GOLD_HAMMER = 8  # 黄金建筑工
TASK_CODE_CAMP = 3  # 军营
TASK_CODE_ACADEMY = 6  # 学院

BUILDING_STATE_NORMAL = 1  # 正常
BUILDING_STATE_UPGRADING = 2  # 升级中

# 龙巢状态
DRAGO_LAIR_STATUS_STANDBY = 1  # 待命中
DRAGO_LAIR_STATUS_DEFENDING = 2  # 防守中
DRAGO_LAIR_STATUS_ATTACKING = 3  # 出击中

# 聊天: 频道类型
CHAT_CHANNEL_WORLD = 1  # 世界频道
CHAT_CHANNEL_ALLIANCE = 2  # 联盟频道

# 聊天: 消息类型
CHAT_TYPE_TEXT = 1  # 文字
CHAT_TYPE_LOC = 2  # 位置
CHAT_TYPE_STICKER = 7  # 贴纸

BUILDING_POSITION_MAP = {
    'academy': 5,
    'castle': 1,
    'hall_of_alliance': 7,
    'hospital': 6,
    'storage': 2,
    'trading_post': 9,
    'treasure_house': 4,
    'wall': 8,
    'watch_tower': 3,
}

BUILDING_CODE_MAP = {
    'academy': 40100105,
    'barrack': 40100201,
    'castle': 40100101,
    'farm': 40100202,
    'gold_mine': 40100205,
    'hall_of_alliance': 40100107,
    'hospital': 40100106,
    'lumber_camp': 40100203,
    'quarry': 40100204,
    'storage': 40100102,
    'trading_post': 40100109,
    'treasure_house': 40100104,
    'wall': 40100108,
    'watch_tower': 40100103,
}

BUILD_POSITION_UNLOCK_MAP = {
    # level: (pos1, pos2, ..., posN)
    0: (
        {'position': 104, 'code': BUILDING_CODE_MAP['farm']},
        {'position': 105, 'code': BUILDING_CODE_MAP['barrack']},
        {'position': 106, 'code': BUILDING_CODE_MAP['lumber_camp']},
        {'position': 107, 'code': BUILDING_CODE_MAP['quarry']},
        {'position': 108, 'code': BUILDING_CODE_MAP['gold_mine']},
        {'position': 109, 'code': BUILDING_CODE_MAP['farm']},
        {'position': 110, 'code': BUILDING_CODE_MAP['barrack']},
        {'position': 111, 'code': BUILDING_CODE_MAP['lumber_camp']},
    ),
    5: (
        {'position': 115, 'code': BUILDING_CODE_MAP['quarry']},
        {'position': 116, 'code': BUILDING_CODE_MAP['gold_mine']},
        {'position': 117, 'code': BUILDING_CODE_MAP['farm']},
        {'position': 118, 'code': BUILDING_CODE_MAP['barrack']},
    ),
    10: (
        {'position': 101, 'code': BUILDING_CODE_MAP['lumber_camp']},
        {'position': 102, 'code': BUILDING_CODE_MAP['quarry']},
        {'position': 103, 'code': BUILDING_CODE_MAP['gold_mine']},
        {'position': 114, 'code': BUILDING_CODE_MAP['farm']},
    ),
    15: (
        {'position': 112, 'code': BUILDING_CODE_MAP['barrack']},
        {'position': 113, 'code': BUILDING_CODE_MAP['lumber_camp']},
        {'position': 119, 'code': BUILDING_CODE_MAP['quarry']},
        {'position': 120, 'code': BUILDING_CODE_MAP['gold_mine']},
    ),
}

# 可收获的资源
HARVESTABLE_CODE = [
    BUILDING_CODE_MAP['farm'],
    BUILDING_CODE_MAP['lumber_camp'],
    BUILDING_CODE_MAP['quarry'],
    BUILDING_CODE_MAP['gold_mine']
]

ITEM_CODE_FOOD = 10100001
ITEM_CODE_LUMBER = 10100002
ITEM_CODE_STONE = 10100003
ITEM_CODE_GOLD = 10100004
ITEM_CODE_CRYSTAL = 10100005

ITEM_CODE_CRYSTAL_10 = 10101001
ITEM_CODE_CRYSTAL_100 = 10101002

ITEM_CODE_VIP_100 = 10101008

ITEM_CODE_FOOD_1K = 10101013
ITEM_CODE_FOOD_5K = 10101014
ITEM_CODE_FOOD_10K = 10101015
ITEM_CODE_FOOD_50K = 10101016
ITEM_CODE_FOOD_100K = 10101017
ITEM_CODE_FOOD_500K = 10101018
ITEM_CODE_FOOD_1M = 10101019
ITEM_CODE_FOOD_5M = 10101020
ITEM_CODE_FOOD_10M = 10101021

ITEM_CODE_LUMBER_1K = 10101022
ITEM_CODE_LUMBER_5K = 10101023
ITEM_CODE_LUMBER_10K = 10101024
ITEM_CODE_LUMBER_50K = 10101025
ITEM_CODE_LUMBER_100K = 10101026
ITEM_CODE_LUMBER_500K = 10101027
ITEM_CODE_LUMBER_1M = 10101028
ITEM_CODE_LUMBER_5M = 10101029
ITEM_CODE_LUMBER_10M = 10101030

ITEM_CODE_STONE_1K = 10101031
ITEM_CODE_STONE_5K = 10101032
ITEM_CODE_STONE_10K = 10101033
ITEM_CODE_STONE_50K = 10101034
ITEM_CODE_STONE_100K = 10101035
ITEM_CODE_STONE_500K = 10101036
ITEM_CODE_STONE_1M = 10101037
ITEM_CODE_STONE_5M = 10101038
ITEM_CODE_STONE_10M = 10101039

ITEM_CODE_GOLD_1K = 10101040
ITEM_CODE_GOLD_5K = 10101041
ITEM_CODE_GOLD_10K = 10101042
ITEM_CODE_GOLD_50K = 10101043
ITEM_CODE_GOLD_100K = 10101044
ITEM_CODE_GOLD_500K = 10101045
ITEM_CODE_GOLD_1M = 10101046
ITEM_CODE_GOLD_5M = 10101047
ITEM_CODE_GOLD_10M = 10101048

ITEM_CODE_FOOD_BOOST_8H = 10102001
ITEM_CODE_FOOD_BOOST_1D = 10102002
ITEM_CODE_LUMBER_BOOST_8H = 10102003
ITEM_CODE_LUMBER_BOOST_1D = 10102004
ITEM_CODE_STONE_BOOST_8H = 10102005
ITEM_CODE_STONE_BOOST_1D = 10102006
ITEM_CODE_GOLD_BOOST_8H = 10102007
ITEM_CODE_GOLD_BOOST_1D = 10102008

ITEM_CODE_GATHERING_BOOST_8H = 10102009
ITEM_CODE_GATHERING_BOOST_1D = 10102010

ITEM_CODE_GOLDEN_HAMMER = 10102023

ITEM_CODE_SILVER_CHEST = 10104024
ITEM_CODE_GOLD_CHEST = 10104025

ITEM_CODE_ALLIANCE_TELEPORT = 10104091

ITEM_CODE_RESOURCE_BOX_LV1 = 10104097
ITEM_CODE_RESOURCE_BOX_LV2 = 10104098
ITEM_CODE_RESOURCE_BOX_LV3 = 10104099
ITEM_CODE_RESOURCE_BOX_LV4 = 10104100
ITEM_CODE_SPEEDUP_BOX_LV1 = 10104101
ITEM_CODE_SPEEDUP_BOX_LV2 = 10104102
ITEM_CODE_SPEEDUP_BOX_LV3 = 10104103
ITEM_CODE_SPEEDUP_BOX_LV4 = 10104104

ITEM_CODE_T1_TROOPS = 10104130

ITEM_CODE_ORB_OF_PORTAL_PIECE = 10603001

ITEM_CODE_ACTION_POINTS_10 = 10101049
ITEM_CODE_ACTION_POINTS_20 = 10101050
ITEM_CODE_ACTION_POINTS_50 = 10101051
ITEM_CODE_ACTION_POINTS_100 = 10101052

ITEM_CODE_SPEEDUP_1M = 10103001
ITEM_CODE_SPEEDUP_5M = 10103002
ITEM_CODE_SPEEDUP_10M = 10103003
ITEM_CODE_SPEEDUP_30M = 10103004
ITEM_CODE_SPEEDUP_1H = 10103005
ITEM_CODE_SPEEDUP_3H = 10103006
ITEM_CODE_SPEEDUP_8H = 10103007
ITEM_CODE_SPEEDUP_1D = 10103008

ITEM_CODE_SPEEDUP_BUILDING_1M = 10103012
ITEM_CODE_SPEEDUP_BUILDING_5M = 10103013
ITEM_CODE_SPEEDUP_BUILDING_10M = 10103014
ITEM_CODE_SPEEDUP_BUILDING_30M = 10103015
ITEM_CODE_SPEEDUP_BUILDING_1H = 10103016
ITEM_CODE_SPEEDUP_BUILDING_3H = 10103017
ITEM_CODE_SPEEDUP_BUILDING_8H = 10103018
ITEM_CODE_SPEEDUP_BUILDING_1D = 10103019

ITEM_CODE_SPEEDUP_RESEARCH_1M = 10103022
ITEM_CODE_SPEEDUP_RESEARCH_5M = 10103023
ITEM_CODE_SPEEDUP_RESEARCH_10M = 10103024
ITEM_CODE_SPEEDUP_RESEARCH_30M = 10103025
ITEM_CODE_SPEEDUP_RESEARCH_1H = 10103026
ITEM_CODE_SPEEDUP_RESEARCH_3H = 10103027
ITEM_CODE_SPEEDUP_RESEARCH_8H = 10103028
ITEM_CODE_SPEEDUP_RESEARCH_1D = 10103029

ITEM_CODE_SPEEDUP_TRAIN_1M = 10103032
ITEM_CODE_SPEEDUP_TRAIN_5M = 10103033
ITEM_CODE_SPEEDUP_TRAIN_10M = 10103034
ITEM_CODE_SPEEDUP_TRAIN_30M = 10103035
ITEM_CODE_SPEEDUP_TRAIN_1H = 10103036
ITEM_CODE_SPEEDUP_TRAIN_3H = 10103037
ITEM_CODE_SPEEDUP_TRAIN_8H = 10103038
ITEM_CODE_SPEEDUP_TRAIN_1D = 10103039

ITEM_CODE_RECOVER_1M = 10103042
ITEM_CODE_RECOVER_5M = 10103043
ITEM_CODE_RECOVER_10M = 10103044
ITEM_CODE_RECOVER_30M = 10103045
ITEM_CODE_RECOVER_1H = 10103046
ITEM_CODE_RECOVER_3H = 10103047
ITEM_CODE_RECOVER_8H = 10103048
ITEM_CODE_RECOVER_1D = 10103049

ITEM_CODE_SPEEDUP_MAP = {
    'universal': {
        ITEM_CODE_SPEEDUP_1M: 60,
        ITEM_CODE_SPEEDUP_5M: 300,
        ITEM_CODE_SPEEDUP_10M: 600,
        ITEM_CODE_SPEEDUP_30M: 1800,
        ITEM_CODE_SPEEDUP_1H: 3600,
        ITEM_CODE_SPEEDUP_3H: 10800,
        ITEM_CODE_SPEEDUP_8H: 28800,
        ITEM_CODE_SPEEDUP_1D: 86400,
    },
    'building': {
        # item_code: seconds
        ITEM_CODE_SPEEDUP_BUILDING_1M: 60,
        ITEM_CODE_SPEEDUP_BUILDING_5M: 300,
        ITEM_CODE_SPEEDUP_BUILDING_10M: 600,
        ITEM_CODE_SPEEDUP_BUILDING_30M: 1800,
        ITEM_CODE_SPEEDUP_BUILDING_1H: 3600,
        ITEM_CODE_SPEEDUP_BUILDING_3H: 10800,
        ITEM_CODE_SPEEDUP_BUILDING_8H: 28800,
        ITEM_CODE_SPEEDUP_BUILDING_1D: 86400,
    },
    'research': {
        ITEM_CODE_SPEEDUP_RESEARCH_1M: 60,
        ITEM_CODE_SPEEDUP_RESEARCH_5M: 300,
        ITEM_CODE_SPEEDUP_RESEARCH_10M: 600,
        ITEM_CODE_SPEEDUP_RESEARCH_30M: 1800,
        ITEM_CODE_SPEEDUP_RESEARCH_1H: 3600,
        ITEM_CODE_SPEEDUP_RESEARCH_3H: 10800,
        ITEM_CODE_SPEEDUP_RESEARCH_8H: 28800,
        ITEM_CODE_SPEEDUP_RESEARCH_1D: 86400,
    },
    'train': {
        ITEM_CODE_SPEEDUP_TRAIN_1M: 60,
        ITEM_CODE_SPEEDUP_TRAIN_5M: 300,
        ITEM_CODE_SPEEDUP_TRAIN_10M: 600,
        ITEM_CODE_SPEEDUP_TRAIN_30M: 1800,
        ITEM_CODE_SPEEDUP_TRAIN_1H: 3600,
        ITEM_CODE_SPEEDUP_TRAIN_3H: 10800,
        ITEM_CODE_SPEEDUP_TRAIN_8H: 28800,
        ITEM_CODE_SPEEDUP_TRAIN_1D: 86400,
    },
    'recover': {
        ITEM_CODE_RECOVER_1M: 60,
        ITEM_CODE_RECOVER_5M: 300,
        ITEM_CODE_RECOVER_10M: 600,
        ITEM_CODE_RECOVER_30M: 1800,
        ITEM_CODE_RECOVER_1H: 3600,
        ITEM_CODE_RECOVER_3H: 10800,
        ITEM_CODE_RECOVER_8H: 28800,
        ITEM_CODE_RECOVER_1D: 86400,
    }
}

USABLE_ITEM_CODE_LIST = (
    ITEM_CODE_FOOD_1K, ITEM_CODE_FOOD_5K, ITEM_CODE_FOOD_10K, ITEM_CODE_FOOD_50K, ITEM_CODE_FOOD_100K,

    ITEM_CODE_LUMBER_1K, ITEM_CODE_LUMBER_5K, ITEM_CODE_LUMBER_10K, ITEM_CODE_LUMBER_50K, ITEM_CODE_LUMBER_100K,

    ITEM_CODE_STONE_1K, ITEM_CODE_STONE_5K, ITEM_CODE_STONE_10K, ITEM_CODE_STONE_50K, ITEM_CODE_STONE_100K,

    ITEM_CODE_GOLD_1K, ITEM_CODE_GOLD_5K, ITEM_CODE_GOLD_10K, ITEM_CODE_GOLD_50K, ITEM_CODE_GOLD_100K,

    ITEM_CODE_VIP_100,

    ITEM_CODE_T1_TROOPS,

    ITEM_CODE_CRYSTAL_100,

    ITEM_CODE_ACTION_POINTS_10, ITEM_CODE_ACTION_POINTS_20, ITEM_CODE_ACTION_POINTS_50, ITEM_CODE_ACTION_POINTS_100
)

BUYABLE_CARAVAN_ITEM_CODE_LIST = (
    ITEM_CODE_FOOD, ITEM_CODE_FOOD_1K, ITEM_CODE_FOOD_5K, ITEM_CODE_FOOD_10K, ITEM_CODE_FOOD_50K,
    ITEM_CODE_FOOD_100K, ITEM_CODE_FOOD_500K, ITEM_CODE_FOOD_1M, ITEM_CODE_FOOD_5M, ITEM_CODE_FOOD_10M,

    ITEM_CODE_LUMBER, ITEM_CODE_LUMBER_1K, ITEM_CODE_LUMBER_5K, ITEM_CODE_LUMBER_10K, ITEM_CODE_LUMBER_50K,
    ITEM_CODE_LUMBER_100K, ITEM_CODE_LUMBER_500K, ITEM_CODE_LUMBER_1M, ITEM_CODE_LUMBER_5M, ITEM_CODE_LUMBER_10M,

    ITEM_CODE_STONE, ITEM_CODE_STONE_1K, ITEM_CODE_STONE_5K, ITEM_CODE_STONE_10K, ITEM_CODE_STONE_50K,
    ITEM_CODE_STONE_100K, ITEM_CODE_STONE_500K, ITEM_CODE_STONE_1M, ITEM_CODE_STONE_5M, ITEM_CODE_STONE_10M,

    ITEM_CODE_GOLD, ITEM_CODE_GOLD_1K, ITEM_CODE_GOLD_5K, ITEM_CODE_GOLD_10K, ITEM_CODE_GOLD_50K,
    ITEM_CODE_GOLD_100K, ITEM_CODE_GOLD_500K, ITEM_CODE_GOLD_1M, ITEM_CODE_GOLD_5M, ITEM_CODE_GOLD_10M,
)

USABLE_BOOST_CODE_MAP = {
    'food': (ITEM_CODE_FOOD_BOOST_8H, ITEM_CODE_FOOD_BOOST_1D),
    'lumber': (ITEM_CODE_LUMBER_BOOST_8H, ITEM_CODE_LUMBER_BOOST_1D),
    'stone': (ITEM_CODE_STONE_BOOST_8H, ITEM_CODE_STONE_BOOST_1D),
    'gold': (ITEM_CODE_GOLD_BOOST_8H, ITEM_CODE_GOLD_BOOST_1D),
    'golden_hammer': (ITEM_CODE_GOLDEN_HAMMER,),
}

# {
#     "_id": "6229ece6a2c48f60ea4c0f20",
#     "loc": [
#         32,
#         293,
#         1979
#     ],
#     "level": 1,
#     "code": 20100101,
#     "param": {
#         "value": 50000 <- resources remain
#     },
#     "state": 1,
#     "expired": "2022-03-11T22:34:23.062Z"
# }
OBJECT_CODE_FARM = 20100101
OBJECT_CODE_LUMBER_CAMP = 20100102
OBJECT_CODE_QUARRY = 20100103
OBJECT_CODE_GOLD_MINE = 20100104
# {
#     "_id": "622aa43ba2c48f60ea531193",
#     "loc": [32,
#             1002,
#             1130],
#     "level": 3,
#     "code": 20100105,
#     "param": {
#         "value": 200
#     },
#     "state": 1,
#     "expired": "2022-03-12T13:39:31.786Z",
#     "occupied": {
#         "id": "621c10b7b975e73353393b54",
#         "targetValue": 200,
#         "moId": "622aa58b8f76db1734b15103",
#         "started": "2022-03-11T01:28:59.678Z",
#         "ended": "2022-03-11T04:05:51.678Z",
#         "shield": 0,
#         "skin": null,
#         "name": "Kobitan",
#         "worldId": 32,
#         "allianceId": "621c40b4c56f92266601578a",
#         "allianceTag": "HEHE"
#     }
# }
OBJECT_CODE_CRYSTAL_MINE = 20100105
OBJECT_CODE_DRAGON_SOUL_CAVERN = 20100106
# {
#     "_id": "622aa433a2c48f60ea530fed",
#     "loc": [
#         32,
#         302,
#         2047
#     ],
#     "level": 2,
#     "code": 20200101,
#     "param": {
#         "value": 5000 <- hp
#     },
#     "state": 1,
#     "expired": "2022-03-12T11:35:28.436Z"
# }
OBJECT_CODE_ORC = 20200101
OBJECT_CODE_SKELETON = 20200102
OBJECT_CODE_GOLEM = 20200103
OBJECT_CODE_GOBLIN = 20200104
# {
#     "_id": "622a1887a2c48f60ea4dc1a1",
#     "loc": [
#         32,
#         302,
#         2010
#     ],
#     "level": 1,
#     "code": 20200201,
#     "param": {
#         "value": 30000 <- hp
#     },
#     "state": 1,
#     "expired": "2022-03-11T10:32:01.895Z"
# }
OBJECT_CODE_DEATHKAR = 20200201
# {
#     "_id": "622174d8c6903c237b5d339e",
#     "loc": [
#         32,
#         304,
#         2038
#     ],
#     "level": 3,
#     "code": 20300101,
#     "occupied": {
#         "id": "621eee50a74093539dee2f91",
#         "started": "2022-03-04T02:09:28.458Z",
#         "skin": null,
#         "name": "lrdMX4",
#         "worldId": 32,
#         "allianceId": "621ef63c5ab7e343e7614568",
#         "allianceTag": "4eOd"
#     },
#     "state": 1
# }
OBJECT_CODE_KINGDOM = 20300101
# {
#     "_id": "622ab2e6a8cc4b49c37ae8d0",
#     "loc": [
#         32,
#         310,
#         2031
#     ],
#     "level": 1,
#     "code": 20500101,
#     "param": {
#         "charmCode": 601
#     },
#     "state": 1,
#     "expired": "2022-03-11T03:24:38.025Z"
# }
OBJECT_CODE_CHARM = 20500101

OBJECT_CODE_OGRE = 20700405
OBJECT_CODE_HUNGRY_WOLF = 20700406
OBJECT_CODE_CYCLOPS = 20700407
OBJECT_CODE_SPARTOI = 20700506  # need rally

OBJECT_MINE_CODE_LIST = (
    OBJECT_CODE_FARM, OBJECT_CODE_LUMBER_CAMP, OBJECT_CODE_QUARRY, OBJECT_CODE_GOLD_MINE, OBJECT_CODE_CRYSTAL_MINE,
    OBJECT_CODE_DRAGON_SOUL_CAVERN
)

OBJECT_MONSTER_CODE_LIST = (
    OBJECT_CODE_ORC, OBJECT_CODE_SKELETON, OBJECT_CODE_GOLEM, OBJECT_CODE_GOBLIN,
    OBJECT_CODE_OGRE, OBJECT_CODE_HUNGRY_WOLF, OBJECT_CODE_CYCLOPS
)

RESEARCH_CODE_MAP = {
    # 生产优先
    'production': {
        'food_production': 30102001,
        'wood_production': 30102002,
        'stone_production': 30102003,
        'gold_production': 30102004,
        'food_capacity': 30102005,
        'wood_capacity': 30102006,
        'stone_capacity': 30102007,
        'gold_capacity': 30102008,
        'food_gathering_speed': 30102009,
        'wood_gathering_speed': 30102010,
        'stone_gathering_speed': 30102011,
        'gold_gathering_speed': 30102012,
        'crystal_gathering_speed': 30102013,
        'infantry_storage': 30102014,
        'ranged_storage': 30102015,
        'cavalry_storage': 30102016,
        'research_speed': 30102017,
        'construction_speed': 30102018,
        'resource_protect': 30102019,
        'advanced_food_production': 30102020,
        'advanced_wood_production': 30102021,
        'advanced_stone_production': 30102022,
        'advanced_gold_production': 30102023,
        'advanced_food_capacity': 30102024,
        'advanced_wood_capacity': 30102025,
        'advanced_stone_capacity': 30102026,
        'advanced_gold_capacity': 30102027,
        'advanced_research_speed': 30102028,
        'advanced_construction_speed': 30102029,
        'advanced_food_gathering_speed': 30102030,
        'advanced_wood_gathering_speed': 30102031,
        'advanced_stone_gathering_speed': 30102032,
        'advanced_gold_gathering_speed': 30102033,
        'advanced_crystal_gathering_speed': 30102034,
    },
    # 训练其次
    'battle': {
        'infantry_hp': 30101001,
        'ranged_hp': 30101002,
        'cavalry_hp': 30101003,
        'infantry_def': 30101004,
        'ranged_def': 30101005,
        'cavalry_def': 30101006,
        'infantry_atk': 30101007,
        'ranged_atk': 30101008,
        'cavalry_atk': 30101009,
        'infantry_spd': 30101010,
        'ranged_spd': 30101011,
        'cavalry_spd': 30101012,
        'troops_storage': 30101013,
        'warrior': 30101014,
        'longbow_man': 30101015,
        'horseman': 30101016,
        'infantry_training_amount': 30101017,
        'ranged_training_amount': 30101018,
        'cavalry_training_amount': 30101019,
        'infantry_training_speed': 30101020,
        'ranged_training_speed': 30101021,
        'cavalry_training_speed': 30101022,
        'infantry_training_cost': 30101023,
        'ranged_training_cost': 30101024,
        'cavalry_training_cost': 30101025,
        'march_size': 30101026,
        'march_limit': 30101027,
        'knight': 30101028,
        'ranger': 30101029,
        'heavy_cavalry': 30101030,
        'troops_spd': 30101031,
        'troops_hp': 30101032,
        'troops_def': 30101033,
        'troops_atk': 30101034,
        'hospital_capacity': 30101035,
        'healing_time_reduced': 30101036,
        'guardian': 30101037,
        'crossbow_man': 30101038,
        'iron_cavalry': 30101039,
        'rally_attack_amount': 30101040,
        'advanced_infantry_hp': 30101041,
        'advanced_ranged_hp': 30101042,
        'advanced_cavalry_hp': 30101043,
        'advanced_infantry_def': 30101044,
        'advanced_ranged_def': 30101045,
        'advanced_cavalry_def': 30101046,
        'advanced_infantry_atk': 30101047,
        'advanced_ranged_atk': 30101048,
        'advanced_cavalry_atk': 30101049,
        'advanced_infantry_spd': 30101050,
        'advanced_ranged_spd': 30101051,
        'advanced_cavalry_spd': 30101052,
        'crusader': 30101053,
        'sniper': 30101054,
        'dragoon': 30101055,
    },
    'advanced': {
        'resource_production': 30103001,
        'infantry_hp_against_archer': 30103002,
        'infantry_def_against_archer': 30103003,
        'infantry_atk_against_archer': 30103004,
        'archer_hp_against_cavalry': 30103005,
        'archer_def_against_cavalry': 30103006,
        'archer_atk_against_cavalry': 30103007,
        'cavalry_hp_against_infantry': 30103008,
        'cavalry_def_against_infantry': 30103009,
        'cavalry_atk_against_infantry': 30103010,
        'resource_capacity': 30103011,
        'castle_defending_infantrys_hp': 30103012,
        'castle_defending_infantrys_def': 30103013,
        'castle_defending_infantrys_atk': 30103014,
        'castle_defending_archers_hp': 30103015,
        'castle_defending_archers_def': 30103016,
        'castle_defending_archers_atk': 30103017,
        'castle_defending_cavalrys_hp': 30103018,
        'castle_defending_cavalrys_def': 30103019,
        'castle_defending_cavalrys_atk': 30103020,
        'resource_protect': 30103021,
        'infantrys_hp_when_composed_of_infantry_only': 30103022,
        'infantrys_def_when_composed_of_infantry_only': 30103023,
        'infantrys_atk_when_composed_of_infantry_only': 30103024,
        'archers_hp_when_composed_of_archer_only': 30103025,
        'archers_def_when_composed_of_archer_only': 30103026,
        'archers_atk_when_composed_of_archer_only': 30103027,
        'cavalrys_hp_when_composed_of_cavalry_only': 30103028,
        'cavalrys_def_when_composed_of_cavalry_only': 30103029,
        'cavalrys_atk_when_composed_of_cavalry_only': 30103030,
        'troop_speed_when_participating_a_rally': 30103031,
        'infantrys_hp_when_participating_a_rally': 30103032,
        'infantrys_def_when_participating_a_rally': 30103033,
        'infantrys_atk_when_participating_a_rally': 30103034,
        'archers_hp_when_participating_a_rally': 30103035,
        'archers_def_when_participating_a_rally': 30103036,
        'archers_atk_when_participating_a_rally': 30103037,
        'cavalrys_hp_when_participating_a_rally': 30103038,
        'cavalrys_def_when_participating_a_rally': 30103039,
        'cavalrys_atk_when_participating_a_rally': 30103040,
    },
}

RESEARCH_MINIMUM_LEVEL_MAP = {
    'production': {
        "food_production": 2,
        "wood_production": 2,
        "stone_production": 2,
        "gold_production": 2,
        "food_capacity": 2,
        "wood_capacity": 2,
        "stone_capacity": 2,
        "gold_capacity": 2,
        "food_gathering_speed": 2,
        "wood_gathering_speed": 2,
        "stone_gathering_speed": 2,
        "gold_gathering_speed": 2,
        "crystal_gathering_speed": 2,
        "infantry_storage": 2,
        "ranged_storage": 2,
        "cavalry_storage": 2,
        "research_speed": 2,
        "construction_speed": 2,
        "resource_protect": 2,
        "advanced_food_production": 3,
        "advanced_wood_production": 3,
        "advanced_stone_production": 3,
        "advanced_gold_production": 3,
        "advanced_food_capacity": 3,
        "advanced_wood_capacity": 3,
        "advanced_stone_capacity": 3,
        "advanced_gold_capacity": 3,
        "advanced_research_speed": 3,
        "advanced_construction_speed": 3,
        "advanced_food_gathering_speed": 3,
        "advanced_wood_gathering_speed": 3,
        "advanced_stone_gathering_speed": 3,
        "advanced_gold_gathering_speed": 3
    },
    'battle': {
        "infantry_hp": 2,
        "ranged_hp": 2,
        "cavalry_hp": 2,
        "infantry_def": 2,
        "ranged_def": 2,
        "cavalry_def": 2,
        "infantry_atk": 2,
        "ranged_atk": 2,
        "cavalry_atk": 2,
        "infantry_spd": 2,
        "ranged_spd": 2,
        "cavalry_spd": 2,
        "troops_storage": 3,
        "warrior": 1,
        "longbow_man": 1,
        "horseman": 1,
        "infantry_training_amount": 2,
        "ranged_training_amount": 2,
        "cavalry_training_amount": 2,
        "infantry_training_speed": 2,
        "ranged_training_speed": 2,
        "cavalry_training_speed": 2,
        "infantry_training_cost": 3,
        "ranged_training_cost": 3,
        "cavalry_training_cost": 3,
        "march_size": 2,
        "march_limit": 1,
        "knight": 1,
        "ranger": 1,
        "heavy_cavalry": 1,
        "troops_spd": 3,
        "troops_hp": 3,
        "troops_def": 3,
        "troops_atk": 3,
        "hospital_capacity": 3,
        "healing_time_reduced": 3,
        "guardian": 1,
        "crossbow_man": 1,
        "iron_cavalry": 1,
        "rally_attack_amount": 5,
        "advanced_infantry_hp": 5,
        "advanced_ranged_hp": 5,
        "advanced_cavalry_hp": 5,
        "advanced_infantry_def": 5,
        "advanced_ranged_def": 5,
        "advanced_cavalry_def": 5,
        "advanced_infantry_atk": 5,
        "advanced_ranged_atk": 5,
        "advanced_cavalry_atk": 5,
        "advanced_infantry_spd": 5,
        "advanced_ranged_spd": 5,
        "advanced_cavalry_spd": 5
    },
    'advanced': {
        "resource_production": 3,
        "infantry_hp_against_archer": 3,
        "infantry_def_against_archer": 3,
        "archer_hp_against_cavalry": 3,
        "archer_def_against_cavalry": 3,
        "cavalry_hp_against_infantry": 3,
        "cavalry_def_against_infantry": 3,
        "infantry_atk_against_archer": 3,
        "archer_atk_against_cavalry": 3,
        "cavalry_atk_against_infantry": 3,
        "resource_capacity": 3,
        "castle_defending_infantrys_hp": 3,
        "castle_defending_infantrys_def": 3,
        "castle_defending_archers_hp": 3,
        "castle_defending_archers_def": 3,
        "castle_defending_cavalrys_hp": 3,
        "castle_defending_cavalrys_def": 3,
        "castle_defending_infantrys_atk": 3,
        "castle_defending_archers_atk": 3,
        "castle_defending_cavalrys_atk": 3,
        "resource_protect": 3,
        "infantrys_hp_when_composed_of_infantry_only": 3,
        "infantrys_def_when_composed_of_infantry_only": 3,
        "archers_hp_when_composed_of_archer_only": 3,
        "archers_def_when_composed_of_archer_only": 3,
        "cavalrys_hp_when_composed_of_cavalry_only": 3,
        "cavalrys_def_when_composed_of_cavalry_only": 3,
        "infantrys_atk_when_composed_of_infantry_only": 3,
        "archers_atk_when_composed_of_archer_only": 3,
        "cavalrys_atk_when_composed_of_cavalry_only": 3,
        "troop_speed_when_participating_a_rally": 3,
        "infantrys_hp_when_participating_a_rally": 3,
        "infantrys_def_when_participating_a_rally": 3,
        "archers_hp_when_participating_a_rally": 3,
        "archers_def_when_participating_a_rally": 3,
        "cavalrys_hp_when_participating_a_rally": 3,
        "cavalrys_def_when_participating_a_rally": 3
    }
}

RESOURCE_IDX_MAP = {
    'food': 0,
    'lumber': 1,
    'stone': 2,
    'gold': 3,
}

# Tier 1
TROOP_CODE_FIGHTER = 50100101
TROOP_CODE_HUNTER = 50100201
TROOP_CODE_STABLE_MAN = 50100301
# Tier 2
TROOP_CODE_WARRIOR = 50100102
TROOP_CODE_LONGBOW_MAN = 50100202
TROOP_CODE_HORSEMAN = 50100302
# Tier 3 (Credit to @mohsenyzd10 https://github.com/hldh214/lok_bot/discussions/11#discussioncomment-2564573)
TROOP_CODE_KNIGHT = 50100103
TROOP_CODE_RANGER = 50100203
TROOP_CODE_HEAVY_CAVALRY = 50100303
# Tier 4
TROOP_CODE_GUARDIAN = 50100104
TROOP_CODE_CROSSBOW_MAN = 50100204
TROOP_CODE_IRON_CAVALRY = 50100304
# Tier 5
TROOP_CODE_CRUSADER = 50100105
TROOP_CODE_SNIPER = 50100205
TROOP_CODE_DRAGON = 50100305

TROOP_LOAD_MAP = {
    TROOP_CODE_FIGHTER: 2,
    TROOP_CODE_HUNTER: 1.5,
    TROOP_CODE_STABLE_MAN: 1,
    TROOP_CODE_WARRIOR: 4,
    TROOP_CODE_LONGBOW_MAN: 3,
    TROOP_CODE_HORSEMAN: 2,
    TROOP_CODE_KNIGHT: 6,
    TROOP_CODE_RANGER: 4.5,
    TROOP_CODE_HEAVY_CAVALRY: 3,
    TROOP_CODE_GUARDIAN: 8,
    TROOP_CODE_CROSSBOW_MAN: 6,
    TROOP_CODE_IRON_CAVALRY: 4,
    TROOP_CODE_CRUSADER: 10,
    TROOP_CODE_SNIPER: 7.5,
    TROOP_CODE_DRAGON: 5
}

BARRACK_LEVEL_TROOP_TRAINING_RATE_MAP = {
    1: 50,
    2: 100,
    3: 150,
    4: 200,
    5: 300,
    6: 400,
    7: 500,
    8: 600,
    9: 700,
    10: 1000,
    11: 1200,
    12: 1400,
    13: 1600,
    14: 1800,
    15: 2000,
    16: 2400,
    17: 2800,
    18: 3200,
    19: 3600,
    20: 4000,
    21: 5000,
    22: 6000,
    23: 7000,
    24: 8000,
    25: 10000,
    26: 12000,
    27: 14000,
    28: 16000,
    29: 18000,
    30: 25000,
}

TRAIN_TROOP_RESOURCE_REQUIREMENT = {
    # Tier 1
    TROOP_CODE_FIGHTER: [30, 0, 60, 15],
    TROOP_CODE_HUNTER: [0, 60, 30, 15],
    TROOP_CODE_STABLE_MAN: [60, 30, 0, 15],
    # Tier 2
    TROOP_CODE_WARRIOR: [60, 0, 120, 30],
    TROOP_CODE_LONGBOW_MAN: [0, 120, 60, 30],
    TROOP_CODE_HORSEMAN: [120, 60, 0, 30],
    # Tier 3
    TROOP_CODE_KNIGHT: [90, 0, 180, 45],
    TROOP_CODE_RANGER: [0, 180, 90, 45],
    TROOP_CODE_HEAVY_CAVALRY: [180, 90, 0, 45],
    # Tier 4
    TROOP_CODE_GUARDIAN: [180, 0, 360, 90],
    TROOP_CODE_CROSSBOW_MAN: [0, 360, 180, 90],
    TROOP_CODE_IRON_CAVALRY: [360, 180, 0, 90],
}

MARCH_TYPE_GATHER = 1
MARCH_TYPE_MONSTER = 5
MARCH_TYPE_SUPPORT = 7
MARCH_TYPE_RALLY = 8


def load_building_json():
    result = {}

    for building_type, building_code in BUILDING_CODE_MAP.items():
        current_building_json = json.load(open(project_root.joinpath(f'lokbot/assets/buildings/{building_type}.json')))
        result[building_code] = current_building_json

    return result


def load_research_json():
    result = {}

    for research_category, research in RESEARCH_CODE_MAP.items():
        current_research_json = json.load(
            open(project_root.joinpath(f'lokbot/assets/research/{research_category}.json'))
        )
        for research_name, research_code in research.items():
            result[research_code] = current_research_json[research_name]

    return result


building_json = load_building_json()
research_json = load_research_json()
# https://play.leagueofkingdoms.com/json/table-live_136.nod
# troop_json = json.load(open(project_root.joinpath('lokbot/assets/troop.json')))
# field_monster_json = json.load(open(project_root.joinpath('lokbot/assets/field_monster.json')))
