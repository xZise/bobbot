#!/usr/bin/python
# -*- coding: utf-8  -*-
from __future__ import division
import pywikibot
import re
from pywikibot import textlib
import urllib2
import StringIO
import struct
import imghdr
import hashlib

site = pywikibot.getSite()

page = pywikibot.page.Page(site, "MediaWiki:Stock Parts/de")
page.text = "Standardteile"
page.save("+German translation (and test if it works);")
