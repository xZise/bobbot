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

# read User:BobBot/Thumbnails
def read_edit_table(site, page_name):
    page = pywikibot.page.Page(site, page_name)
    content = page.text
    start = content.find("BOBBOT EDIT START")
    if start >= 0:
        start = content.find("-->", start) #new line after this
        if start >= 0:
            new_line_found = False
            while start < len(content):
                new_line = content[start] in ["\n", "\r"]
                if new_line_found and not new_line:
                    break;
                elif not new_line_found:
                    new_line_found = new_line
                start += 1
    end = content.find("BOBBOT EDIT END") #new line before this
    if end >= 0 and start >= 0:
        end = content.rfind("<!--", start, end)
        if end >= 0:
            while end > 0:
                if content[end - 1] in ["\n", "\r"]:
                    break;
                end -= 1
    return (page, content[start:end], start, end)

def splice_edit_table(table_data, content, overwrite=True):
    end = table_data[2 if overwrite else 3] #use [:end] ... [end:] to not overwrite
    table_data[0].text = table_data[0].text[:end] + content + table_data[0].text[table_data[3]:]
