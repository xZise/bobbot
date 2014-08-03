#!/usr/bin/python
# -*- coding: utf-8  -*-
from __future__ import division
from __future__ import unicode_literals
import pywikibot
from pywikibot import page
import mwparserfromhell

site = pywikibot.getSite()

def scan_category(category, prefix):
    for article in category.articles():
        parsed = mwparserfromhell.parse(article.text)
        comment = []
        for heading in parsed.filter_headings():
            old = heading.title
            if heading.title.lower().find("description") >= 0:
                heading.title = "{} description".format(prefix)
            if old != heading.title:
                comment += ["*updated description title;"]
        for template in parsed.filter_templates():
            if template.name.lower() == "description":
                template.name = "Quote"
                comment += ["*replaced description template with quote template;"]
            if template.name.lower() == "quote":
                author = None
                for param in template.params:
                    if param.name == "2":
                        author = param
                    elif param.name != "1":
                        break
                else:
                    if author:
                        template.remove(author)
                        comment += ["-removed author for description;"]
        if comment:
            pywikibot.showDiff(article.text, parsed)
            article.text = parsed
            article.save(comment=" ".join(comment))

scan_category(page.Category(site, "Category:Agencies"), "Agency")
scan_category(page.Category(site, "Category:Default parts"), "Product")
