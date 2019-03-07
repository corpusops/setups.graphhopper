#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import unittest
from controller import main


class TestDocker(unittest.TestCase):
    def setUp(self):
        self.c = main.GraphHopperController()
        self.gdocker = self.c.gdocker
        self.tk = self.c.tk

    def test_detachattach(self):
        ret = self.tk.detach("ying")
        assert "#[backends.graphhopper.servers.ying]" in ret[1]
        ret = self.tk.detach("yang")
        assert "#[backends.graphhopper.servers.yang]" in ret[1]
        ret = self.tk.get_attached_backends()
        assert ret == {'ying': False, 'yang': False}
        ret = self.tk.attach("ying")
        assert "#[backends.graphhopper.servers.ying]" not in ret[1]
        ret = self.tk.attach("yang")
        assert "#[backends.graphhopper.servers.yang]" not in ret[1]
        ret = self.tk.get_attached_backends()
        assert ret == {'ying': True, 'yang': True}


if __name__ == "__main__":
    unittest.main()

# vim:set et sts=4 ts=4 tw=80:
