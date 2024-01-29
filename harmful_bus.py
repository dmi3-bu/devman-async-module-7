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
        assert msg == '{"errors": ["Requires busId specified as string"], "msgType": "Errors"}'

        data = '{"busId": "12345", "route": 104, "lat": 55.750152827772, "lng": 37.492125737793}'
        await ws.send_message(data)
        msg = await ws.get_message()
        assert msg == '{"errors": ["Requires route specified as string"], "msgType": "Errors"}'

        data = '{"busId": "12345", "route": "104", "lat": 55, "lng": 37.492125737793}'
        await ws.send_message(data)
        msg = await ws.get_message()
        assert msg == '{"errors": ["Requires lat specified as float"], "msgType": "Errors"}'

        data = '{"busId": "12345", "route": "104", "lat": 55.750152827772, "lng": 37}'
        await ws.send_message(data)
        msg = await ws.get_message()
        assert msg == '{"errors": ["Requires lng specified as float"], "msgType": "Errors"}'


if __name__ == '__main__':
    trio.run(test_validations)
