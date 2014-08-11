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
import confignodereader
import ksp_util


def page_exists(site, name):
    return pywikibot.page.Page(site, name).exists()

def generate_content(part_name, content):
    return "{{{{Part config|{}|2={}\n}}}}".format(part_name, content)

def guess_next_version(version, size=1):
    splitted = version.split('.')
    new_version = splitted[:min(size, len(splitted))]
    while len(new_version) < size:
        new_version.append('0')
    new_version.append(str(int(splitted[size]) + 1) if size < len(splitted) else '1')
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
            parts = [str(x) for x in range(3)]
            increment_index = int(pywikibot.inputChoice("Which part of the version number was incremented?", parts, parts, '1'))
            if increment_index in [int(x) for x in parts]:
                version = guess_next_version(current_version_match.group(3), increment_index)
                if pywikibot.inputChoice("Guessing next version number: {}?".format(version), ['Yes', 'No'], ['y', 'n'], 'n') == 'n':
                    sys.exit(1)
            else:
                sys.exit(1)
        else:
            print("Can't guess the next version. Can't interpret 'Template:Check version/Cur' correctly.")
            sys.exit(1)

comment_new = "+added in {};".format(version)
comment_update = "*update to {};".format(version)

if root_directory is not None:
    root_directory = ksp_util.get_gamedata(root_directory)


def join_parts(*args):
    result = "Parts"
    for i in args:
        if i:
            result += "/" + i
    return result


def check_file(root, filename, mod):
    file_path = os.path.join(root, *filename)
    # filename = (parent, part, part.cfg)
    if len(filename) == 2:
        filename = ("", filename[0], filename[1])
    elif len(filename) == 3:
        filename = tuple(filename)
    else:
        raise Exception("Number of filename parts is neither 3 nor 2.")
    if mod == "Squad":
        mod = ""
    page_name = join_parts(mod, *filename)
    if os.path.getsize(file_path) > 1<<20:
        print("Cancelled reading '{}' because it is larger than 1 MiB.".format(filename[1]))
        return
    with open(file_path, 'r') as f:
        content = f.read()
    target = Page(site, page_name)
    root_node = confignodereader.read(content)
    if root_node.name != "PART":
        raise Exception("Root node is not PART")
    part_name = root_node.get("title")
    new_page_content = generate_content(part_name, content)
    try:
        infobox, infobox_page, root_element = ksp_util.get_part_infobox(site, part_name)
    except pywikibot.NoPage as e:
        infobox_page = e.getPage()
        infobox = None
    new_infobox_page = not infobox
    require_type_parent_update = False
    if new_infobox_page:
        # Create new box template
        if infobox_page.title()[-4] != "/Box":
            raise Exception("Tried to create a infobox not in a box page")
        infobox_page.text = "<noinclude>{{Data template used}}<noinclude>\n{{Infobox/Part\n}}"
        infobox, root_element = ksp_util.extract_from_page(infobox_page)
        infobox.add("since", version)
        require_type_parent_update = "The infobox page is newly created."
        old_infobox_content = ""
    else:
        old_infobox_content = infobox_page.text
    parent = ksp_util.get_parent(infobox) or ""
    if target.exists():
        old_page_content = target.get()
        pywikibot.showDiff(old_page_content, new_page_content)
        if old_page_content != new_page_content:
            if pywikibot.inputChoice("Do you want to upload the new version of '{}'?".format(target.title()), ['Yes', 'No'], ['y', 'n'], 'y') == 'y':
                target.text = new_page_content
                target.save(comment=comment_update)
    else:
        if infobox.has("part"):
            part = infobox.get("part")
        else:
            part = filename[1]
        source = Page(site, join_parts(mod, parent, part, "part.cfg"))
        if source.exists():
            if pywikibot.inputChoice("Move and update '{}' to '{}'?".format(source.title(), target.title()), ['Yes', 'No'], ['y', 'n'], 'y') == 'y':
                source.move(newtitle=target.title(), reason="Renamed part configuration file after update.", deleteAndMove=True)
                source.text = new_page_content
                source.save(comment=comment_update)
                require_type_parent_update =("The part.cfg has been moved, "
                                             "but the infobox doesn't link to "
                                             "it anymore.")
        else:
            if pywikibot.inputChoice("Create new page '{}'?".format(target.title()), ['Yes', 'No'], ['y', 'n'], 'y') == 'y':
                target.text = new_page_content
                target.save(comment=comment_new)
                require_type_parent_update =("The part.cfg has been created, "
                                             "but the infobox doesn't link to "
                                             "it yet.")

    if require_type_parent_update:
        # new probable type
        options = [("Manually", "m")]
        valid_types = None
        if filename[0]:
            types = ksp_util.reverse_maplist(ksp_util.type_map).get(filename[0])
            options += [("Parent", "p"), ("Type", "t")]
        print("The infobox for '{}' requires attention.".format(part_name))
        if len(options) == 1:
            print(require_type_parent_update)
            print("The infobox can't be configured to point to the "
                  "part.cfg. Please fix this manually.")
        else:
            #infobox must be updated: Either type or parent and maybe part
            answers, hotkeys = zip(*options)
            choice = pywikibot.inputChoice(
                        require_type_parent_update + " What should be "
                        "set?", answers, hotkeys, "m")
        if choice == "t":
            types += ["Other"]
            hotkeys = ["o"] + range(1, len(types))
            # which type?
            if len(types) > 1:
                type_idx = pywikibot.inputChoice(
                            "Choose the new type or 'other' if none "
                            "applies to this part.", types, hotkeys)
            else:
                type_idx = "o"
            if type_idx == "o":
                types = ["None"] + ksp_util.type_map.keys()
                hotkeys = ["n"] + range(1, len(all_types))
                type_idx = pywikibot.inputChoice(
                            "Choose the new type. It'll set the parent "
                            "directly if 'none' is chosen.", types, hotkeys)
            if type_idx != "n":    
                new_type = types[int(type_idx)]
                infobox.add("type", new_type)
            else:
                choice = "p"

        if choice == "p":
            infobox.add("parent", filename[0])
        infobox.add("part", filename[1])
        if mod:
            mod_short = ksp_util.reverse_maplist(ksp_util.MOD_MAP)[mod][0]
            infobox.add("mod", mod_short)
    # default infobox values

    # manufacturer= requires manufacturer map

    # name pair: (infobox, config)
    default_pairs = [("costs", "cost"), ("mass", "mass"),
                     ("tolerance", "crashTolerance"), ("temp", "maxTemp")]
    for infobox_name, config_name in default_pairs:
        value = root_node.get(config_name)
        if value:
            infobox.add(infobox_name, value)
        else:
            print("Part definition doesn't contain a value for '{}'".format(config_name))
    # special: drag (maximum_drag and minimum_drag)
    min_drag = root_node.get("minimum_drag")
    max_drag = root_node.get("maximum_drag")
    if not min_drag and not max_drag:
        print("Part definition doesn't contain drag values.")
    else:
        min_drag = float((min_drag or max_drag).strip())
        max_drag = float((max_drag or min_drag).strip())
        if abs(min_drag - max_drag) < 0.001:
            infobox.add("drag", "{}".format(min_drag))
        else:
            infobox.add("drag", "{}-{}".format(min_drag, max_drag))
    # special: research
    research = root_node.get("TechRequired")
    if research:
        research_name = ksp_util.RESEARCH_MAP.get(research)
        if research_name:
            infobox.add("research", research_name)
        elif research != "Unresearcheable":  # ignore the "special value"
            print("Unknown research definition: {}".format(research))
    else:
        print("Part definition doesn't contain a research value.")
    infobox_page.text = unicode(root_element)
    if old_infobox_content != infobox_page.text:
        pywikibot.showDiff(old_infobox_content, infobox_page.text)
        if pywikibot.inputChoice("Do you want to upload the new version of '{}'?".format(infobox_page.title()), ['Yes', 'No'], ['y', 'n'], 'y') == 'y':
            infobox_page.save(comment=comment_new if new_infobox_page else comment_update)
            

def check_directory(root, mod, sub):
    for filename in os.listdir(os.path.join(root, *sub)):
        new_sub = sub + [filename]
        complete_path = os.path.join(root, *new_sub)
        if os.path.isfile(complete_path):
            if filename[-4:] == ".cfg":
                check_file(root, new_sub, mod)
        elif os.path.isdir(complete_path):
            # Parts = depth of 0, parent = 1, part = 2, part.cfg = 3
            if len(new_sub) < 3:
                check_directory(root, mod, new_sub)
            else:
                print("Didn't checked '{}' because the subdirectory depth is already {}.".format(complete_path, len(sub)))

if root_directory is None:
    print("Parts directory is not given, don't update part configurations.")
else:
    for mod in ["Squad", "NASAmission"]:
        parts_directory = os.path.join(root_directory, mod, "Parts")
        if os.path.isdir(parts_directory):
            check_directory(parts_directory, mod, [])
        else:
            print("Parts director '{}' does not exists/is not a directory!".format(parts_directory))

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
