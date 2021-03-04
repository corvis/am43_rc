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

import abc
import asyncio
import logging
from abc import ABCMeta
from uuid import UUID

from typing import Optional, NamedTuple, Union, List, Any, Dict, TypeVar, Generic

from ble_proxy.error import NotConnectedError
from ble_proxy.utils import none_throws


class BLEDeviceInfo(NamedTuple):
    address: str
    bt_device_name: str
    name: Optional[str]
    rssi: int


AddrOrBLEDevInfo = Union[str, BLEDeviceInfo]
GattIdentifier = Union[str, int, UUID]


class BLEConnection(metaclass=ABCMeta):
    def __init__(self, target: AddrOrBLEDevInfo, iface: str = "hci0") -> None:
        super().__init__()
        self.iface = iface
        if isinstance(target, BLEDeviceInfo):
            self.address = target.address
            self.name = target.name
        elif isinstance(target, str):
            self.address = target
            self.name = None
        else:
            raise ValueError("Device must be specified either by mac address or by BLEDeviceInfo instance")

    @abc.abstractmethod
    async def is_connected(self) -> bool:
        pass

    @abc.abstractmethod
    async def connect(self, timeout: float = 2) -> bool:
        pass

    @abc.abstractmethod
    async def disconnect(self):
        pass

    @abc.abstractmethod
    async def write_gatt_char(self, characteristic: GattIdentifier, data: bytearray, write_with_response: bool = False):
        pass

    @abc.abstractmethod
    async def write_gatt_descriptor(self, handle: int, data: bytearray):
        pass

    @abc.abstractmethod
    async def read_gatt_char(self, characteristic: GattIdentifier) -> bytearray:
        pass

    @abc.abstractmethod
    async def subscribe_for_char_notifications(self, characteristic: GattIdentifier, handler):
        pass

    @abc.abstractmethod
    async def get_all_services(self) -> Any:  # TODO: Implement proper wrapper
        pass


class BLEDevice(metaclass=ABCMeta):
    def __init__(self, connection: BLEConnection) -> None:
        super().__init__()
        self._connection = connection
        self._has_connect_attempts = False
        self._notification_bytes: Optional[bytearray] = None
        self._read_state_event: Optional[asyncio.Event] = asyncio.Event()
        self._lock = asyncio.Lock()
        self._logger = logging.getLogger(self.__class__.__name__)

    def _default_notification_handler(self, sender, data):
        # Todo: It is possible to get multiple notifications for single command have to figure out how to
        #  deal with this...
        if self._notification_bytes is None:
            self._notification_bytes = data
        else:
            self._notification_bytes += data
        # Notify waiters
        if self._read_state_event is not None:
            self._read_state_event.set()

    async def _wait_for_read_event(self):
        if self._read_state_event is not None:
            await self._read_state_event.wait()

    async def _on_connection_established(
        self,
    ):
        """This method could be overridden by subclass to define some device specific behavior e.g. subscribe
        for notifications"""
        pass

    async def verify_connected(self):
        """
        :return:
        :raises: RuntimeError in case device is not connected
        """
        if not await self.is_connected():
            raise NotConnectedError("Illegal state: device must be connected before running any commands")

    async def connect(self, timeout: float = 2):
        async with self._lock:
            if not await self.is_connected():
                await self._connection.connect(timeout=timeout)
                self._has_connect_attempts = True
                await self._on_connection_established()
                # TODO: shall we subscribe for disconnect callback and change status?
                # TODO: shall we check services to determine if device is compatible

    async def is_connected(self):
        if not self._has_connect_attempts:
            return False
        try:
            return await self._connection.is_connected()
        except Exception:
            self._logger.error("Is Connected: Failed to verify connection status")
            return False

    async def disconnect(self):
        async with self._lock:
            if self._has_connect_attempts and await self.is_connected():
                await self._connection.disconnect()

    async def _send_char_command(
        self, char: GattIdentifier, command: bytearray, expect_reply=True, write_with_response=False
    ):
        async with self._lock:
            self._notification_bytes = None
            await self._connection.write_gatt_char(char, command, write_with_response=write_with_response)
            if expect_reply:
                none_throws(self._read_state_event).clear()
                await asyncio.wait_for(self._wait_for_read_event(), timeout=1)  # TODO: Const!
                return self._notification_bytes

    async def _send_descriptor_command(self, handle: int, data: bytearray):
        async with self._lock:
            await self._connection.write_gatt_descriptor(handle, data)

    async def configure_default_response_pipeline(self, target_characteristic: GattIdentifier):
        await self._connection.subscribe_for_char_notifications(
            target_characteristic, self._default_notification_handler
        )

    @property
    def address(self) -> str:
        return self._connection.address

    @property
    def name(self) -> Optional[str]:
        return self._connection.name


T = TypeVar("T", bound=BLEDevice)


class BLEDiscoveryManager(Generic[T]):
    def __init__(self, iface: str = "hci0") -> None:
        self.ble_interface = iface
        self._managed_devices: Dict["str", T] = {}
        self._logger = logging.getLogger(self.__class__.__name__)
        self._lock = asyncio.Lock()

    @classmethod
    def is_target_device(cls, dev: Any) -> bool:
        """
        Method which is used for filtering discovery devices and returning only a subset.
        Useful when you expect to discover only devices of specific type.
        By default doesn't filter out anything so all devices will be included in the final list unless overridden.

        SHOULD BE OVERRIDDEN BY SUBCLASS
        :param dev: device object coming from underlying BLE library(backend)
        :return: True if device should be included into the final discovered list
        """
        return True

    @classmethod
    def compose_device_name(cls, name: str, dev: Any) -> str:
        """
        This method could be used for converting ble device name coming from the device into something more user
        friendly.
        By default just returns the original name.

        SHOULD BE OVERRIDDEN BY SUBCLASS
        :param name: original name coming from ble device
        :param dev: device object coming from underlying BLE library(backend)
        :return:
        """
        return name

    @abc.abstractmethod
    async def discover(self, timeout: int = 5) -> List[BLEDeviceInfo]:
        """
        Listens to devices advertisement for TIMEOUT seconds and returns the list of discovered devices.
        The original devices list coming from the underlying BLE libary will be filtered by is_target_device method.

        :param timeout: time to wait for devices in seconds
        :return: list of discovered devices
        """
        pass

    @classmethod
    def _get_addr_for_target(cls, target: AddrOrBLEDevInfo) -> str:
        """
        Utility method which returns blemac address for the target which might be either address string or
        BLEDeviceInfo object
        :param target: string address or BLEDeviceInfo
        :return: ble mac address
        """
        if isinstance(target, BLEDeviceInfo):
            address = target.address
        elif isinstance(target, str):
            address = target
        else:
            raise ValueError("Device must be specified either by mac address or by BLEDeviceInfo instance")
        return address

    @abc.abstractmethod
    async def build_new_device(self, target: AddrOrBLEDevInfo) -> T:
        pass

    async def connect(self, target: AddrOrBLEDevInfo, timeout: float = 5, attempts=1) -> T:
        address = self._get_addr_for_target(target)
        device = self._managed_devices.get(address, None)
        if device is None:  # If not found in managed devices list
            device = await self.build_new_device(target)
            self._managed_devices[address] = device
        # if not await device.is_connected():
        attempts_left = attempts
        while attempts_left > 0:
            current_attempt = (attempts - attempts_left) + 1
            try:
                await device.connect(timeout)
                return device
            except Exception as e:
                if attempts == 1:
                    raise e
                self._logger.warning("Connection failed. Attempt #{} Re-connecting...".format(current_attempt))
                attempts_left -= 1
                await asyncio.sleep(0.5)
        raise RuntimeError("Connection to device {} failed after {} attempts".format(address, attempts))

    async def disconnect_all(self):
        """
        Disconnects all currently connected devices.
        All errors will be logged and suppressed
        :return: None
        """
        for addr, dev in list(self._managed_devices.items()):
            try:
                self._logger.info("Disconnecting {}...".format(dev.address))
                await dev.disconnect()
                del self._managed_devices[addr]
            except Exception as e:
                self._logger.exception("Unable to disconnect device {}: {}".format(dev.address, str(e)))
