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
        assert msg == '{"errors": ["Requires msgType specified"], "msgType": "Errors"}'

        data = '{"msgType": "newBounds", "data": null}'
        await ws.send_message(data)
        msg = await ws.get_message()
        assert msg == '{"errors": ["Requires data specified"], "msgType": "Errors"}'

        data = '{"msgType": "newBounds", "data": {}}'
        await ws.send_message(data)
        msg = await ws.get_message()
        assert msg == '{"errors": ["Requires lat and lng specified"], "msgType": "Errors"}'

        data = ('{"msgType": "newBounds", "data": {"south_lat": "54", "north_lat": "54", "west_lng": "54", "east_lng": '
                '"54"}}')
        await ws.send_message(data)
        msg = await ws.get_message()
        assert msg == '{"errors": ["Requires lat and lng specified as floats"], "msgType": "Errors"}'


if __name__ == '__main__':
    trio.run(test_validations)
