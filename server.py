import argparse
import json
import logging
from contextlib import suppress
from dataclasses import asdict
from functools import partial
from pydantic import ValidationError, NonNegativeFloat

import trio
from pydantic.dataclasses import dataclass
from trio_websocket import ConnectionClosed, serve_websocket

RESPONSE_INTERVAL = 1
INIT_BOUNDS_COORD = 0.0

buses = {}


@dataclass
class Bus:
    busId: str
    route: str
    lat: NonNegativeFloat
    lng: NonNegativeFloat


@dataclass
class WindowBounds:
    south_lat: NonNegativeFloat
    north_lat: NonNegativeFloat
    west_lng: NonNegativeFloat
    east_lng: NonNegativeFloat

    def update(self, south_lat, north_lat, west_lng, east_lng):
        self.south_lat = south_lat
        self.north_lat = north_lat
        self.west_lng = west_lng
        self.east_lng = east_lng

    def is_inside(self, lat, lng):
        if self.north_lat > lat > self.south_lat and self.east_lng > lng > self.west_lng:
            return True

        return False


async def serve_buses(request):
    try:
        ws = await request.accept()
        while True:
            message = await ws.get_message()
            result, error_msg = validate_bus_data(message)
            if not result:
                await ws.send_message(error_msg)
                continue

            buses[result.busId] = result
    except ConnectionClosed:
        pass


async def serve_browsers(request):
    try:
        ws = await request.accept()
        bounds = WindowBounds(INIT_BOUNDS_COORD, INIT_BOUNDS_COORD, INIT_BOUNDS_COORD, INIT_BOUNDS_COORD)
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

        bounds.update(result.south_lat, result.north_lat, result.west_lng, result.east_lng)


def validate_bounds_data(message):
    try:
        new_bounds_fields = json.loads(message)
    except json.decoder.JSONDecodeError:
        return None, '{"errors": ["Requires valid JSON"], "msgType": "Errors"}'

    try:
        new_bounds = WindowBounds(**new_bounds_fields.get('data', {}))
    except ValidationError as e:
        return None, str({"errors": e.errors(), "msgType": "Errors"})

    return new_bounds, None


def validate_bus_data(message):
    try:
        new_bus_fields = json.loads(message)
    except json.decoder.JSONDecodeError:
        return None, '{"errors": ["Requires valid JSON"], "msgType": "Errors"}'

    try:
        new_bus = Bus(**new_bus_fields)
    except ValidationError as e:
        return None, str({"errors": e.errors(), "msgType": "Errors"})

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
        nursery.start_soon(serve_ws, serve_buses, '127.0.0.1', args.bus_port)
        nursery.start_soon(serve_ws, serve_browsers, '127.0.0.1', args.browser_port)


if __name__ == '__main__':
    args = prepare_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger('trio-websocket').setLevel(logging.INFO)
    else:
        logging.disable(level=logging.DEBUG)

    with suppress(KeyboardInterrupt):
        trio.run(main)
