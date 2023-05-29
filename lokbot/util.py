import random

import jwt

from lokbot.enum import *


def get_resource_index_by_item_code(item_code):
    """
    Returns the index of the item in the resource list
    [0,    1,      2,     3   ]
    [food, lumber, stone, gold]
    """
    if (ITEM_CODE_FOOD_1K <= item_code <= ITEM_CODE_FOOD_10M) or (item_code == ITEM_CODE_FOOD):
        return 0

    if (ITEM_CODE_LUMBER_1K <= item_code <= ITEM_CODE_LUMBER_10M) or (item_code == ITEM_CODE_LUMBER):
        return 1

    if (ITEM_CODE_STONE_1K <= item_code <= ITEM_CODE_STONE_10M) or (item_code == ITEM_CODE_STONE):
        return 2

    if (ITEM_CODE_GOLD_1K <= item_code <= ITEM_CODE_GOLD_10M) or (item_code == ITEM_CODE_GOLD):
        return 3

    return -1


def run_functions_in_random_order(*funcs):
    functions = list(funcs)
    random.shuffle(functions)
    for func in functions:
        func()


def get_zone_id_by_coords(x, y):
    return (x // 32) + 64 * (y // 32)


def decode_jwt(token):
    return jwt.decode(token, options={'verify_signature': False})
