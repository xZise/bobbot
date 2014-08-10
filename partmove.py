#!/usr/bin/python
# -*- coding: utf-8  -*-
import pywikibot
import re
from pywikibot import textlib
from pywikibot.page import Page, Category
import mwparserfromhell

# update both maps
type_map = {
    'lfe': 'Engine',
    'cm': 'Command',
    'sep': 'Utility',
    'int': 'Utility',
    'win': 'Aero',
    'ant': 'Utility',
    'lft': 'FuelTank',
    'cs': 'Aero',
    'sen': 'Utility',
    'xgt': 'FuelTank',
    'cp': 'Command',
    'ie': 'Engine',
    'pod': 'Command',
    'rov': 'Utility',
    'rw': 'Command',
    'nc': 'Aero',
    're': 'Utility',
    'rcs': "Utility",
    'sas': 'Command',
    'chu': 'Utility',
    'ada': 'Utility',
    'pan': 'Electrical',
    'lan': 'Utility',
    'exp': 'Science',
    'lad': 'Utility',
    'lab': 'Science',
    'mpt': 'FuelTank',
    'lig': 'Utility',
    'let': 'Aero',
    'je': 'Engine',
    'dp': 'Utility',
    'srb': 'Engine',
    'bat': 'Electrical',
    'str': 'Structural',
    'dec': 'Utility',
}
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

def extract_from_name(template, base_length):
    sub_name = template.name[base_length:].strip()
    if sub_name in parent_map:
        return parent_map[sub_name]
    else:
        return None

pywikibot.handleArgs()
site = pywikibot.getSite()
p = re.compile(r"Parts/([^/]+)/part\.cfg")

def extract_from_page(page):
    if page.exists():
        parsed = mwparserfromhell.parse(page.text)
        parents = []
        for template in parsed.filter_templates(recursive=False):
            if template.name.strip()[:13] == "Infobox/Part/":
                parent = extract_from_name(template, 13)
            elif template.name.strip()[:8] == "Partbox/":
                parent = extract_from_name(template, 8)
            elif template.name.strip() == "Infobox/Part":
                parent = None
            else:
                continue
            if template.has("parent"):
                parent = template.get("parent").value.strip()
            elif template.has("type"):
                if template.get("type").value.strip() in type_map:
                    parent = type_map[template.get("type").value.strip()]
                else:
                    print("ERROR: Unknown type '{}'".format(template.get("type").value.strip()))
            if parent:
                parents += [parent]
            else:
                print("ERROR: Unable to determine parent for a template in '{}'".format(page.title()))
        if len(parents) == 1:
            return parents[0]
        else:
            return None
    else:
        return None


cat = Category(site, 'Category:Part configuration files')
for page in cat.articles():
  m = p.match(page.title())
  if m:
    print("==========================================")
    print("Working on page: '{}'".format(page.title()))
    part_name = m.group(1)
    parsed = mwparserfromhell.parse(page.text)
    templates = parsed.filter_templates()
    text_name = []
    for template in templates:
        if template.name == "Part config":
            if template.has("1"):
                text_name += [template.get("1")]
            else:
                text_name += [None]
    if len(text_name) == 1:
        text_name = str(text_name[0])
        box_page = Page(site, text_name + "/Box")
        if not box_page.exists():
            print("WARNING: The infobox page {} does not exist.".format(box_page.title()))
        box_parent = extract_from_page(box_page)
        part_page = Page(site, text_name)
        part_parent = extract_from_page(part_page)
        if not box_parent and not part_parent:
            print("ERROR: Unable to determine part parent")
        elif bool(box_parent) != bool(part_parent) or box_parent == part_parent:
            parent = box_parent or part_parent
            target = "Parts/{}/{}/part.cfg".format(parent, part_name)
            print("Parent: {}; Target: {}".format(parent, target))
            if Page(site, target).exists():
                print("Didn't moved '{}' to '{}' because it already exists".format(page.title(), target))
            else:
                print("Move '{}' to '{}'".format(page.title(), target))
                page.move(newtitle=target, reason="Update to new directory system", deleteAndMove=True)
        elif box_parent and part_parent:
            print("ERROR: Two parents identified but differing: {} and {}".format(box_parent, part_parent))
    else:
        print("ERROR: Found multiple part config templates")
