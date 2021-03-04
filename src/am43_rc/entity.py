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

from typing import Optional


class AM43State(object):
    light: int
    battery: int
    position: Optional[int] = None

    def __init__(
        self, light: Optional[int] = None, battery: Optional[int] = None, position: Optional[int] = None
    ) -> None:
        super().__init__()
        if light is not None:
            self.light = light
        if battery is not None:
            self.battery = battery
        if position is not None:
            self.position = position

    @property
    def is_closed(self) -> bool:
        return self.position == 100

    @property
    def is_open(self) -> bool:
        return not self.is_closed

    def __repr__(self):
        return "AM43 State: {}, Position: {}, Battery: {}, Luminosity: {}".format(
            "OPEN" if self.is_open else "CLOSED", self.position, self.battery, self.light
        )