import asyncio

import lokbot.async_client

import lokbot.enum


class AsyncLokFarmer:
    def __init__(self, token, concurrency=50):
        self.api = lokbot.async_client.AsyncLokBotApi(token)
        self.concurrency = concurrency

    async def parallel_buy_caravan(self):
        caravan_items = (await self.api.kingdom_caravan_list()).get('caravan').get('items')

        for each_item in caravan_items:
            if each_item.get('costItemCode') != lokbot.enum.ITEM_CODE_CRYSTAL:
                continue

            if each_item.get('code') not in lokbot.enum.BUYABLE_CARAVAN_ITEM_CODE_LIST:
                continue

            jobs = [
                asyncio.ensure_future(self.api.kingdom_caravan_buy(each_item.get('_id')))
                for _ in range(self.concurrency)
            ]
            await asyncio.gather(*jobs)
            return
