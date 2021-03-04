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

import asyncio
import logging

from am43_rc.service import AM43DeviceManager

device_manager = AM43DeviceManager()


async def main():
    try:
        # result = await device_manager.discover(5)
        device = await device_manager.connect("02:6C:9D:D4:07:94")
        print(await device.is_connected())
        state = await device.read_state()
        print(state)
        await device.set_position(20)
        # await device.open()
        # print(await device.read_battery_status())
        await asyncio.sleep(2)
    finally:
        await device_manager.disconnect_all()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
