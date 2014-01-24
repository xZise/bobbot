#!/usr/bin/python
# -*- coding: utf-8  -*-
import pywikibot
import re
from pywikibot import catlib, textlib, pagegenerators

parent_map = {
  'Engine/Solid': 'Engine',
  'Engine/Liquid': 'Engine'
}

def extract_parent(template, base_length):
  if 'parent' in template[1]:
    return template[1]['parent']
  else:
    sub_name = template[0][base_length:]
    print sub_name
    if sub_name in parent_map:
      return parent_map[sub_name]
    else:
      return None

site = pywikibot.getSite()
#page = pywikibot.Page(site, u"Bla")
#text = page.get(get_redirect = True)
#print text

p = re.compile(r"Parts/([^/]+/part\.cfg)")
closing_brackets = re.compile(r"(^|[^}])}($|[^}])", re.M)
opening_brackets = re.compile(r"(^|[^{]){($|[^{])", re.M)

cat = catlib.Category(site, 'Category:Part configuration')
gen = pagegenerators.CategorizedPageGenerator(cat)
for page in gen:
  print("==========================================")
  m = p.search(page.title())
  if m:
    print("Working on page: '{}'".format(page.title()))
    sub_name = m.groups()[0]
    text = page.get()
    print text.splitlines()[0]
    entity_text = closing_brackets.sub(r"\1&#125;\2", text)
    entity_text = opening_brackets.sub(r"\1&#123;\2", entity_text)
    templates = textlib.extract_templates_and_params(entity_text)
    print "Params:", str(templates)[:100]
    part_config_count = 0
    for template in templates:
      if template[0] == 'Part config' and part_config_count == 0:
        part_config_count += 1;
        part_name = template[1]['1']
        if pywikibot.Page(site, part_name + "/Box").exists():
          part_name = part_name + "/Box"
        print part_name
        part_page = pywikibot.Page(site, part_name)
        print part_page.get()
        part_templates = textlib.extract_templates_and_params(part_page.get())
        for part_template in part_templates:
          # Infobox/Part (7+1+4)
          # Partbox      (7)
          if part_template[0][:12] == 'Infobox/Part':
            parent = extract_parent(part_template, 12 + 1)
          elif part_template[0][:7] == 'Partbox':
            parent = extract_parent(part_template, 7 + 1)
            print(part_page.title(), "is using old Partbox template")
        if parent is None:
          print("Unable to determine parent for", part_name)
    if part_config_count != 1:
      print("Multiple {{Part config}} found.")
    if parent is not None:
      print "Parent: ", parent
    print "Parts/{}/{}".format(parent, sub_name)
  else:
    print("Skipped page: '{}'".format(page.title()))
