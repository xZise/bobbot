#!/usr/bin/python
# -*- coding: utf-8  -*-
from __future__ import division
from __future__ import unicode_literals
import pywikibot
from pywikibot import page
import mwparserfromhell
import re

pywikibot.handleArgs()
site = pywikibot.getSite()

def is_description(title):
    return title.lower().find("description") >= 0

def get_heading(section):
    if len(section.nodes) > 0 and type(section.nodes[0]) is mwparserfromhell.nodes.heading.Heading:
        return section.nodes[0]
    else:
        return None

def get_order(section):
    section_title = get_heading(section)
    if not section_title:
        return -2
    else:
        section_title = section_title.title.lower().strip()
    if section_title.find("usage") >= 0 or section_title == "use":
        return -1
    elif is_description(section_title):
        return 0
    elif section_title == "trivia":
        return 2
    elif section_title == "gallery":
        return 3
    elif section_title == "changes":
        return 4
    elif section_title == "see also":
        return 5
    elif section_title == "references":
        return 6
    elif section_title == "notes":
        return 7
    else:
        return 1

NOT_ENGLISH = re.compile(r"^.*/[a-z]{2}(-[a-z]{2})?$")
ENGLISH_QUOTE_PARAMETER = ["1"]
NOT_ENGLISH_QUOTE_PARAMETER = ["1", "src lang", "trans lang", "trans"]
BOX_TEMPLATE = re.compile(r"^:(.*/Box)$", re.I)

def _minc(m, t):
    m[t] = m[t] + 1

def _plural(n):
    return (n, "" if n == 1 else "s")

def scan_list(pages, new_description, reorder_sections, must_be_part):
    apply_all = False
    for article in pages:
        is_english = not NOT_ENGLISH.match(article.title())
        quote_parameter = ENGLISH_QUOTE_PARAMETER if is_english else NOT_ENGLISH_QUOTE_PARAMETER
        print("======================================")
        print("Working on: {}".format(article.title()))
        parsed = mwparserfromhell.parse(article.text)
        comment = {
            "desc title": 0,
            "desc to quote": 0,
        }
        comments = []
        is_part = False
        for template in parsed.filter_templates():
            template_name = template.name.lower().strip()
            if template_name == "description":
                template.name = "Quote"
                _minc(comment, "desc to quote")
            elif template_name.find("infobox/part") >= 0 or template_name.find("partbox") >= 0:
                is_part = True
                print("NOTE: Page '{}' does not use outsourced infobox template.")
            else:
                box_page_match = BOX_TEMPLATE.match(template.name.strip())
                if box_page_match:
                    # read box template
                    box_page = page.Page(site, box_page_match.group(1))
                    for box_template in mwparserfromhell.parse(box_page.text).filter_templates():
                        box_template_name = box_template.name.lower().strip()
                        if box_template_name.find("infobox/part") >= 0 or box_template_name.find("partbox") >= 0:
                            if box_template_name.find("partbox") >= 0:
                                print("NOTE: Page '{}' uses Partbox".format(box_page.title()))
                            is_part = True
                            break
        # ONLY handle part pages (not pages like Part)
        if not is_part and must_be_part:
            print("NOTE: Skipped '{}' because is not part page.".format(article.title()))
            continue
        if is_english:
            for heading in parsed.filter_headings():
                old = heading.title
                if heading.title.strip() != new_description and is_description(heading.title):
                    heading.title = new_description
                    if old != heading.title:
                        _minc(comment, "desc title")
        # only read == .. == sections and not omit the first section
        sections = parsed.get_sections(levels=[2], include_lead=True)
        if reorder_sections:
            # quick and dirty workaround to have the footer in the last section
            last_section = unicode(sections[-1])
            footer_start = last_section.find("{{Parts}}")
            if last_section[footer_start - 1] == "\n" and last_section[footer_start - 2] == "\n":
                while last_section[footer_start - 3] == "\n":
                    footer_start -= 1
            if footer_start < 0:
                print("ERROR: No {{Parts}} in last section")
            else:
                footer_less = last_section[:footer_start]
                footer = last_section[footer_start:]
                sections[-1] = mwparserfromhell.parse(footer_less)
            # the next line is not part of the workaround
            sorted_sections = sorted(sections, key=get_order)
            if footer_start >= 0:
                last_section = unicode(sorted_sections[-1])
                if last_section[-1] != "\n":
                    last_section += "\n"
                last_section += footer
                sorted_sections[-1] = mwparserfromhell.parse(last_section)
            # workaround ends here
            for i in range(0, len(sections)):
                if i >= len(sorted_sections) or get_heading(sections[i]) != get_heading(sorted_sections[i]):
                    comments += ["*sorted order of sections;"]
                    break
            sections = sorted_sections
            new_text = ""

        for section in sections:
            heading = get_heading(section)
            if heading:
                heading.title = " {} ".format(heading.title.strip())
                if is_description(heading.title):
                    for template in section.filter_templates():
                        if template.name.lower().strip() == "quote":
                            author = None
                            for param in template.params:
                                if param.name == "2":
                                    author = param
                                elif param.name not in quote_parameter:
                                    break
                            else:
                                if author:
                                    template.remove(author)
                                    comments += ["-removed author for description;"]
                                break #only change the first quote template!
            if reorder_sections:
                new_text += "{}".format(section)
        if not reorder_sections:
            new_text = "{}".format(parsed)
        if comment["desc title"]:
            comments += ["*updated {} description title{};".format(*_plural(comment["desc title"]))]
        if comment["desc to quote"]:
            comments += ["*replaced {0} description template{1} with quote template{1};".format(*_plural(comment["desc to quote"]))]
        if comments:
            pywikibot.showDiff(article.text, new_text)
            article.text = new_text
            comment = " ".join(comments)
            if not apply_all:
                answer = pywikibot.inputChoice("Save {}?".format(article.title()), ["Yes", "No", "All"], ["Y", "N", "A"], "N")
                if answer == "a":
                    apply_all = True
                else:
                    apply_now = answer == "y"
            if apply_all or apply_now:
                article.save(comment=comment)
            else:
                print("Skipping...")
            if pywikibot.config.simulate:
                print("Summary: {}".format(comment))

def scan_category(category, prefix, reorder_sections=False, must_be_part=True, sub_categories=False):
    new_description = "{} description".format(prefix)
    apply_all = False
    scan_list(category.articles(), new_description, reorder_sections, must_be_part)
    if sub_categories:
        scan_list(category.subcategories(), new_description, reorder_sections, must_be_part)

scan_category(page.Category(site, "Category:Agencies"), "Agency", must_be_part=False, sub_categories=True)
scan_category(page.Category(site, "Category:Default parts"), "Product", True)
