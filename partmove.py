#!/usr/bin/python
# -*- coding: utf-8  -*-
import pywikibot
import re
from pywikibot import textlib, page
import sys

parent_map = {
  'Adapter': 'Structural',
  'AirIntake': 'Utility',
  'Antenna': 'Utility',
  'Battery': 'Electrical',
  'CommandModule': 'Command',
  'ControlSurface': 'Aero',
  'Decoupler': 'Utility',
  'DockingPort': 'Utility',
  'Engine/Ion': 'Utility',
  'Engine/Liquid': 'Engine',
  'Engine/RCS': 'Utility',
  'Engine/Solid': 'Engine',
  'FuelTank/Jet': 'FuelTank',
  'FuelTank/Liquid': 'FuelTank',
  'FuelTank/RCS': 'FuelTank',
  'Ladder': 'Utility',
  'LandingStrut': 'Utility',
  'Light': 'Utility',
  'Parachute': 'Utility',
  'ReactionWheel': 'Command',
  'RoverWheel': 'Wheel', #verify
  'SAS': 'Command',
  'SolarPanel': 'Electrical',
  'Strut': 'Structural',
  'Wing': 'Aero',
}

def extract_parent(template, base_length):
  if 'parent' in template[1]:
    return template[1]['parent']
  else:
    sub_name = template[0][base_length:]
    print sub_name
    if sub_name in parent_map:
      return parent_map[sub_name]
    else:
      return None

site = pywikibot.getSite()
p = re.compile(r"Parts/([^/]+)/part\.cfg")
closing_brackets = re.compile(r"(^|[^}])}($|[^}])", re.M)
opening_brackets = re.compile(r"(^|[^{]){($|[^{])", re.M)

cat = page.Category(site, 'Category:Part configuration')
for page in cat.articles():
  print("==========================================")
  m = p.search(page.title())
  if m:
    print("Working on page: '{}'".format(page.title()))
    sub_name = m.groups()[0]
    part = None
    text = page.get()
    # extract_templates_and_params doesn't support single "{" and "}"
    # replacing all with the html entities
    entity_text = closing_brackets.sub(r"\1&#125;\2", text)
    entity_text = opening_brackets.sub(r"\1&#123;\2", entity_text)
    templates = textlib.extract_templates_and_params(entity_text)
    part_config_count = 0
    for template in templates:
      if template[0] == 'Part config' and part_config_count == 0:
        part_config_count += 1;
        if len(template) == 2 and '1' in template[1]:
          part_name = template[1]['1']
          if pywikibot.Page(site, part_name + "/Box").exists():
            part_name = part_name + "/Box"
          print("Infobox is in page: '{}'".format(part_name))
          part_page = pywikibot.Page(site, part_name)
          part_templates = textlib.extract_templates_and_params(part_page.get())
          for part_template in part_templates:
            # Infobox/Part (7+1+4)
            # Partbox      (7)
            valid = False
            if part_template[0][:12] == 'Infobox/Part':
              parent = extract_parent(part_template, 12 + 1)
              valid = True
            elif part_template[0][:7] == 'Partbox':
              parent = extract_parent(part_template, 7 + 1)
              valid = True
              print("'{}' is using old Partbox template".format(part_page.title()))
            if valid and 'part' in part_template[1]:
              part = part_template[1]['part']
            if parent is None and valid:
              print part_template
              print("Unable to determine parent for '{}'".format(part_name))
        else:
          print("Part config template without part name.")
    if part_config_count > 1:
      print("Multiple {{Part config}} found.")
    if parent is not None:
      if part is not None and part != sub_name:
        print("Internal part name changed from '{}' to '{}'".format(sub_name, part))
        sub_name = part
      target = "Parts/{}/{}/part.cfg".format(parent, sub_name)
      print("Parent: {}; Target: {}".format(parent, target))
      if pywikibot.Page(site, target).exists():
        print("Didn't moved '{}' to '{}' because it already exists".format(page.title(), target))
      else:
        print("Move '{}' to '{}'".format(page.title(), target))
#        page.move(newtitle=target, reason="Update to new directory system", deleteAndMove=True)
    elif part_config_count == 0:
      print("Unable to determine part name in '{}'".format(page.title()))
  else:
    print("Skipped page: '{}'".format(page.title()))