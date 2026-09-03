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
FEATURE_BATTERY_STATUS = 0x000D
FEATURE_LIGHT_STATE = 0x0D00
FEATURE_LIGHT_THEME = 0x0D40
FEATURE_LIGHT_SPEED = 0x0D43

THEMES = {
    "bounce": 0x89,
    "loop": 0x88,
    "switch": 0x8B,
    "freeze": 0x8C,
}


def packet(command: int, payload: bytes) -> bytes:
    return struct.pack("<HHBBH", PROTOCOL_HEADER, command, 1, 0, len(payload)) + payload


def get_light_status_packet() -> bytes:
    return packet(
        COMMAND_GET,
        struct.pack(
            "<HHHH",
            FEATURE_BATTERY_STATUS,
            FEATURE_LIGHT_THEME,
            FEATURE_LIGHT_STATE,
            FEATURE_LIGHT_SPEED,
        ),
    )


def set_light_state_packet(enabled: bool) -> bytes:
    value = 0x80 if enabled else 0x7F
    return packet(COMMAND_SET, struct.pack("<HHB", FEATURE_LIGHT_STATE, 1, value))


def set_light_theme_packet(theme: str) -> bytes:
    return packet(COMMAND_SET, struct.pack("<HHB", FEATURE_LIGHT_THEME, 1, THEMES[theme]))


def set_light_speed_packet(level: int) -> bytes:
    if not 0 <= level <= 2:
        raise ValueError("light speed must be between 0 (slow) and 2 (fast)")
    return packet(COMMAND_SET, struct.pack("<HHB", FEATURE_LIGHT_SPEED, 1, level + 128))




def light_status(replies: Iterable[bytes]) -> dict[int, bytes]:
    values: dict[int, bytes] = {}
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
            values[feature] = value
    if FEATURE_LIGHT_STATE not in values:
        raise RuntimeError("The speaker did not return a light-state response")
    if FEATURE_BATTERY_STATUS not in values:
        raise RuntimeError("The speaker did not return a battery-status response")
    return values



async def exchange(address: str, commands: Iterable[bytes]) -> list[bytes]:
    replies: list[bytes] = []

    def on_reply(_: object, data: bytearray) -> None:
        replies.append(bytes(data))

    try:
        async with BleakClient(address, timeout=15) as client:
            await client.start_notify(SERVICE_NOTIFY, on_reply)
            for command in commands:
                await client.write_gatt_char(SERVICE_WRITE, command, response=True)
                await asyncio.sleep(0.5)
            await asyncio.sleep(1)
            await client.stop_notify(SERVICE_NOTIFY)
    except EOFError:
        if not replies:
            raise

    return replies



async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "on", "off", "theme", "speed"))
    parser.add_argument(
        "--theme",
        choices=THEMES,
        help="ambient light theme; required with the theme action",
    )
    parser.add_argument(
        "--speed",
        type=int,
        metavar="0..2",
        help="ambient light speed; required with the speed action",
    )
    parser.add_argument("--address", default=DEFAULT_ADDRESS, help="speaker Bluetooth address")
    args = parser.parse_args()

    if args.action == "theme" and args.theme is None:
        parser.error("--theme is required with the theme action")

    if args.action == "speed" and args.speed is None:
        parser.error("--speed is required with the speed action")
    commands: list[bytes] = []
    if args.action in ("on", "off"):
        commands.append(set_light_state_packet(args.action == "on"))
    elif args.action == "theme":
        commands.append(set_light_theme_packet(args.theme))
    elif args.action == "speed":
        commands.append(set_light_speed_packet(args.speed))
    commands.append(get_light_status_packet())

    values = light_status(await exchange(args.address, commands))
    enabled = bool(values[FEATURE_LIGHT_STATE][0] & 0x80)
    theme = next(name for name, value in THEMES.items() if values[FEATURE_LIGHT_THEME] == bytes([value]))
    print(f"Ambient edge light: {'on' if enabled else 'off'}")
    print(f"Ambient light theme: {theme}")
    speed = values[FEATURE_LIGHT_SPEED][0] - 128
    print(f"Ambient light speed: {speed}")
    battery = values[FEATURE_BATTERY_STATUS][0]
    charging = battery >= 128
    level = battery - 128 if charging else battery
    if level >= 95:
        level = 100
    print(f"Battery: {level}%{' (charging)' if charging else ''}")



if __name__ == "__main__":
    asyncio.run(main())
