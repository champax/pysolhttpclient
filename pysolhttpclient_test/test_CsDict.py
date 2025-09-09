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
import logging
import unittest

from pysolhttpclient.NonCsDict.NonCsDict import NonCsDict

logger = logging.getLogger(__name__)


# noinspection PyProtectedMember
class TestCsDict(unittest.TestCase):
    """
    Test description
    """

    # noinspection PyPep8Naming
    def setUp(self):
        """
        Setup (called before each test)
        """

        pass

    # noinspection PyPep8Naming
    def tearDown(self):
        """
        Setup (called after each test)
        """

        pass

    def test_cs_dict(self):
        """
        Test
        """

        d = NonCsDict()

        d["AAA"] = 1
        d["BBb"] = 2

        # get + contains
        self.assertTrue("AAA" in d)
        self.assertTrue("aaA" in d)
        self.assertTrue("BBB" in d)
        self.assertTrue(d.get("AAA", 1))
        self.assertTrue(d.get("aaA", 1))
        self.assertTrue(d.get("BBB", 2))

        # d2 : copy, get + contains
        d2 = d.copy()
        self.assertTrue("AAA" in d2)
        self.assertTrue("aaA" in d2)
        self.assertTrue(d2.get("AAA", 1))
        self.assertTrue(d2.get("aaA", 1))
        self.assertTrue(d2.get("BBB", 2))

        # d2 : pop
        v1 = d2.pop("aaA")
        self.assertEqual(v1, 1)
        self.assertFalse("AAA" in d2)

        k, v = d2.popitem()
        self.assertEqual(k, "bbb")
        self.assertEqual(v, 2)

        # items
        ark = list()
        arv = list()
        for k, v in d.items():
            ark.append(k)
            arv.append(v)
        self.assertEqual(len(ark), 2)
        self.assertEqual(len(arv), 2)
        self.assertIn("aaa", ark)
        self.assertIn("bbb", ark)
        self.assertIn(1, arv)
        self.assertIn(2, arv)

        d3 = dict()
        d3["XXX"] = 3
        d3["YYY"] = 4
        d.update(d3)

        self.assertTrue("xxx" in d)
        self.assertIn("xxx", d)
        self.assertTrue("yyy" in d)
        self.assertIn("yyy", d)
        self.assertEqual(d["xxx"], 3)
        self.assertEqual(d["yyy"], 4)
        self.assertEqual(d.get("xxx"), 3)
        self.assertEqual(d.get("yyy"), 4)
