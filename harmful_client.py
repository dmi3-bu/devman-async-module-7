import trio
from trio_websocket import open_websocket_url


async def test_validations():
    async with open_websocket_url('ws://localhost:8000') as ws:
        _msg = await ws.get_message()
        data = '"invalid json))}'
        await ws.send_message(data)
        msg = await ws.get_message()
        assert msg == '{"errors": ["Requires valid JSON"], "msgType": "Errors"}'

        data = '{"msgType": "invalid"}'
        await ws.send_message(data)
        msg = await ws.get_message()
        assert msg == ("{'errors': [{'type': 'missing', 'loc': ('south_lat',), 'msg': 'Field required', 'input': "
                       "ArgsKwargs(()), 'url': 'https://errors.pydantic.dev/2.6/v/missing'}, {'type': 'missing', "
                       "'loc': ('north_lat',), 'msg': 'Field required', 'input': ArgsKwargs(()), "
                       "'url': 'https://errors.pydantic.dev/2.6/v/missing'}, {'type': 'missing', 'loc': ('west_lng',"
                       "), 'msg': 'Field required', 'input': ArgsKwargs(()), "
                       "'url': 'https://errors.pydantic.dev/2.6/v/missing'}, {'type': 'missing', 'loc': ('east_lng',"
                       "), 'msg': 'Field required', 'input': ArgsKwargs(()), "
                       "'url': 'https://errors.pydantic.dev/2.6/v/missing'}], 'msgType': 'Errors'}")

        data = ('{"msgType": "newBounds", "data": {"south_lat": -54, "north_lat": "54", "west_lng": "-54", "east_lng": '
                '"54"}}')
        await ws.send_message(data)
        msg = await ws.get_message()
        assert msg == ("{'errors': [{'type': 'greater_than_equal', 'loc': ('south_lat',), 'msg': 'Input should be "
                       "greater than or equal to 0', 'input': -54, 'ctx': {'ge': 0.0}, "
                       "'url': 'https://errors.pydantic.dev/2.6/v/greater_than_equal'}, {'type': "
                       "'greater_than_equal', 'loc': ('west_lng',), 'msg': 'Input should be greater than or equal to "
                       "0', 'input': '-54', 'ctx': {'ge': 0.0}, 'url': "
                       "'https://errors.pydantic.dev/2.6/v/greater_than_equal'}], 'msgType': 'Errors'}")

if __name__ == '__main__':
    trio.run(test_validations)
