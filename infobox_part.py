#!/usr/bin/python
# -*- coding: utf-8  -*-
from __future__ import unicode_literals
import pywikibot
import re
import mwparserfromhell
from pywikibot import textlib
import types
import ksp_util

site = pywikibot.getSite()
infobox_page = re.compile("^.*/Box$")
yes_all = False
for arg in pywikibot.handleArgs():
  if arg in ["--all", "-a"]:
    yes_all = True

def tank_check(type_name, name, parameters):
    # check resources
    return name == "tank"

def cm_check(type_name, name, parameters):
    if name == "command module":
        if type_name == "cm":
            return float(parameters.get("power consumption", 0.0)) > 0
        elif type_name in ["cp", "pod"]:
            return int(parameters.get("crew", 0)) > 0
    else:
        return False

# Type structure:
# (TYPE_NAME, Required sub templates, [Allowed sub templates], [Not allowed sub templates])
# If allowed is an empty list, doesn't allow other templates than required
# If allowed is None, does obey the not allowed list
# If not allowed is an empty list, does allow all other templates
# If not allowed is None, doesn't allow other templates than required (same as allowed set to [])
# Entries with empty required sub templates will be ignored (they are only there to know which types are legit)
TYPES = {
    "lfe": (["reaction engine"], [], ["thrust vectors"]),
    "srb": (["solid fuel engine"], [], []),
    "je":  (["jet engine"], [], []),
    "ie":  (["ion engine"], [], []),
    "lft": ([("tank", tank_check)], [], []),
    "re":  (["thrust vectors", "reaction engine"], [], []),
    "sas": (["SAS"], [], []),
    "rw":  (["torque"], [], []),
    "cm":  ([("command module", cm_check)], ["energy storage"], []),
    "cp":  ([("command module", cm_check)], ["energy storage"], [], ["cockpit"]),
    "pod": ([("command module", cm_check)], ["energy storage"], []),
    "lab": (["laboratory"], [], []),
    "exp": (["sensor"], [], []),
    "sen": (["sensor"], [], []),
    "ada": ([], [], []),
    "ant": (["antenna"], [], []),
    "int": (["air intake"], [], []),
    "sep": (["separator"], [], [], ["separator"]),
    "dec": (["separator"], [], []),
    "bat": (["energy storage"], [], []),
    "pan": (["solar panel"], [], []),
    "rov": (["rover wheel"], [], []),
    "dp":  ([], [], []),
    "chu": ([], [], []),
    "lad": ([], [], []),
    "lan": ([], [], []),
    "lig": ([], [], []),
    "nc":  ([], [], []),
    "cs":  (["control surface"], ["winglet"], []),
    "win": ([], [], []),
    "let": (["winglet"], [], []),
    "str": ([], [], []),
}
WATCHED = set()
for type_tuple in TYPES.itervalues():
    for i in range(0,2):
        for e in type_tuple[i] if type_tuple[i] else []:
            WATCHED.add(e[0] if type(e) is tuple else e)

def matches(type_name, e, sub_template):
    if type(e) is not tuple:
        e = (e, None)
    if e[0] == sub_template[0]:
        if e[1] is not None:
            return e[1](type_name, sub_template[0], sub_template[1])
        else:
            return True
    else:
        return False

"""
lfe Engine     {{Infobox/Part/reaction engine}}
srb            {{Infobox/Part/solid fuel engine}}
je             {{Infobox/Part/jet engine}}
ie             {{Infobox/Part/ion engine}}
lft FuelTank   {{Infobox/Part/tank}}
re  Command    {{Infobox/Part/reaction engine}}, {{Infobox/Part/thrust vectors}}
sas            {{Infobox/Part/SAS}}
rw             {{Infobox/Part/torque}}
cm             {{Infobox/Part/command module}} (crew == 0)
cp             !!
pod            !!
lab Science    {{Infobox/Part/laboratory}}
exp            {{Infobox/Part/sensor}}
sen Utility    !!
ada            (not yet)
ant            {{Infobox/Part/antenna}}
int            {{Infobox/Part/air intake}}
dec            {{Infobox/Part/separator}}
sep            !!
bat            {{Infobox/Part/energy storage}}
pan            {{Infobox/Part/solar panel}}
rov            {{Infobox/Part/rover wheel}}
dp             (n/a)
chu            (not yet)
lad            (not yet)
lan            (not yet)
lig            (not yet)
nc  Aero       (n/a)
cs             {{Infobox/Part/control surface}}
win            (not yet)
let            {{Infobox/Part/winglet}}
str Structural (n/a) 
"""

def get_entry_string(entries):
    s = ""
    for entry in entries:
        s += "{{" + "User:BobBot/Types/entry|{}|{}|{}".format(entry[0], entry[1], entry[2]) + "".join(["|{}".format(guess) for guess in entry[3]]) + "}}\n"
    return s

# Order of parameter names:
ORDER = {
    "name": 0,
    "file": 1,
    "role": 2,
    "type": 3,
    "size": 4,
    "size2": 5,
    "manufacturer": 6,
    "costs": 7,
    "mass": 8,
    "lf": 9,
    "ox": 10,
    "mp": 11,
    "sf": 12,
    "xg": 13,
    "ia": 14,
    "drag": 15,
    "drag type": 16,
    "temp": 17,
    "tolerance": 18,
    "research": 19,
    "since": 20,
    "part": 21,
    "parent": 22,
    "more": 23,
    "notes": 24,
    "nref": 25,
}

def save_read(template, parameter, default=None):
    if template.has(parameter):
        return unicode(template.get(parameter).value).strip()
    else:
        return default

def save_save(page, comment):
    page.save(comment=comment)
#    print("Would've saved '{}' with comment '{}'".format(page.title(), comment))
#    print(page.text)

# Read all entries in User:BobBot/Types, and cache valid (types contain only one), the rest can be ignored (they will be either rediscovered in the next step or might be solved otherwise)
entry_line = re.compile(r"^{{User:BobBot/Types/entry\|([^|]*)\|([^|]*)\|([^|]*)\|[ \t]*([a-zA-Z]{2,3})[| \t]*}}$", re.M)
table_data = ksp_util.read_edit_table(site, "User:BobBot/Types")
entries = entry_line.findall(table_data[1])
manual_type = {}
# 0=file, 1=title, 2=desc, 3=type
for entry in entries:
    # valid type
    if entry[3].lower() in TYPES:
        manual_type[entry[1]] = entry[3].lower()

print("Found '{}' element(s) which were typed manually.".format(len(manual_type)))

# each entry:
# failure/successes = (IMAGE, TITLE, REASON, SUGGESTIONS)
successes = []
failures = []
try:
    for page in site.allpages():
    #for page in [pywikibot.page.Page(site, p) for p in ["TR-18A Stack Decoupler/Box", "RC-L01 Remote Guidance Unit/Box", "AV-R8 Winglet/Box", "NCS Adapter/Box", "Rockomax Brand Decoupler/Box"]]:
    #for page in [pywikibot.page.Page(site, p) for p in ["Mobile Processing Lab MPL-LG-2/Box"]]:
        if infobox_page.match(page.title()):
            content = mwparserfromhell.parse(page.text)
            templates = content.filter_templates(recursive=False)
            for template in templates:
                if template.name.startswith("Partbox"):
                    partbox_page = pywikibot.page.Page(site, "Template:{}".format(template.name))
                    if partbox_page.isRedirectPage():
                        partbox = partbox_page.getRedirectTarget()
                    else:
                        partbox = False
                        print("Partbox template '{}' does not redirect.".format(template.name))
                else:
                    partbox = False
                if template.name.strip() in ["Infobox/Part", "Partbox"]:
                    part_type, role, parent, mod = save_read(template, "type"), save_read(template, "role"), save_read(template, "parent"), save_read(template, "mod")
#                    part_type = None
                    if part_type and part_type not in TYPES:
                        print("Part type '{}' is not recognised.".format(part_type))
                        old_part_type = part_type
                        part_type = None
                    else:
                        old_part_type = None
                    if not part_type and (bool(role) is not (bool(parent) or bool(mod))): #inconsitent: no type and only role xor parent
                        failures += [(save_read(template, "file", ""), page.title(), "Inconsistent parameters.", [])]
                        valid_guesses = None
                    elif page.title() in manual_type:
                        valid_guesses = [manual_type[page.title()]]
                        successes += [(save_read(template, "file", ""), page.title(), "Updated because the type was manually defined in the [[User:BobBot/Types]] table", valid_guesses)]
                    elif not part_type and not role: #no data at all: can guess
                        more_templates = textlib.extract_templates_and_params(save_read(template, "more", ""))
                        sub_templates = []
                        for more_template in more_templates:
                            sub_template = more_template[0][len("Infobox/Part/"):]
                            if sub_template in WATCHED:
                                sub_templates += [(sub_template, more_template[1])]
                        valid_guesses = []

                        for type_name, type_tuple in TYPES.iteritems():
                            # all in required must be in sub_template
                            required = len(type_tuple[0]) > 0
                            other_templates = []
                            for e in type_tuple[0]:
                                for sub_template in sub_templates:
                                    if matches(type_name, e, sub_template):
                                        break
                                else:
                                    required = False
                                    other_templates += [sub_template]
                            if type_tuple[1] is None and type_tuple[2] is not None: # use not allow list (which is not None)
                                disallowed = False
                                for sub_template in other_templates:
                                    for e in type_tuple[2]:
                                        if matches(type_name, e, sub_template):
                                            disallowed = True
                                allowed = True
                            # if type_tuple[1] is empty: does not allow any other
                            elif (type_tuple[1] is None and type_tuple[2] is None) or len(type_tuple[1]) == 0:
                                # check all sub_templates, if one is NOT in "required"
                                allowed = len(other_templates) == 0
                                disallowed = False
                            elif len(type_tuple[1]) > 0: # some can be allowed
                                allowed = True
                                for sub_template in other_templates:
                                    for e in type_tuple[1]:
                                        if matches(type_name, e, sub_template):
                                            break
                                    else:
                                        allowed = False
                                disallowed = False

                            if required and allowed and not disallowed:
                                valid_guesses += [([type_name] + [type_entry for type_entry in type_tuple])]
                                print valid_guesses
                        
                        all_guesses = [valid_guess[0] for valid_guess in valid_guesses]
                        better_guesses = []
                        worse_guesses = []
                        if len(valid_guesses) > 1:
                            print("Better guess start")
                            for valid_guess in valid_guesses:
                                if len(valid_guess) > 4: #5. name list
                                    print(str(valid_guess) + " has a name list")
                                    for name in valid_guess[4]:
                                        print("Check name " + str(name))
                                        if name in page.title():
                                            print("Match")
                                            better_guesses += [valid_guess]
                                            break
                                    else:
                                        worse_guesses += [valid_guess]
                                if old_part_type and old_part_type in valid_guess[0]:
                                    better_guesses += [valid_guess]
                            if len(better_guesses) == 1:
                                print("Chose '{}' as better guess.".format(better_guesses[0][0]))
                                valid_guesses = better_guesses
                            elif len(valid_guesses) - len(worse_guesses) == 1:
                                valid_guesses = [guess for guess in valid_guesses if guess not in worse_guesses]
                                print("Chose '{}' because others were worse.".format(valid_guesses[0][0]))
                        valid_guesses = [valid_guess[0] for valid_guess in valid_guesses]

                        description = "Guessed '" + "', '".join(valid_guesses) + "' for '{}'".format(page.title())
                        print(description)
                        if len(valid_guesses) == 1:
                            if better_guesses or worse_guesses:
                                description += " from '" + "', '".join(all_guesses) + "' because the name better matched."
                            successes += [(save_read(template, "file", ""), page.title(), description, valid_guesses)]
                        else:
                            if len(valid_guesses) > 1:
                                description = "Multiple guesses found."
                            else:
                                description = "No guess found."
                            failures += [(save_read(template, "file", ""), page.title(), description, valid_guesses)]
                    else:
                        valid_guesses = []
                else:
                    valid_guesses = None
                template_name = partbox.title(withNamespace=False) if partbox else template.name
                if partbox:
                    print("Partbox template '{}' moved to '{}'.".format(template.name.strip(), template_name))
                    template.name = unicode(template.name).replace(template.name.strip(), template_name)
                add_type = valid_guesses and len(valid_guesses) == 1
                if add_type:
                    template.add("type", valid_guesses[0])
                
                if partbox or valid_guesses and len(valid_guesses) == 1:
                    comments = []
                    # reorder parameters
                    if add_type:
                        try:
                            template.params.sort(key=lambda parameter: ORDER[str(parameter.name)])
                        except KeyError as e:
                            print("Unable to sort the parameter '{}' in '{}'".format(e, page.title()))
                        else:
                            comments += [ "*ordered infobox parameters;" ]
                    page.text = unicode(content)
                    if add_type:
                        comments += [ "+type parameter;" ]
                    if partbox:
                        comments += [ "*use infobox/part instead of partbox prefix;" ]
                    save_save(page, " ".join(comments))
finally:
    #update edited pages
    if len(successes) > 0:
        success_table = ksp_util.read_edit_table(site, "User:BobBot/Types/done")
        ksp_util.splice_edit_table(success_table, get_entry_string(successes), False)
        save_save(success_table[0], "+added {} entry/entries;".format(len(successes)))

    failure_table = get_entry_string(failures)

    ksp_util.splice_edit_table(table_data, failure_table)
    #table_data[0].text = table_data[0].text[:table_data[2]] + failure_table + table_data[0].text[table_data[3]:]
    save_save(table_data[0], "*updated to {} entries;".format(len(failures)))
