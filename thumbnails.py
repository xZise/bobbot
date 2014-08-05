#!/usr/bin/python
# -*- coding: utf-8  -*-
from __future__ import division
import pywikibot
import re
from pywikibot import textlib
from pywikibot import page
import urllib2
import StringIO
import struct
import imghdr
import hashlib
import ksp_util

import mwparserfromhell

# Files in these categories are small but no thumbnails
VALID_CATEGORIES = { 'Technology tree node images' }

site = pywikibot.getSite()

def set_hash(template, image_hash):
    if template.has("1"):
        for param in template.params:
            if param.name == "1":
                param.value = image_hash
                break
    else:
        template.add("1", image_hash)

def no_template_or_param_inequal(template, param, value, accept_empty=True):
    return not template or (accept_empty and not template.has(param, ignore_empty=True) ) or (template.has(param, ignore_empty=True) and template.get(param).lower() != value)

log_entries = []

names = re.compile("^.*\.(?:png|gif|jpg|jpeg)$", re.I)
handled = set()

def check_image(image, handled):
    if image.title() not in handled and names.match(image.title()):
        handled.add(image.title())
        image_data = urllib2.urlopen(image.fileUrl()).read()
        new_hash = hashlib.md5(image_data).hexdigest().lower()
        valid = []
        for category in image.categories():
            if category.title(withNamespace=False) in VALID_CATEGORIES:
                valid += [category.title(withNamespace=False)]
        if valid:
            print("Image '{}' is in valid category/categories '{}'. Skipped.".format(image.title(), "', '".join(valid)))
        else:
            parsed = mwparserfromhell.parse(image.text)
            try:
                templates = parsed.ifilter_templates(recursive=mwparserfromhell.wikicode.RECURSE_OTHERS)
            except AttributeError: #mwparserfromhell v0.4 required, "dummy" mode might work too:
                templates = parsed.ifilter_templates(recursive=True)
            concerned_templates = [template for template in templates if template.name.lower() in ["nothumbnailsplease", "no thumbnails please", "is not thumbnail"]]
            if len(concerned_templates) > 1:
                print("CONFLICT! Multiple thumbnail templates for image '{}'.".format(image.title()))
                log_entries.append((image.title(), "c", new_hash))
                pass
            else:
                concerned_template = concerned_templates[0] if concerned_templates else None
                # Das "nicht leer" ist optional deaktivierbar
                if no_template_or_param_inequal(concerned_template, "1", new_hash):
                    if no_template_or_param_inequal(concerned_template, "2", "skip"):
                        size = ksp_util.get_image_size(image_data)
                        if size:
                            # the values are switched for the second statement
                            is_thumbnail = size[0]/size[1] > 0.4 and size[1]/size[0] > 0.4 and (size[0] < 100 or size[1] < 100)
                            if is_thumbnail:
                                print("Image '{}' fit's size constraints.".format(image.title()))
                        else:
                            is_thumbnail = None #wtf?
                            print("Unable to determine size of '{}'! Skipped.".format(image.title()))
                    else:
                        is_thumbnail = concerned_template.name.lower() != "is not thumbnail"
                    if is_thumbnail is not None:
                        if concerned_template:
                            # it was a thumbnail, but the new one isn't anymore
                            if concerned_template.name.lower() != "is not thumbnail" and not is_thumbnail:
                                comment = "-is no thumbnail anymore;"
                                #TODO: Remove template: Does ↓ work?
                                parsed.remove(concerned_template) # noinclude remove too?
                                log_entries.append((image.title(), "-", new_hash))
                            else:
                                set_hash(concerned_template, new_hash)
                                comment = "*update thumbnail template hash;"
                                if is_thumbnail and concerned_template.name.lower() == "is not thumbnail":
                                    concerned_template.name = "No thumbnails please"
                                    comment += " *changed to marked as thumbnail;"
                                    log_entries.append((image.title(), "++", new_hash))
                                else:
                                    log_entries.append((image.title(), "*", new_hash))
                            image.text = unicode(parsed)
                            image.save(comment=comment)
                        elif is_thumbnail:
                            image.text = "{{No thumbnails please|" + new_hash + "}}" + image.text
                            image.save(comment="+no thumbnails please template;")
                            log_entries.append((image.title(), "+", new_hash))

for image in page.Category(site, "Category:Image thumbnails").articles(namespaces=6):
    check_image(page.ImagePage(image), handled)

print("Finished checking already marked images. Search for new images.")

for image in site.allimages(maxsize=20*2<<10):
    check_image(image, handled)

if log_entries:
    table = ksp_util.EditTable(site, "User:BobBot/The Thumbnail Job")

    log_entries.sort(key=lambda entry: entry[0])
    line = "\n".join([ "{{{{User:BobBot/The Thumbnail Job/entry|{}|{}|{}}}}}".format(*log_entry) for log_entry in log_entries ]) + "\n"
    table.splice(line, False)
    table.page.save(comment="+added changes;")
