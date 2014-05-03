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

# Files in these categories are small but no thumbnails
VALID_CATEGORIES = { 'Technology tree node images' }

site = pywikibot.getSite()

# read User:BobBot/Thumbnails
thumb_page = pywikibot.page.Page(site, "User:BobBot/Thumbnails")
content = thumb_page.text
thumb_line = re.compile(r"^{{User:BobBot/thumb\|(File:[^|]*)\|([yn?])\|([0-9a-fA-F]{32})}}$", re.M)
start = content.find("BOBBOT EDIT START") #new line after this
end = content.find("BOBBOT EDIT END") #new line before this
entries = thumb_line.findall(content[start:end])
remaining = []
for entry in entries:
    if entry[1] not in ["y", "n"]:
        remaining += entry
    else:
        image_page = pywikibot.page.ImagePage(site, entry[0])

print entries
raise Exception()

names = re.compile("^.*\.(?:png|gif|jpg|jpeg)$", re.I)
yes_all = False
for arg in pywikibot.handleArgs():
  if arg in ["--all", "-a"]:
    yes_all = True

images_total = 0
images_marked = 0
images_detected = 0
images_edited = 0
#Maximum size is 20 KiB (20×2²⁰ bytes)
for image in site.allimages(maxsize=20*2<<10):
  images_total += 1
  if names.match(image.title()):
    content = image.text
    templates = textlib.extract_templates_and_params(content)
    for template in templates:
      if template[0].lower() in ["nothumbnailsplease", "no thumbnails please"]:
        print("Already contain template in '{}'. Skipped.".format(image.title()))
        images_marked += 1
        break
      elif template[0].lower() == "is not thumbnail":
        print("Image '{}' is not a thumbnail. Skipped.".format(image.title()))
        images_marked += 1
        break;
    else:
      valid = []
      for c in image.categories():
        if c.title(withNamespace=False) in VALID_CATEGORIES:
          valid += [c.title(withNamespace=False)]
      if valid:
        print("Image '{}' is in valid categories '{}'. Skipped.".format(image.title(), "', '".join(valid)))
        images_marked += 1
        size = None
      else:
        # for didn't find
        image_data = urllib2.urlopen(image.fileUrl()).read()
        size = get_image_size(image_data)
        if size:
          # the values are switched for the second statement
          if size[0]/size[1] > 0.4 and size[1]/size[0] > 0.4 and (size[0] < 100 or size[1] < 100):
            images_detected += 1
            if not yes_all:
              answer = pywikibot.inputChoice("Add template to '{}'?".format(image.title()), ['Yes', 'No', 'Mark', 'All'], ['y', 'n', 'm', 'a'], 'n')
              if answer == 'a':
                yes_all = True
            if answer == 'm':
              image.text = content + "\n{{Is not thumbnail|" + hashlib.md5(image_data).hexdigest() + "}}"
              image.save(comment="+add 'is not thumbnails' template;")
              print("Edited page '{}'.".format(image.title()))
              images_edited += 1
            elif yes_all or answer != 'n':
              image.text = "{{No thumbnails please}}\n" + content
              image.save(comment="+add 'no thumbnails please' template;")
              print("Edited page '{}'.".format(image.title()))
              images_edited += 1
        else:
          print("Unable to determine size of '{}'! Skipped.".format(image.title()))
if images_total == 0:
  print("No images found.")
else:
  print("Statistics: {} images, {} ({:.0%}) already marked, {} ({:.0%}) detected, {} ({:.0%}) edited.".format(images_total, images_marked, images_marked / images_total, images_detected, images_detected / images_total, images_edited, images_edited / images_total))
