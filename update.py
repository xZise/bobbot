#!/usr/bin/python
# -*- coding: utf-8  -*-
"""
Checks after an update of Kerbal Space Program if part configuration
files need to be updated, added or moved.

It first searches through the complete GameData/Squad/Parts directory
and catalogues all parts. It then compares every file with the existing
one on the wiki. If it doesn't exists, it searches for the infobox with
the part name to determine the current location on the wiki. It will
move the part configuration then to the new location or upload a new
one. If that file already exists, it updates it.
"""

import pywikibot
import re
import os.path
import sys
from pywikibot import textlib
from pywikibot.page import Page, Category

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

def get_base_length(name):
  """Gets the length of the generic template part"""
  if name[:12] == 'Infobox/Part':
    return 12
  elif name[:7] == 'Partbox':
    return 7
  else:
    return -1

def extract_parent(template):
  if 'parent' in template[1]:
    return template[1]['parent']
  else:
    base_length = get_base_length(template[0])
    sub_name = template[0][base_length:]
    if sub_name in parent_map:
      return parent_map[sub_name]
    else:
      return None

def page_exists(site, name):
  return pywikibot.page.Page(site, name).exists()

def get_templates(site, name):
  page = pywikibot.page.Page(site, name)
  if page.exists():
    return pywikibot.textlib.extract_templates_and_params(page.get())
  else:
    return []

def get_infobox_from_list(templates):
  for template in templates:
    if get_base_length(template[0]) >= 0:
      return template
  return None

def get_infobox(site, name):
  # first try box template
  infobox = get_infobox_from_list(get_templates(site, "{}/Box".format(name)))
  if infobox is None:
    infobox = get_infobox_from_list(get_templates(site, name))
  return infobox

def generate_content(part_name, content):
  return "{{{{Part config|{}|2={}\n}}}}".format(part_name, content.replace("{", "&#123;").replace("}", "&#125;"))

def guess_next_version(version, size=1):
  splitted = version.split('.')
  new_version = splitted[:min(size, len(splitted))]
  while len(new_version) < size:
    new_version.append('0')
  new_version.append(str(int(splitted[size] if size < len(splitted) else '0') + 1))
  return ".".join(new_version)

site = pywikibot.getSite()
p = re.compile(r"Parts/([^/]+)/part\.cfg")
closing_brackets = re.compile(r"(^|[^}])}($|[^}])", re.M)
opening_brackets = re.compile(r"(^|[^{]){($|[^{])", re.M)
title = re.compile(r"^\s*title\s*=\s*(.*)\s*$", re.M)

version = None
root_directory = None
args = iter(pywikibot.handleArgs())
for arg in args:
  if arg == "--version" or arg == "-V":
    version = next(args, None)
    if version is None:
      print "Version without number"
  elif arg == "--directory" or arg == "-d":
    root_directory = next(args, None)
    if root_directory is None:
      print "Root directory not given"

if version is None:
  print("Version is not given.")
  #get version from Template:Check version/Cur and then ++
  current_version_match = re.search(r"<(only)?include(only)?>((?:[0-9]+\.)+[0-9]+)</(only)?include(only)?>.*", Page(site, "Template:Check version/Cur").get())
  if current_version_match:
    if current_version_match.group(1) != current_version_match.group(2) or current_version_match.group(4) != current_version_match.group(5):
      parts = [str(x) for x in range(a.count(".") + 1)]
      if len(parts) < 2:
        parts = [str(x) for x in range(3)]
      parts_default = list(parts)
      parts_default[1] = "1 (default)"
      increment_index = int(pywikibot.inputChoice("Which part of the version number was incremented?", parts_default, parts, '1'))
      if increment_index in [int(x) for x in parts]:
        version = guess_next_version(current_version_match.group(3), increment_index)
        if pywikibot.inputChoice("Guessing next version number: {}?".format(version), ['Yes', 'No'], ['y', 'n'], 'n') == 'n':
          sys.exit(1)
      else:
        sys.exit(1)
    else:
      print("Can't guess the next version. Can't interpret 'Template:Check version/Cur' correctly.")
      sys.exit(1)

comment_new = "+added in {}".format(version)
comment_update = "*update to {}".format(version)

if root_directory is not None:
  if os.path.basename(os.path.abspath(root_directory)) == "Parts" and os.path.exists(os.path.join(os.path.split(os.path.abspath(root_directory))[0], "GameData")):
    root_directory = os.path.join(root_directory, "GameData")
  if os.path.basename(os.path.abspath(root_directory)) == "GameData":
    root_directory = os.path.join(root_directory, "Squad")
  if os.path.basename(os.path.abspath(root_directory)) == "Squad":
    root_directory = os.path.join(root_directory, "Parts")

  if os.path.basename(os.path.abspath(root_directory)) != "Parts":
    print("Invalid path given '{}'".format(root_directory))
    sys.exit(1)

def check_file(root, filename):
  filename = "Parts/{}".format(filename) # might be necessary
  if os.path.getsize(os.path.join(root, filename)) > 1<<20:
    print("Cancelled reading {} because it is larger than 1 MiB.".format(filename))
    return
  f = open(os.path.join(root, filename), 'r')
  content = f.read()
  new_page_content = generate_content(part_name, content)
  target = Page(site, filename)
  if target.exists():
    old_page_content = target.get()
    old_page_content = opening_brackets.sub(r"\1&#123;\2", old_page_content)
    old_page_content = closing_brackets.sub(r"\1&#125;\2", old_page_content)
    pywikibot.showDiff(old_page_content, new_page_content)
    if old_page_content != new_page_content:
      if pywikibot.inputChoice("Do you want to upload the new version of '{}'?".format(filename), ['Yes', 'No'], ['y', 'n'], 'n') == 'y':
        target.text = new_page_content
        target.save(comment=update_comment)
  else:
    match = title.search(content)
    if match:
      part_name = match.group(0)
      infobox = get_infobox(site, part_name)
      if infobox is not None:
        parent = extract_parent(infobox)
        part = infobox[1].get('part')
        if parent is None or part is None:
          print("Unable to determine part configuration for '{}'".format(part_name))
        else:
          source = Page(site, "Parts/{}/{}/part.cfg".format(parent, part))
          if source.exists():
            if pywikibot.inputChoice("Move and update '{}' to '{}'?".format(source.title(), filename), ['Yes', 'No'], ['y', 'n'], 'n') == 'y':
              source.move(newtitle=filename, reason="Renamed part configuration file after update.", deleteAndMove=True)
              source.text = new_page_content
              source.save(comment=comment_update)
          else:
            if pywikibot.inputChoice("Create new page '{}'?".format(filename), ['Yes', 'No'], ['y', 'n'], 'n') == 'y':
              source.text = new_page_content
              source.save(comment=comment_new)
    else:
      print("Unable to determine title name for '{}'".format(filename))

def check_directory(root, sub="", depth=0):
  filenames = os.listdir(os.path.join(root, sub))
  for filename in filenames:
    if os.path.isfile(filename) and filename == "part.cfg":
      check_file(root, os.path.join(sub, filename))
    elif os.path.isdir(filename):
      # Parts = depth of 0, parent = 1, part = 2, part.cfg = 3
      if depth < 3:
        check_directory(root, os.path.join(sub, filename), depth + 1)
      else:
        print("Didn't checked '{}' because the subdirectory depth is already {}".format(os.path.join(root, sub, filename), depth))

if root_directory is None:
  print("Parts directory is not given, don't update part configurations.")
else:
  check_directory(None)
# Update check version
if pywikibot.inputChoice("Should 'Template:Check version/Cur' be updated?", ['Yes', 'No'], ['y', 'n'], 'n') == 'y':
  check_version_cur = Page(site, "Template:Check version/Cur")
  check_version_cur.text = "<onlyinclude>{}</onlyinclude><noinclude>: Newest version available to buy. Needs to be updated when a new version gets released.</noinclude>".format(version)
  check_version_cur.save(comment=comment_update)
new_version = guess_next_version(version)
if pywikibot.inputChoice("Should 'Template:Check version/Rev' be updated?", ['Yes', 'No'], ['y', 'n'], 'n') == 'y':
  check_version_rev = Page(site, "Template:Check version/Rev")
  if check_version_rev.exists():
    if check_version_rev.get().find(new_version) < 0:
      print("Template:Check version/Rev already contains the version {}. Skipped.".format(new_version))
    else:
      lines = check_version_rev.get()
      match = re.compile(r"^\|{}=([1-9][0-9]*)$".format(version), re.M).search(lines)
      if match:
        index = match.end()
        check_version_rev.text = lines[:index] + "\n|{}={}".format(new_version, int(match.group(1)) + 1) + lines[index:]
        check_version_rev.save(comment=comment_update)
      else:
        print("Template:Check version/Rev doesn't contain the current version. Skipped.")
  else:
    print("Template:Check version/Rev doesn't exists. Skipped.")
if pywikibot.inputChoice("Should a check version category for version {} be created?".format(new_version), ['Yes', 'No'], ['y', 'n'], 'n') == 'y':
  check_version_cat = Category(site, "Category:Check version/{}".format(new_version))
  if check_version_cat.exists():
    print("'{}' already exists. Skipped.".format(check_version_cat.title()))
  else:
    check_version_cat.text = "{{{{Check version/Cat|{}}}}}".format(new_version)
    check_version_cat.save(comment=comment_new)
if pywikibot.inputChoice("Should a redirect from {} to the version history be created?".format(version), ['Yes', 'No'], ['y', 'n'], 'n') == 'y':
  version_redirect = Page(site, version)
  if version_redirect.exists():
    print("'{}' already exists. Skipped.".format(version_redirect.title()))
  else:
    version_redirect.text = "#REDIRECT [[Version history#{}]]".format(version)
    print version_redirect.text
    version_redirect.save(comment=comment_update if version_redirect.exists() else comment_new)
