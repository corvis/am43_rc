#    AM43 Remote Control
#    Copyright (C) 2020 Dmitry Berezovsky
#
#    am43 is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    am43 is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import bleak
from typing import List, Any, Optional

from am43_rc.entity import AM43State
from ble_proxy.backend.bleak import BleakBLEConnection
from ble_proxy.ble import (
    BLEConnection,
    BLEDevice,
    BLEDiscoveryManager,
    BLEDeviceInfo,
    AddrOrBLEDevInfo,
)


class AM43Device(BLEDevice):
    CONTROL_SERVICE_UUID = "0000fe50-0000-1000-8000-00805f9b34fb"
    CONTROL_RW_CHARACTERISTIC_UUID = "0000fe51-0000-1000-8000-00805f9b34fb"

    CMD_PREFIX = bytearray([0x00, 0xFF, 0x00, 0x00, 0x9A])
    NO_DATA = bytearray([0x01])

    class Cmd:
        # OPEN_BLINDS = bytearray([0x00, 0xFF, 0x00, 0x00, 0x9A, 0x0D, 0x01, 0x00, 0x96])
        # CLOSE_BLINDS = bytearray([0x00, 0xFF, 0x00, 0x00, 0x9A, 0x0D, 0x01, 0x64, 0xF2])
        # STOP_BLINDS = bytearray([0x00, 0xFF, 0x00, 0x00, 0x9A, 0x0A, 0x01, 0xCC, 0x5D])
        # POSITION_BLINDS_PREFIX = bytearray([0x00, 0xFF, 0x00, 0x00])
        # POSITION_BLIND_FIXED_CRC_CONTENT = bytearray([0x9A, 0x0D, 0x01])
        # BATTERY_REQUEST = bytearray([0x00, 0xFF, 0x00, 0x00, 0x9A, 0xA2, 0x01, 0x01, 0x38])
        # LIGHT_REQUEST = bytearray([0x00, 0xFF, 0x00, 0x00, 0x9A, 0xAA, 0x01, 0x01, 0x30])
        # POSITION_REQUEST = bytearray([0x00, 0xFF, 0x00, 0x00, 0x9A, 0xA7, 0x01, 0x01, 0x3D])
        MOVE = 0x0A
        SET_POSITION = 0x0D
        GET_POSITION = 0xA7
        GET_BATTERY = 0xA2
        GET_LIGHT = 0xAA
        LOGIN = 0x17

    class MoveOption:
        MOVE_OPEN = bytearray([0xDD])
        MOVE_CLOSE = bytearray([0xEE])
        MOVE_STOP = bytearray([0xCC])

    class ReplyPrefix:
        BATTERY = bytearray((0x9A, 0xA2))
        LIGHT = bytearray((0x9A, 0xAA))
        POSITION = bytearray((0x9A, 0xA7))

    def __init__(self, connection: BLEConnection) -> None:
        super().__init__(connection)

    @classmethod
    def __verify_reply_identifier(cls, expected_prefix: bytearray, blob: bytearray):
        match = expected_prefix == blob[: len(expected_prefix)]
        if not match:
            raise ValueError("Unexpected prefix for reply {}. Expected {}".format(blob, expected_prefix))

    def __calc_crc(self, blob: bytearray) -> int:
        crc = 0
        for x in blob:
            crc = crc ^ x
        return crc ^ 0xFF

    def __parse_status_blob(self, data):
        pass

    def on_state_data_received(self, sender, data):
        self._logger.info("Received data: ", str(data))

    async def _on_connection_established(self):
        await self.configure_default_response_pipeline(self.CONTROL_RW_CHARACTERISTIC_UUID)

    async def read_state(self):
        # Invalidate state
        self.__state = None
        self.__state = AM43State(
            battery=await self.read_battery_status(),
            light=await self.read_light_status(),
            position=await self.read_position(),
        )
        return self.__state

    async def __send_command(self, command: int, params: bytearray) -> bytearray:
        data = bytearray(self.CMD_PREFIX)
        data.append(command)
        data.append(len(params))
        data += params
        data.append(self.__calc_crc(data))
        return await self._send_char_command(self.CONTROL_RW_CHARACTERISTIC_UUID, data)

    async def read_battery_status(self) -> int:
        data = await self.__send_command(self.Cmd.GET_BATTERY, self.NO_DATA)
        self.__verify_reply_identifier(self.ReplyPrefix.BATTERY, data)
        return data[7]

    async def read_light_status(self) -> int:
        data = await self.__send_command(self.Cmd.GET_LIGHT, self.NO_DATA)
        self.__verify_reply_identifier(self.ReplyPrefix.LIGHT, data)
        return data[4]

    async def read_position(self) -> Optional[int]:
        """
        Returns current position in percents.
        :return: Curent position in %. None means limits are not set so it's impossible to determine position
        """
        data = await self.__send_command(self.Cmd.GET_POSITION, self.NO_DATA)
        self.__verify_reply_identifier(self.ReplyPrefix.POSITION, data)
        # * Bytes in this packet are:
        #  *  3: Configuration flags, bits are:
        #  *    1: direction
        #  *    2: operation mode
        #  *    3: top limit set
        #  *    4: bottom limit set
        #  *    5: has light sensor
        #  *  4: Speed setting
        #  *  5: Current position
        #  *  6,7: Shade length.
        #  *  8: Roller diameter.
        #  *  9: Roller type.
        pos = data[5]
        return pos if pos != 255 else None

    async def set_position(self, position: int):
        if 0 < position > 100:
            raise ValueError("Position should be in percent (integer 0-100). Got " + str(position))

        await self.__send_command(self.Cmd.SET_POSITION, bytearray([position]))

    async def open(self):
        await self.__send_command(self.Cmd.MOVE, self.MoveOption.MOVE_OPEN)

    async def close(self):
        await self.__send_command(self.Cmd.MOVE, self.MoveOption.MOVE_CLOSE)

    async def stop(self):
        await self.__send_command(self.Cmd.MOVE, self.MoveOption.MOVE_STOP)


class AM43DeviceManager(BLEDiscoveryManager[AM43Device]):
    DEVICE_NAME_PREFIXES = ["Blind"]

    def __init__(self, iface: str = "hci0") -> None:
        super().__init__(iface)

    @classmethod
    def is_target_device(cls, dev: "bleak.backends.device.BLEDevice"):
        return dev.name and len(list(filter(dev.name.startswith, cls.DEVICE_NAME_PREFIXES))) > 0

    @classmethod
    def compose_device_name(cls, dev_name: str, dev: Any) -> str:
        name = dev_name
        if dev_name:
            for prefix in cls.DEVICE_NAME_PREFIXES:
                if dev_name.startswith(prefix):
                    name = dev_name  # .replace(prefix, "", 1)
                    break
        return name.strip()

    async def discover(self, timeout: int = 5) -> List[BLEDeviceInfo]:
        async with self._lock:
            discovered_devs = await bleak.discover(timeout)
        return list(
            map(
                lambda dev: BLEDeviceInfo(
                    address=dev.address,
                    bt_device_name=(dev.name or "").strip(),
                    name=self.compose_device_name(dev.name, dev),
                    rssi=dev.rssi,
                ),
                filter(self.is_target_device, discovered_devs),
            )
        )

    async def build_new_device(self, target: AddrOrBLEDevInfo) -> AM43Device:
        return AM43Device(BleakBLEConnection(target, self.ble_interface))
