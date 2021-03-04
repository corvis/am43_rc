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

import argparse
import sys
import traceback

from typing import Optional


class CLI:
    verbose_mode = False

    @classmethod
    def print_data(cls, msg: str):
        print(msg)

    @classmethod
    def print_info(cls, msg: str):
        print(msg, file=sys.stderr)

    @classmethod
    def print_error(cls, exception):
        print(" -> ERROR: " + str(exception), file=sys.stderr)
        if cls.verbose_mode:
            print("--------------")
            traceback.print_exc(file=sys.stderr)

    @classmethod
    def print_debug(cls, string_to_print):
        if cls.verbose_mode:
            print("[DEBUG] " + string_to_print, file=sys.stderr)


class CliExtension(object):
    """
    Allows to extend CLI interface
    """

    COMMAND_NAME: Optional[str] = None
    COMMAND_DESCRIPTION: Optional[str] = None

    def __init__(self, parser: argparse.ArgumentParser):
        super().__init__()
        self.parser = parser

    @classmethod
    def setup_parser(cls, parser: argparse.ArgumentParser):
        pass

    def handle(self, args):
        raise NotImplementedError()


def parse_bool_val(v: str) -> bool:
    if isinstance(v, bool):
        return v
    if v.lower() in ("on", "yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("off", "no", "false", "f", "n", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")
