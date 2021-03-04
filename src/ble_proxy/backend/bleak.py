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

from ble_proxy.ble import BLEConnection, AddrOrBLEDevInfo, GattIdentifier


class BleakBLEConnection(BLEConnection):
    def __init__(self, target: AddrOrBLEDevInfo, iface: str = "hci0") -> None:
        super().__init__(target, iface)
        self.__bleak = bleak.BleakClient(self.address, device=self.iface)

    async def is_connected(self) -> bool:
        return await self.__bleak.is_connected()

    async def connect(self, timeout: float = 2) -> bool:
        return await self.__bleak.connect(timeout=timeout)

    async def disconnect(self):
        await self.__bleak.disconnect()

    async def write_gatt_char(self, characteristic: GattIdentifier, data: bytearray, write_with_response: bool = False):
        await self.__bleak.write_gatt_char(characteristic, data, write_with_response)

    async def write_gatt_descriptor(self, handle: int, data: bytearray):
        await self.__bleak.write_gatt_descriptor(handle, data)

    async def read_gatt_char(self, characteristic: GattIdentifier) -> bytearray:
        return await self.__bleak.read_gatt_char(characteristic)

    async def subscribe_for_char_notifications(self, characteristic: GattIdentifier, handler):
        await self.__bleak.start_notify(characteristic, handler)

    async def get_all_services(self):
        return await self.__bleak.get_services()
