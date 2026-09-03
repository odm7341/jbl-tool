# jbl-tool

Control a JBL Go 5's ambient edge light from Linux over Bluetooth Low Energy. No JBL Portable app required.

This repository currently supports verified ambient-light controls:

- enabled/disabled: `status`, `on`, and `off`
- themes: `bounce`, `loop`, `switch`, and `freeze`

## Requirements

- Linux with BlueZ and a Bluetooth LE adapter
- Python 3.10+
- A paired JBL Go 5

Install the Python dependency:

```bash
python3 -m pip install -r requirements.txt
```

## Usage

The utility defaults to the Bluetooth address used during development. For another speaker, pass its address explicitly:

```bash
./jbl_go5_light.py status --address 74:68:59:7E:98:33
./jbl_go5_light.py off --address 74:68:59:7E:98:33
./jbl_go5_light.py on --address 74:68:59:7E:98:33
./jbl_go5_light.py theme --theme bounce --address 74:68:59:7E:98:33
./jbl_go5_light.py theme --theme loop --address 74:68:59:7E:98:33
./jbl_go5_light.py theme --theme switch --address 74:68:59:7E:98:33
./jbl_go5_light.py theme --theme freeze --address 74:68:59:7E:98:33

Find paired-device addresses with:

```bash
bluetoothctl devices
```

The command prints the resulting speaker state after every request.

## Protocol

The Go 5 exposes JBL's private Protocol 4 service:

```text
service: 65786365-6c70-6f69-6e74-2e636f6d0000
write:   65786365-6c70-6f69-6e74-2e636f6d0002
notify:  65786365-6c70-6f69-6e74-2e636f6d0001
```

The light-state feature is `0x0D00`. JBL Portable sends `0x7F` to disable it and `0x80` to enable it. The light-theme feature is `0x0D40`.

## Bluetooth transport note

Some BlueZ/controller combinations do not establish a separate GATT control bearer while the speaker is actively connected as an A2DP audio sink. If the utility reports `org.bluez.Error.Failed: Not connected`, disconnect and reconnect the speaker, then retry the command.

## Verified theme behavior

| Theme | Value | Observed behavior |
| --- | --- | --- |
| `bounce` | `0x89` | Animated blue light |
| `loop` | `0x88` | Distinct animation |
| `switch` | `0x8B` | Swaps the blue light between top and bottom bars |
| `freeze` | `0x8C` | Static light |

## Reverse-engineered, not yet exposed

The broader Protocol 4 implementation also contains controls for battery and firmware information, device naming, feedback tones, auto-standby, Playtime Boost, Auracast/group state, EQ, and additional lighting parameters. Those commands are intentionally not exposed until they are tested against the Go 5.
