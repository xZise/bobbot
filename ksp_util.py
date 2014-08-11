#!/usr/bin/python
# -*- coding: utf-8  -*-
from __future__ import division
import pywikibot
import StringIO
import struct
import imghdr
import os.path
import mwparserfromhell

# Answer by "Fred the Fantastic": http://stackoverflow.com/a/20380514/473890
# Modified to get a file object directly
def get_image_size(content):
    '''Determine the image type of fhandle and return its size.
    from draco'''
    if len(content) < 24:
        return
    image_type = imghdr.what("", content)
    if image_type == 'png':
        check = struct.unpack('>i', content[4:8])[0]
        if check != 0x0d0a1a0a:
            return
        width, height = struct.unpack('>ii', content[16:24])
    elif image_type == 'gif':
        width, height = struct.unpack('<HH', content[6:10])
    elif image_type == 'jpeg':
        try:
            fhandle = StringIO.StringIO(content)
            fhandle.seek(0) # Read 0xff next
            size = 2
            ftype = 0
            while not 0xc0 <= ftype <= 0xcf:
                fhandle.seek(size, 1)
                byte = fhandle.read(1)
                while ord(byte) == 0xff:
                    byte = fhandle.read(1)
                ftype = ord(byte)
                size = struct.unpack('>H', fhandle.read(2))[0] - 2
            # We are at a SOFn block
            fhandle.seek(1, 1)  # Skip `precision' byte.
            height, width = struct.unpack('>HH', fhandle.read(4))
        except Exception as  e: #IGNORE:W0703
            print e
            return
    else:
        return
    return width, height

class EditTable:
    def __init__(self, site, page_name):
        self.page = pywikibot.page.Page(site, page_name)
        content = self.page.text
        self.start = content.find("BOBBOT EDIT START")
        if self.start >= 0:
            self.start = content.find("-->", self.start) #new line after this
            if self.start >= 0:
                new_line_found = False
                while self.start < len(content):
                    new_line = content[self.start] in ["\n", "\r"]
                    if new_line_found and not new_line:
                        break;
                    elif not new_line_found:
                        new_line_found = new_line
                    self.start += 1
        self.end = content.find("BOBBOT EDIT END") #new line before this
        if self.end >= 0 and self.start >= 0:
            self.end = content.rfind("<!--", self.start, self.end)
            if self.end >= 0:
                while self.end > 0:
                    if content[self.end - 1] in ["\n", "\r"]:
                        break;
                    self.end -= 1
        self.selected = content[self.start:self.end]

    def splice(self, content, overwrite=True):
        start = self.start if overwrite else self.end #use [:end] ... [end:] to not overwrite
        self.page.text = self.page.text[:start] + content + self.page.text[self.end:]

# read User:BobBot/Thumbnails
def read_edit_table(site, page_name):
    o = EditTable(site, page_name)
    return (o.page, o.selected, o.start, o.end)

def splice_edit_table(table_data, content, overwrite=True):
    end = table_data[2 if overwrite else 3] #use [:end] ... [end:] to not overwrite
    table_data[0].text = table_data[0].text[:end] + content + table_data[0].text[table_data[3]:]

"""
Tries to detect the GameData directory from the path.

    - returns GameData if it's directly in that path
    - if there is a Parts directory it's probably a mod,
      so going two directories up

After that only check if it contains the Squad directory,
and returns it.
"""
def get_gamedata(path):
    contents = os.listdir(path)
    if "GameData" in contents:
        directory = os.path.join(path, "GameData")
    elif "Parts" in contents:
        # probably a mod/squad directory
        directory = os.path.join(path, "../../")
    else:
        directory = path
    directory = os.path.abspath(directory)
    if "Squad" in os.listdir(directory):
        return directory
    else:
        raise Exception("GameData directory could not be determined.")



def reverse_maplist(input_map):
    reverse_map = {}
    for k, v in input_map.iteritems():
        if v not in reverse_map:
            reverse_map[v] = []
        reverse_map[v].append(k)
    return reverse_map


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

MOD_MAP = {
    "n": "NASAmission"
}

RESEARCH_MAP = {
    "start": "Start",
    "basicRocketry": "Basic Rocketry",
    "generalRocketry": "General Rocketry",
    "stability": "Stability",
    "survivability": "Survivability",
    "advRocketry": "Advanced Rocketry",
    "generalConstruction": "General Construction",
    "flightControl": "Flight Control",
    "scienceTech": "Science Tech",
    "heavyRocketry": "Heavy Rocketry",
    "fuelSystems": "Fuel Systems",
    "advConstruction": "Advanced Construction",
    "aerodynamicSystems": "Aerodynamics",
    "advFlightControl": "Advanced Flight Control",
    "electrics": "Electrics",
    "spaceExploration": "Space Exploration",
    "landing": "Landing",
    "heavierRocketry": "Heavier Rocketry",
    "specializedConstruction": "Specialized Construction",
    "actuators": "Actuators",
    "supersonicFlight": "Supersonic Flight",
    "specializedControl": "Specialized Control",
    "precisionEngineering": "Precision Engineering",
    "advElectrics": "Advanced Electrics",
    "advExploration": "Advanced Exploration",
    "advLanding": "Advanced Landing",
    "nuclearPropulsion": "Nuclear Propulsion",
    "advMetalworks": "Advanced MetalWorks",
    "composites": "Composites",
    "advAerodynamics": "Advanced Aerodynamics",
    "highAltitudeFlight": "High Altitude Flight",
    "largeControl": "Large Control",
    "unmannedTech": "Unmanned Tech",
    "ionPropulsion": "Ion Propulsion",
    "largeElectrics": "Large Electrics",
    "electronics": "Electronics",
    "fieldScience": "Field Science",
    "veryHeavyRocketry": "Very Heavy Rocketry",
    "metaMaterials": "Meta-Materials",
    "heavyAerodynamics": "Heavy Aerodynamics",
    "hypersonicFlight": "Hypersonic Flight",
    "advUnmanned": "Advanced Unmanned Tech",
    "specializedElectrics": "Specialized Electrics",
    "advScienceTech": "Advanced Science Tech",
    "advancedMotors": "Advanced Motors",
}
REVERSE_RESEARCH_MAP = {v: k for k, v in RESEARCH_MAP.iteritems()}

def get_parent(template):
    template_name = template.name.strip()
    parent = None
    if len(template_name) > 12 and template_name[12] == "/":
        sub_name = template_name[13:]
        if sub_name == "Strut": # the only template not converted
            parent = "Structural"
        else:
            print("Unrecognized subtemplate '{}'".format(sub_name))
    if template.has("parent"):
        parent = template.get("parent").value.strip()
    elif template.has("type"):
        if template.get("type").value.strip() in type_map:
            parent = type_map[template.get("type").value.strip()]
        else:
            print("ERROR: Unknown type '{}'".format(template.get("type").value.strip()))
    if not parent:
        print("ERROR: Unable to determine parent for a template in '{}'".format(page.title()))
    return parent


def extract_from_page(page):
    if page.exists():
        parsed = mwparserfromhell.parse(page.text)
        infoboxes = []
        for template in parsed.filter_templates(recursive=False):
            if template.name.strip()[:12] == "Infobox/Part":
                infoboxes += [template]
        if len(infoboxes) == 1:
            return infoboxes[0], parsed
        else:
            return None, parsed
    else:
        return None, parsed


def get_part_infobox(site, part_name):
    box_page = pywikibot.page.Page(site, part_name + "/Box")
    box_infobox, box_parsed = extract_from_page(box_page)
    part_page = pywikibot.page.Page(site, part_name)
    part_infobox, part_parsed = extract_from_page(part_page)
    if not box_page.exists():
        if not part_page.exists():
            raise pywikibot.NoPage(box_page, box_parsed)
        print("WARNING: The infobox page {} does not exist.".format(box_page.title()))
    # only one must be defined
    if not box_infobox and not part_infobox:
        print("ERROR: Neither the part nor box page contain an infobox.")
        return (None, box_page, box_parsed)
    elif box_infobox and part_infobox:
        print("ERROR: Both part and box page contin an infobox.")
        return (None, box_page, box_parsed)
    else:
        return (box_infobox or part_infobox, box_page if box_infobox else part_infobox, box_parsed if box_infobox else part_parsed)
