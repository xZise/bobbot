#!/usr/bin/python
# -*- coding: utf-8  -*-
from __future__ import division
import pywikibot
import re
from pywikibot import textlib
import urllib2
import StringIO
import struct
import imghdr
import hashlib
import ksp_util

# Files in these categories are small but no thumbnails
VALID_CATEGORIES = { 'Technology tree node images' }

site = pywikibot.getSite()

def find_new_line(string, index, check):
    if index >= 0:
        new_line_found = False
        while check(index, len(string)):
            new_line = string[index] in ["\n", "\r"]
            if new_line_found and not new_line:
                break;
            elif not new_line_found:
                new_line_found = new_line
            start += 1

# read User:BobBot/Thumbnails
thumbs_table = ksp_util.EditTable(site, "User:BobBot/Thumbnails")
thumb_line = re.compile(r"^{{User:BobBot/thumb\|(File:[^|]*)\|([yn?])\|([ac])\|([0-9a-fA-F]{32})}}$", re.M)
hash_regex = re.compile(r"^[0-9a-fA-F]{32}$")
is_thumb_rep = re.compile("{{([Nn]oThumbnailsPlease|[Nn]o thumbnails please)(\|[0-9a-fA-F]{32})?}}")
is_no_thumb_rep = re.compile("{{[Ii]s not thumbnail(\|[0-9a-fA-F]{32})?}}")
entries = thumb_line.findall(thumbs_table.selected)
remainings = []
images_changed = 0
images_is_template = 0
images_not_template = 0
images_updated = 0
images_already_applied = 0
images_conflict = 0
for entry in entries:
    image_page = pywikibot.page.ImagePage(site, entry[0])
    if image_page.exists():
        if entry[1] not in ["y", "n"]:
            remainings += [ entry ]
        else:
            is_thumbnail = entry[1] == "y"
            image_data = urllib2.urlopen(image_page.fileUrl()).read()
            new_hash = hashlib.md5(image_data).hexdigest().lower()
            is_applicable = new_hash.lower() == entry[3].lower() #hash hashn't changed
            content = image_page.text
            templates = textlib.extract_templates_and_params(content)
            is_thumb_hashes = set()
            is_no_thumb_hashes = set()
            for template in templates:
                hashes = None
                if template[0].lower() in ["nothumbnailsplease", "no thumbnails please"]:
                    hashes = is_thumb_hashes
                elif template[0].lower() == "is not thumbnail":
                    hashes = is_no_thumb_hashes
                if "1" in template[1] and hash_regex.match(template[1]["1"]):
                    hashes.add(template[1]["1"])
            if len(is_no_thumb_hashes) == 0 and len(is_thumb_hashes) == 0:
                # automatic
                if not is_applicable:
                    # hash has changed
                    remainings += [ (entry[0], "?", "a", new_hash) ]
                    images_changed += 1
                elif is_thumbnail:
                    image.text = "{{No thumbnails please|" + new_hash + "}}\n" + content
                    #image.save(comment="+add 'no thumbnails please' template;")
                    print("'{}' would've saved:".format(image_page.title))
                    print(image.text)
                    images_is_template += 1
                else:
                    image.text = content + "\n{{Is not thumbnail|" + new_hash + "}}"
                    #image.save(comment="+add 'is not thumbnails' template;")
                    print("'{}' would've saved:".format(image_page.title))
                    print(image.text)
                    images_not_template += 1
            elif len(is_no_thumb_hashes if is_thumbnail else is_thumb_hashes) == 0 and len(is_thumb_hashes if is_thumbnail else is_no_thumb_hashes) == 1:
                # there is already a correct entry, but the hash might need to be updated
                if next(iter(is_thumb_hashes if is_thumbnail else is_no_thumb_hashes)).lower() != new_hash.lower():
                    if is_applicable:
                        # hash has changed, but the answer was for the current hash
                        image.text = (is_thumb_rep if is_thumbnail else is_no_thumb_rep).sub(r"{{" + ("No thumbnails please" if is_thumbnail else "Is not thumbnail") + "|" + new_hash.lower() + "}}", content)
                        #image.save(comment="*update thumbnail template hash;")
                        print("'{}' would've saved:".format(image_page.title))
                        print(image.text)
                        images_updated += 1
                    else:
                        remainings += [ (entry[0], "?", "a", new_hash) ]
                        images_changed += 1
                else:
                    print("Image '{}' is already marked accordingly. No change necessary.".format(image_page.title()))
                    images_already_applied += 1
            else:
                # conflict, please resolve manually
                remainings += [ (entry[0], "?", "c", new_hash) ]
                images_conflict += 1
    else:
        print("Image '{}' does not exists anymore. Skipped.".format(image_page.title()))
        images_already_applied += 1

# Files in these categories are small but no thumbnails
VALID_CATEGORIES = { 'Technology tree node images' }

names = re.compile("^.*\.(?:png|gif|jpg|jpeg)$", re.I)

print("Searching for new thumbnails.")
images_total = 0
images_unmarked = 0
images_detected = 0
images_outdated = 0
images_multiple = 0
#Maximum size is 20 KiB (20×2²⁰ bytes)
for image in site.allimages(maxsize=20*2<<10):
    for remaining in remainings:
        if remaining[0] == image.title():
            in_remaining = True
            break
    else:
        in_remaining = False
    if not in_remaining and names.match(image.title()):
        images_total += 1
        content = image.text
        valid = []
        for c in image.categories():
            if c.title(withNamespace=False) in VALID_CATEGORIES:
                valid += [c.title(withNamespace=False)]
        if valid:
            print("Image '{}' is in valid category/categories '{}'. Skipped.".format(image.title(), "', '".join(valid)))
        else:
            image_data = urllib2.urlopen(image.fileUrl()).read()
            new_hash = hashlib.md5(image_data).hexdigest().lower()
            templates = textlib.extract_templates_and_params(content)
            hashes = set()
            for template in templates:
                if (template[0].lower() in ["nothumbnailsplease", "no thumbnails please"] or template[0].lower() == "is not thumbnail") and "1" in template[1] and template[1]["1"] and hash_regex.match(template[1]["1"]):
                    hashes.add(template[1]["1"])
            if len(hashes) == 0:
                images_unmarked += 1
                size = ksp_util.get_image_size(image_data)
                if size:
                    # the values are switched for the second statement
                    if size[0]/size[1] > 0.4 and size[1]/size[0] > 0.4 and (size[0] < 100 or size[1] < 100):
                        images_detected += 1
                        remainings += [ (image.title(), "?", "a", hashlib.md5(image_data).hexdigest()) ]
                        print("Image '{}' fit's size constraints.".format(image.title()))
                else:
                    print("Unable to determine size of '{}'! Skipped.".format(image.title()))
            elif len(hashes) == 1 and hashes.pop() != new_hash:
                images_outdated += 1
                remainings += [ (image.title(), "?", "a", new_hash) ]
                print("Image '{}' has the thumbnail info set, but with another hash.".format(image.title()))
            elif len(hashes) > 1:
                # conflict, please resolve manually
                images_multiple += 1
                remainings += [ (entry[0], "?", "c", new_hash) ]
                print("Image '{}' has multiple thumbnail info entries.".format(image.title()))
if images_total == 0:
    print("No images found.")
else:
    print("Statistics: {} images, {} ({:.0%}) already unmarked, {} ({:.0%}) detected, {} ({:.0%}) outdated, {} ({:.0%}) multiple.".format(images_total, images_unmarked, images_unmarked / images_total, images_detected, images_detected / images_total, images_outdated, images_outdated / images_total, images_multiple, images_multiple / images_total))

# generate new list
line = "\n".join([ "{{{{User:BobBot/thumb|{}|{}|{}|{}}}}}".format(*remaining) for remaining in remainings ]) + "\n"

thumbs_table.splice(line)
thumbs_table.page.save(comment="+{} outdated; +{} multiple; +{} new; *{} changed; *{} conflicts; -{} already applied; -{} 'is thumbnail'; -{} 'is not thumbnail'; -{} hash updated;".format(images_outdated, images_multiple, images_detected, images_changed, images_conflict, images_already_applied, images_is_template, images_not_template, images_updated))
