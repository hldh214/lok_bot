import json

import httpx

from lokbot import logger


class Base:
    def solve(self, picture_base64: str):
        raise NotImplementedError


class Ttshitu(Base):
    def __init__(self, username, password):
        self.client = httpx.Client(base_url='https://api.ttshitu.com/')
        self.username = username
        self.password = password

    def solve(self, picture_base64: str):
        json_data = {
            'username': self.username,
            'password': self.password,
            'typeid': '1',
            'image': picture_base64
        }

        response = self.client.post('predict', json=json_data)
        json_response = response.json()

        logger.debug(json.dumps({
            'url': 'predict',
            'data': json_data,
            'res': json_response,
            'elapsed': response.elapsed.total_seconds()
        }))

        assert json_response['success'] is True

        return json_response.get('data', {}).get('result', '')
