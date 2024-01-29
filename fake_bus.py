import argparse
import itertools
import json
import logging
import os
import random
import uuid
from contextlib import suppress

import trio
import trio_websocket
from trio_websocket import open_websocket_url

RECONNECTION_TIMEOUT = 3


def load_routes(directory_path='routes'):
    for filename in os.listdir(directory_path):
        if filename.endswith(".json"):
            filepath = os.path.join(directory_path, filename)
            with open(filepath, 'r', encoding='utf8') as file:
                yield json.load(file)


def get_next_coordinate(route):
    init_coord_position = random.randint(0, len(route['coordinates']) - 1)
    for coords in itertools.islice(route['coordinates'], init_coord_position, len(route['coordinates'])):
        yield coords

    for coords in itertools.cycle(route['coordinates']):
        yield coords


async def run_bus(send_channel, bus_id, route):
    coords = get_next_coordinate(route)
    while True:
        await send_message_to_channel(send_channel, bus_id, next(coords), route)
        await trio.sleep(args.refresh_timeout + random.randint(1, 5))


async def send_message_to_channel(send_channel, bus_id, coords, route):
    data = {"busId": bus_id, "route": route['name'], 'lat': coords[0], 'lng': coords[1]}
    await send_channel.send(data)


def generate_bus_id(route_id, bus_index):
    return f"{route_id}-{bus_index}-{args.emulator_id}"


def relaunch_on_disconnect(async_function):
    async def wrapper(arguments):
        while True:
            try:
                await async_function(arguments)
            except (trio_websocket.HandshakeError, trio_websocket.ConnectionClosed) as e:
                logging.debug(f'{type(e)}: {e}')
                await trio.sleep(RECONNECTION_TIMEOUT)

    return wrapper


@relaunch_on_disconnect
async def send_updates(receive_channel):
    async with open_websocket_url(args.server) as ws:
        async for data in receive_channel:
            await ws.send_message(json.dumps(data, ensure_ascii=False))


def prepare_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--server", type=str, default='ws://localhost:8080', help="websocket address")
    parser.add_argument("--routes_number", type=int, default=595, help="Number of bus routes")
    parser.add_argument("--buses_per_route", type=int, default=3, help="Number of buses per route")
    parser.add_argument("--websockets_number", type=int, default=3, help="Number of websocket client connections")
    parser.add_argument("--emulator_id", type=str, default=str(uuid.uuid4()), help="Prefix for bus_id")
    parser.add_argument("--refresh_timeout", default=3, type=int, help="refresh_timeout")
    parser.add_argument("-v", "--verbose", action=argparse.BooleanOptionalAction, help="Enable logging")

    return parser.parse_args()


async def main():
    async with trio.open_nursery() as nursery:
        send_channels = []
        for i in range(args.websockets_number):
            send_channel, receive_channel = trio.open_memory_channel(0)
            nursery.start_soon(send_updates, receive_channel)
            send_channels.append(send_channel)

        routes = itertools.islice(load_routes(), args.routes_number)
        buses_limit = args.routes_number * args.buses_per_route
        for idx, route in enumerate(itertools.cycle(routes)):
            if idx == buses_limit:
                break

            bus_id = generate_bus_id(route['name'], idx)
            nursery.start_soon(run_bus, random.choice(send_channels), bus_id, route)


if __name__ == '__main__':
    args = prepare_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.disable(level=logging.DEBUG)

    with suppress(KeyboardInterrupt):
        trio.run(main)
