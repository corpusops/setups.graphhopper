#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import unittest
from controller import main


class TestDocker(unittest.TestCase):
    def setUp(self):
        self.gdocker = main.GDocker()

    def test_containers(self):
        ct = self.gdocker.get_containers()
        assert (
            main.COMPOSE_PROJECT_NAME
            in ct["/" + main.COMPOSE_PROJECT_NAME + "_traefik_1"]["Names"][0]
        )

    def test_yingyang(self):
        ying = self.gdocker.get_ying()
        yang = self.gdocker.get_yang()
        no = self.gdocker.get_ct("foo")
        assert "-ying_" in ying["Names"][0]
        assert "-yang_" in yang["Names"][0]
        assert no is None

    def test_stopstart(self):
        y = self.gdocker.get_yang()
        if y["State"] == "running":
            self.gdocker.stop("yang")
        self.gdocker.start("yang")
        self.gdocker.stop("yang")
        self.gdocker.start("yang")
        yang = self.gdocker.get_yang()
        st = yang["State"]
        assert "Up " in st or "running" in st

    def test_syncdata(self):
        self.gdocker.stop("yang")
        ret = self.gdocker.sync_data("ying", "yang")
        assert "sending" in ret.decode("utf-8")

    def test_cleanup_data(self):
        self.gdocker.cleanup_data("yang")
        ret = self.gdocker.list_data("yang")
        assert ret == ""


if __name__ == "__main__":
    unittest.main()

# vim:set et sts=4 ts=4 tw=80:
