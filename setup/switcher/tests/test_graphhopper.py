#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import unittest
from controller import main


class TestDocker(unittest.TestCase):
    def setUp(self):
        self.c = main.GraphHopperController()
        self.gdocker = self.c.gdocker
        self.oto = self.c.timeout

    def tearDown(self):
        self.c.timeout = self.oto

    def test_limits_timeout(self):
        self.gdocker.wipe("yang")
        assert self.c.is_data_ok("yang") is False
        self.c.timeout = 1
        self.c.reconstruct("yang")
        self.assertRaises(main.UpdateTimeoutError, self.c.wait_ready, "yang")
        self.c.timeout = self.oto
        self.c.reconstruct("yang")
        self.c.wait_ready("yang")
        assert self.c.is_data_ok("yang") is True

    def test_isdataok(self):
        self.gdocker.wipe("yang")
        assert self.c.is_data_ok("yang") is False
        self.gdocker.start("yang")
        self.c.wait_ready("yang")
        assert self.c.is_data_ok("yang") is True


if __name__ == "__main__":
    unittest.main()

# vim:set et sts=4 ts=4 tw=80:
