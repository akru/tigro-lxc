#!/usr/bin/env python
# -*- coding: utf-8 -*- 
## @package tigropy
#  LXC-container controller script.
#
#  This script is a part of TIGRO project.
#  Module contain classes and function for create and control LXC-containers.
from tigro.hostnode import HostNode
import logging

logging.basicConfig(
        format = u'%(levelname)-8s [%(asctime)s] %(name)-15s > %(message)s',
        level = logging.INFO)#, filename='tigro-lxc.log')

if __name__ == '__main__':
    hn = HostNode()
    hn.start()
    hn.join()
