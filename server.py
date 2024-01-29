import argparse
import json
import logging
from contextlib import suppress
from dataclasses import asdict, dataclass
from functools import partial

import trio
from trio_websocket import ConnectionClosed, serve_websocket

RESPONSE_INTERVAL = 1
INIT_BOUNDS_COORD = 0.0

buses = {}


@dataclass
class Bus:
    busId: str
    route: str
    lat: float
    lng: float


@dataclass
class WindowBounds:
    south_lat: float = INIT_BOUNDS_COORD
    north_lat: float = INIT_BOUNDS_COORD
    west_lng: float = INIT_BOUNDS_COORD
    east_lng: float = INIT_BOUNDS_COORD

    def update(self, south_lat, north_lat, west_lng, east_lng):
        self.south_lat = south_lat
        self.north_lat = north_lat
        self.west_lng = west_lng
        self.east_lng = east_lng

    def is_inside(self, lat, lng):
        if self.north_lat > lat > self.south_lat and self.east_lng > lng > self.west_lng:
            return True

        return False


async def bus_server(request):
    try:
        ws = await request.accept()
        while True:
            message = await ws.get_message()
            result, error_msg = validate_bus_data(message)
            if not result:
                await ws.send_message(error_msg)
                continue

            buses[result["busId"]] = Bus(**result)
    except ConnectionClosed:
        pass


async def browser_server(request):
    try:
        ws = await request.accept()
        bounds = WindowBounds()
        async with trio.open_nursery() as nursery:
            nursery.start_soon(talk_to_browser, ws, bounds)
            nursery.start_soon(listen_browser, ws, bounds)
    except ConnectionClosed:
        pass


async def talk_to_browser(ws, bounds):
    while True:
        await send_buses(ws, bounds)
        await trio.sleep(RESPONSE_INTERVAL)


async def listen_browser(ws, bounds):
    while True:
        message = await ws.get_message()
        logging.debug(message)
        result, error_msg = validate_bounds_data(message)
        if not result:
            await ws.send_message(error_msg)
            continue

        bounds.update(**result['data'])


def validate_bounds_data(message):
    try:
        new_bounds = json.loads(message)
    except json.decoder.JSONDecodeError:
        return None, '{"errors": ["Requires valid JSON"], "msgType": "Errors"}'

    if new_bounds.get('msgType') != 'newBounds':
        return None, '{"errors": ["Requires msgType specified"], "msgType": "Errors"}'

    if type(new_bounds.get('data')) is not dict:
        return None, '{"errors": ["Requires data specified"], "msgType": "Errors"}'

    if set(new_bounds['data'].keys()) != {'south_lat', 'north_lat', 'west_lng', 'east_lng'}:
        return None, '{"errors": ["Requires lat and lng specified"], "msgType": "Errors"}'

    if any(map(lambda x: type(x) is not float, new_bounds['data'].values())):
        return None, '{"errors": ["Requires lat and lng specified as floats"], "msgType": "Errors"}'

    return new_bounds, None


def validate_bus_data(message):
    try:
        new_bus = json.loads(message)
    except json.decoder.JSONDecodeError:
        return None, '{"errors": ["Requires valid JSON"], "msgType": "Errors"}'

    if type(new_bus.get('busId')) != str:
        return None, '{"errors": ["Requires busId specified as string"], "msgType": "Errors"}'

    if type(new_bus.get('route')) != str:
        return None, '{"errors": ["Requires route specified as string"], "msgType": "Errors"}'

    if type(new_bus.get('lat')) != float:
        return None, '{"errors": ["Requires lat specified as float"], "msgType": "Errors"}'

    if type(new_bus.get('lng')) != float:
        return None, '{"errors": ["Requires lng specified as float"], "msgType": "Errors"}'

    return new_bus, None


async def send_buses(ws, bounds):
    buses_in_bounds = [asdict(bus) for bus in buses.values() if bounds.is_inside(bus.lat, bus.lng)]
    logging.debug(f'{len(buses_in_bounds)} buses inside bounds')

    data = {
        "msgType": "Buses",
        "buses": buses_in_bounds
    }
    await ws.send_message(json.dumps(data, ensure_ascii=False))


def is_inside(bounds, lat, lng):
    if bounds['north_lat'] > lat > bounds['south_lat'] and bounds['east_lng'] > lng > bounds['west_lng']:
        return True

    return False


def prepare_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bus_port", type=int, default=8080)
    parser.add_argument("--browser_port", type=int, default=8000)
    parser.add_argument("-v", "--verbose", action=argparse.BooleanOptionalAction, help="Enable logging")

    return parser.parse_args()


async def main():
    async with trio.open_nursery() as nursery:
        serve_ws = partial(serve_websocket, ssl_context=None)
        nursery.start_soon(serve_ws, bus_server, '127.0.0.1', args.bus_port)
        nursery.start_soon(serve_ws, browser_server, '127.0.0.1', args.browser_port)


if __name__ == '__main__':
    args = prepare_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger('trio-websocket').setLevel(logging.INFO)
    else:
        logging.disable(level=logging.DEBUG)

    with suppress(KeyboardInterrupt):
        trio.run(main)
