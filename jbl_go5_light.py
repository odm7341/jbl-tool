#!/usr/bin/env python3
"""Control the JBL Go 5 ambient edge light over BLE."""

import argparse
import asyncio
import struct
from collections.abc import Iterable

from bleak import BleakClient

DEFAULT_ADDRESS = "74:68:59:7E:98:33"
SERVICE_WRITE = "65786365-6c70-6f69-6e74-2e636f6d0002"
SERVICE_NOTIFY = "65786365-6c70-6f69-6e74-2e636f6d0001"

PROTOCOL_HEADER = 0xDD00
COMMAND_GET = 0x0001
COMMAND_SET = 0x0002
FEATURE_LIGHT_STATE = 0x0D00


def packet(command: int, payload: bytes) -> bytes:
    return struct.pack("<HHBBH", PROTOCOL_HEADER, command, 1, 0, len(payload)) + payload


def get_light_state_packet() -> bytes:
    return packet(COMMAND_GET, struct.pack("<H", FEATURE_LIGHT_STATE))


def set_light_state_packet(enabled: bool) -> bytes:
    value = 0x80 if enabled else 0x7F
    return packet(COMMAND_SET, struct.pack("<HHB", FEATURE_LIGHT_STATE, 1, value))


def light_state(replies: Iterable[bytes]) -> bool:
    for reply in replies:
        if len(reply) < 10 or reply[:4] != b"\x00\xdd\x01\x00":
            continue
        payload = reply[8:]
        if len(payload) < 2 or payload[:2] != b"\x00\x00":
            continue
        offset = 2
        while offset + 4 <= len(payload):
            feature, length = struct.unpack_from("<HH", payload, offset)
            offset += 4
            value = payload[offset : offset + length]
            offset += length
            if feature == FEATURE_LIGHT_STATE and len(value) == 1:
                return bool(value[0] & 0x80)
    raise RuntimeError("The speaker did not return a light-state response")



async def exchange(address: str, commands: Iterable[bytes]) -> list[bytes]:
    replies: list[bytes] = []

    def on_reply(_: object, data: bytearray) -> None:
        replies.append(bytes(data))

    async with BleakClient(address, timeout=15) as client:
        await client.start_notify(SERVICE_NOTIFY, on_reply)
        for command in commands:
            await client.write_gatt_char(SERVICE_WRITE, command, response=True)
            await asyncio.sleep(0.5)
        await asyncio.sleep(1)
        await client.stop_notify(SERVICE_NOTIFY)

    return replies


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "on", "off"))
    parser.add_argument("--address", default=DEFAULT_ADDRESS, help="speaker Bluetooth address")
    args = parser.parse_args()

    commands: list[bytes] = []
    if args.action != "status":
        commands.append(set_light_state_packet(args.action == "on"))
    commands.append(get_light_state_packet())

    enabled = light_state(await exchange(args.address, commands))
    print(f"Ambient edge light: {'on' if enabled else 'off'}")


if __name__ == "__main__":
    asyncio.run(main())
