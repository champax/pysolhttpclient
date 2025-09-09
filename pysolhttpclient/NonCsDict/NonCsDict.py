"""
# -*- coding: utf-8 -*-
# ===============================================================================
#
# Copyright (C) 2013/2025 Laurent Labatut / Laurent Champagnac
#
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
# ===============================================================================
"""
from typing import Mapping


class NonCsDict(dict):
    """
    Case insensitive dict
    """

    @classmethod
    def _to_lower(cls, key):
        """
        To lower
        :param key: object
        :return: object
        """
        return key.lower() if isinstance(key, str) else key

    def __init__(self, *args, **kwargs):
        super(NonCsDict, self).__init__(*args, **kwargs)
        self._lower_all_keys()

    def __getitem__(self, key):
        return super(NonCsDict, self).__getitem__(self._to_lower(key))

    def __setitem__(self, key, value):
        super(NonCsDict, self).__setitem__(self._to_lower(key), value)

    def __delitem__(self, key):
        return super(NonCsDict, self).__delitem__(self._to_lower(key))

    def __contains__(self, key):
        # noinspection PyTypeChecker
        return super(NonCsDict, self).__contains__(self._to_lower(key))

    def pop(self, key, *args, **kwargs):
        return super(NonCsDict, self).pop(self._to_lower(key), *args, **kwargs)

    def get(self, key, *args, **kwargs):
        return super(NonCsDict, self).get(self._to_lower(key), *args, **kwargs)

    def setdefault(self, key, *args, **kwargs):
        # noinspection PyArgumentList
        return super(NonCsDict, self).setdefault(self._to_lower(key), *args, **kwargs)

    def copy(self):
        return NonCsDict(self)

    def update(self, other=None, **kwargs):
        if other is not None:
            for k, v in other.items() if isinstance(other, Mapping) else other:
                self[self._to_lower(k)] = v
        for k, v in kwargs.items():
            self[self._to_lower(k)] = v

    def _lower_all_keys(self):
        for k in list(self.keys()):
            # Pop for us
            v = super(NonCsDict, self).pop(k)
            # Add to us (will be lowered)
            self.__setitem__(k, v)
