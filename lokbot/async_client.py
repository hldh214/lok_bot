import json

import httpx

import lokbot.enum
from lokbot import logger


class AsyncLokBotApi:
    def __init__(self, access_token):
        self.opener = httpx.AsyncClient(
            headers={
                'User-Agent': 'BestHTTP',
                'x-access-token': access_token
            },
            http2=True,
            base_url=lokbot.enum.API_BASE_URL
        )

    async def post(self, url, json_data=None):
        if json_data is None:
            json_data = {}

        response = await self.opener.post(url, data={'json': json.dumps(json_data)})

        log_data = {
            'url': url,
            'data': json_data,
            'elapsed': response.elapsed.total_seconds(),
        }

        try:
            json_response = response.json()
        except json.JSONDecodeError:
            log_data.update({'res': response.text})
            logger.error(log_data)

            return None

        log_data.update({'res': json_response})
        logger.debug(json.dumps(log_data))

        return json_response

    async def kingdom_caravan_list(self):
        return await self.post('kingdom/caravan/list')

    async def kingdom_caravan_buy(self, caravan_item_id):
        return await self.post('kingdom/caravan/buy', {'caravanItemId': caravan_item_id})
