#!/usr/bin/python
# -*- coding: utf-8  -*-
from __future__ import unicode_literals
import pywikibot
import re
from pywikibot import textlib

site = pywikibot.getSite()
data_template = re.compile("^.*/(Data|Box|RefFrame|Param)$")
yes_all = False
for arg in pywikibot.handleArgs():
  if arg in ["--all", "-a"]:
    yes_all = True

for page in site.allpages():
    match = data_template.search(page.title())
    if match:
        if not page.isRedirectPage():
            content = page.text
            templates = textlib.extract_templates_and_params(content)
            for template in templates:
                if template[0] == "Data template used":
                    print("Already contain template in '{}'. Skipped.".format(page.title()))
                    break
            else:
                # for didn't find
                page.text = "<noinclude>{{Data template used}}</noinclude>" + content
                if not yes_all:
                    answer = pywikibot.inputChoice("Add template to '{}'?".format(page.title()), ['Yes', 'No', 'All'], ['y', 'n', 'a'], 'n')
                    if answer == 'a':
                        yes_all = True
                if yes_all or answer != 'n':
                    page.save(comment="+add 'data template used' template;")
                    print("Edited page '{}'.".format(page.title()))
        else:
            print("Page '{}' is a redirect. Skipped.".format(page.title()))
