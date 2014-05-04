#!/usr/bin/python
# -*- coding: utf-8  -*-
from __future__ import division
import pywikibot
import StringIO
import struct
import imghdr

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
