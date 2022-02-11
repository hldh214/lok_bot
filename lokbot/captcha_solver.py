import json

import httpx

from lokbot import logger


class Base:
    def solve(self, get_picture_base64_func, captcha_confirm_func):
        raise NotImplementedError


class Ttshitu(Base):
    def __init__(self, username, password):
        self.client = httpx.Client(base_url='https://api.ttshitu.com/')
        self.username = username
        self.password = password

    def _post(self, url, json_data):
        response = self.client.post(url, json=json_data)
        json_response = response.json()

        logger.debug(json.dumps({
            'url': url,
            'data': json_data,
            'res': json_response,
            'elapsed': response.elapsed.total_seconds()
        }))

        assert json_response['success'] is True

        return json_response.get('data')

    def _predict(self, picture_base64: str):
        return self._post('predict', {
            'username': self.username,
            'password': self.password,
            'typeid': '1',
            'image': picture_base64
        })

    def _report_error(self, predict_id):
        return self._post('reporterror.json', {'id': predict_id})

    def solve(self, get_picture_base64_func, captcha_confirm_func):
        picture_base64 = get_picture_base64_func()

        predict = self._predict(picture_base64)
        predict_result = predict.get('result')
        predict_id = predict.get('id')

        if not captcha_confirm_func(predict_result):
            self._report_error(predict_id)
            return False

        return True


if __name__ == '__main__':
    import base64

    t = Ttshitu('php', '6Xmu6Yy6m9XS')
    # print(t._predict(base64.b64encode(open('../docs/images/captcha/captcha5.png', 'rb').read()).decode()))
    # print(t._report_error('bX0izRo8ReyzEE_jLsEzCA'))
