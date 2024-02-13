import trio
from trio_websocket import open_websocket_url


async def test_validations():
    async with open_websocket_url('ws://localhost:8080') as ws:
        data = '"invalid json))}'
        await ws.send_message(data)
        msg = await ws.get_message()
        assert msg == '{"errors": ["Requires valid JSON"], "msgType": "Errors"}'

        data = '{"busId": 12345, "route": "104", "lat": 55.750152827772, "lng": 37.492125737793}'
        await ws.send_message(data)
        msg = await ws.get_message()
        assert msg == ("{'errors': [{'type': 'string_type', 'loc': ('busId',), 'msg': 'Input should be a valid "
                       "string', 'input': 12345, 'url': 'https://errors.pydantic.dev/2.6/v/string_type'}], "
                       "'msgType': 'Errors'}")

        data = '{"busId": "12345", "route": 104, "lat": 55.750152827772, "lng": 37.492125737793}'
        await ws.send_message(data)
        msg = await ws.get_message()
        assert msg == ("{'errors': [{'type': 'string_type', 'loc': ('route',), 'msg': 'Input should be a valid "
                       "string', 'input': 104, 'url': 'https://errors.pydantic.dev/2.6/v/string_type'}], 'msgType': "
                       "'Errors'}")

        data = '{"busId": "12345", "route": "104", "lat": "-55", "lng": 37.492125737793}'
        await ws.send_message(data)
        msg = await ws.get_message()
        assert msg == ("{'errors': [{'type': 'greater_than', 'loc': ('lat',), 'msg': 'Input should be greater than 0', "
                       "'input': '-55', 'ctx': {'gt': 0.0}, 'url': "
                       "'https://errors.pydantic.dev/2.6/v/greater_than'}], 'msgType': 'Errors'}")

        data = '{"busId": "12345", "route": "104", "lat": 55.750152827772, "lng": -37}'
        await ws.send_message(data)
        msg = await ws.get_message()
        assert msg == ("{'errors': [{'type': 'greater_than', 'loc': ('lng',), 'msg': 'Input should be greater than 0', "
                       "'input': -37, 'ctx': {'gt': 0.0}, 'url': 'https://errors.pydantic.dev/2.6/v/greater_than'}], "
                       "'msgType': 'Errors'}")

if __name__ == '__main__':
    trio.run(test_validations)
