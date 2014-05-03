#!/usr/bin/python
# -*- coding: utf-8  -*-
from __future__ import division
import pywikibot
import re
from pywikibot import textlib
from pywikibot.page import Page

site = pywikibot.getSite()
yes_all = False
for arg in pywikibot.handleArgs():
  if arg in ["--all", "-a"]:
    yes_all = True

def get_name(page):
  if page.title().startswith("File:"):
    return page.title(withNamespace = False)
  else:
    return source.title()

def replace(source_name, target_name):
  source = Page(site, "")
  target = Page(site, "")
  old = get_name(source)
  new = get_name(target)

  # Move all references
  for reference in source.getReferences(follow_redirects=False):
    old_text = reference.text
    reference.text = old_text.replace(old, new)
    pywikibot.showDiff(old_text, reference.text)

def peek(l):
  return l[len(l) - 1] if len(l) > 0 else None

from collections import namedtuple
def split_sections(content):
  """
  This method splits the text given in the parameter into sections. Currently it doesn't detect <pre></pre> blocks or using headers in templates.

  The result is a list of all sections. Each section is a 5-tuple with the following values:
  0. The header which is the part between the equal signs. Is None for the first section if the page doesn't start with a header.
  1. The content following after it until the next header. Is never None.
  2. The parent section. None if there is none.
  3. The child sections as a list of sections. The resulting list also contains them.
  4. The depth as the number of equals signs. So there might be gaps, but the parent section has always a lower depth value and the children sections a higher depth value. Later sibling sections might have higher depth values than the current section. Previous sibling sections have always the same depth value. If there is no header defaults to zero.

  @param content: The content as a string
  @return: a list with all sections
  """
  Section = namedtuple('Section', 'title content parent children depth')

  section_regex = re.compile(r"(?:\A|^(?P<es>=+) *(?P<title>[^\n\r]+?) *(?P=es))(?P<content>[^=].*?)(?=(?:^=+ *[^=]+ *=+|\Z))", re.M | re.S)
  super_sections = [] # use as stack
  sections = []
  for match in section_regex.finditer(content):
    depth = 0 if match.group('es') is None else len(match.group('es'))
    while len(super_sections) > 0 and peek(super_sections).depth > depth:
      super_section.pop()
    super_section = peek(super_sections)
    section = Section(match.group('title'), match.group('content'), super_section, [], depth)
    if super_section is not None:
      super_section.parent += [section]
    sections += [section]
  return sections
    

# Automatically read the requests
requests = Page(site, "Project:Request Move#Requests")
#TODO: More general regex? Or manuall reading?
row_regex = re.compile(r"(?:\|\||\n\|)[ \t]*((?:\[\[.*\]\]|(?:\[\[.*\]\]|[^-}])(?:\[\[.*\]\]|[^|\n])*(?:\[\[.*\]\]|[^|\n ])))?")
sections = split_sections(requests.text)
print sections
for tested_section in sections:
  if tested_section.title == "Completed":
    section = tested_section.content
# Get line by line
for row in section.split("|-"):
  elements = [match.group(1) for match in row_regex.finditer(row)]
  if len(elements) == 2:
    elements += ['No reason given.']
  if len(elements) == 3:
    if pywikibot.inputChoice("Move '{}' to '{}'? Reason: {}".format(*elements), ['Yes', 'No'], ['y', 'n'], 'n', y):
      reason = raw_input("What is the reason for moving the page? Input nothing to use current reason.")
      if len(reason) > 0:
        elements[2] = reason
      Page(site, elements[0]).move(newtitle=elements[1], reason=elements[2], movetalkpage=True)
    

images_total = 0
if images_total == 0:
  print("No images found.")
else:
  print("Statistics: {} images, {} ({:.0%}) already marked, {} ({:.0%}) detected, {} ({:.0%}) edited.".format(images_total, images_marked, images_marked / images_total, images_detected, images_detected / images_total, images_edited, images_edited / images_total))
