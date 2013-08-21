#!/usr/bin/env python
# -*- coding: utf-8 -*- 
################################################################################
##
##  LXC container controller script
##
################################################################################
from parser import OpenVPNStatusParser
from threading import Thread
from psycopg2 import connect

class Creator(Thread):
    def __init__(s, dbname, user, password):
        Thread.__init__(s)
        s.db = connect ("dbname='{0}' user='{1}' password='{2}'"
                        .format(dbname, user, password))

    def run(s):
        pass

if __name__ == '__main__':
    c = Creator()
