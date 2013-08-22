#!/usr/bin/env python
# -*- coding: utf-8 -*- 
## @package tigropy
#  LXC-container controller script.
#
#  This script is a part of TIGRO project.
#  Module contain classes and function for create and control LXC-containers.
from tigro.creator import Creator


if __name__ == '__main__':
    c = Creator()
    c.start()
    c.join()
