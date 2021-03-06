#!/usr/bin/python
# -*- coding: utf-8  -*-
"""
Automatically adds a new language to the KSP wiki. It follows
the instructions from http://wiki.kerbalspaceprogram.com/wiki/Kerbal_Space_Program_Wiki:Adding_a_New_Language :

1. Create MediaWiki:langlink-##, where ## is the two-letter language code. The content should be {{mw-langlink|##}}
2. Add {{mp-lang|##}} to Template:Main Page Layout/Language Box.
3. Add ** langlink-##|Language Name to MediaWiki:Sidebar under Languages.
4. Check the templates in Category:Language code templates if the language code needs to be added. 
"""

import pywikibot
import re
import sys
from string import Template
from pywikibot.page import Page, Category
    
import pywikibot
from pywikibot import deprecate_arg
from pywikibot import config
from pywikibot import deprecated
from pywikibot import pagegenerators
from pywikibot.throttle import Throttle
from pywikibot.data import api
from pywikibot.exceptions import *
from pywikibot.site import LoginStatus
def login(self, sysop=False):
	print "hihi"
	"""Log the user in if not already logged in."""
        # check whether a login cookie already exists for this user
        self._loginstatus = LoginStatus.IN_PROGRESS
        if hasattr(self, "_userinfo"):
            del self._userinfo
        self.getuserinfo()
	print self.userinfo['name']
	print self._username[sysop]
	print self.logged_in(sysop)
#        if self.userinfo['name'] == self._username[sysop] and \
#           self.logged_in(sysop):
#            return
        loginMan = api.LoginManager(site=self, sysop=sysop,
                                    user=self._username[sysop])
        if loginMan.password is None:
		print "none"
        print "'" + loginMan.password + "'"

login(pywikibot.getSite())

def insert_alphabetically(page, regex, language_code, new, comment, suffix="\n"):
  """
  Inserts the "new" into the list given in site. Each entry of the list, is matched by
  "regex". This regex must have a group named "code" OR a placeholder named "code" ($code).

  This code is then checked against language_code, and if the current code is after the
  language_code it adds the "new" prior to that. The new entry needs a placeholde named code
  ($code).

  On both "regex" and "new" is string.Template.substitute applied. Any trailing $-signs are
  automatically escaped if not done so.
  """
  if re.search(r"[^$](\$\$)*\$$", regex):
    regex += '$'
  oldtext = page.text
  compiled = re.compile(Template(regex).substitute(code=r'(?P<code>[a-z]{2}(-[a-z]{2})?)', newline=r'(?P<newline>\n)?'), re.M)
  print compiled.pattern
  matches = list(compiled.finditer(oldtext))
  if len(matches) == 0:
    print("No matches found.")
    return False
  else:
    insert_at = 0
    got_to_end = False
    for match in matches:
      if match.group('code') == language_code:
        print("Language is already available")
        return False
      elif match.group('code') > language_code:
        insert_at = match.start()
        break
    else:
      insert_at = match.end()
      got_to_end = True
    try:
      if match.start('newline') < 0:
        suffix = ""
      else:
        suffix = "\n"
    except IndexError:
      pass
    print "here we are {}".format(insert_at)
    print oldtext[insert_at]
    if got_to_end and len(oldtext) > insert_at + len(suffix):
      insert_at += len(suffix)
    if insert_at > 0 and len(oldtext) == insert_at - len(suffix) + 1:
      print "+= {}".format(len(suffix))
      oldtext += suffix
    page.text = oldtext[:insert_at]
    if callable(new):
      page.text += new(language_code, match)
    else:
      page.text += Template(new).substitute(code=language_code) + suffix
    page.text += oldtext[insert_at:]
    print("Changes in {}:".format(page.title()))     
    pywikibot.showDiff(oldtext, page.text)
    if pywikibot.inputChoice("Save changes?", ['Yes', 'No'], ['y', 'n'], 'n') == 'y':
      page.save(comment=comment)
    return True

site = pywikibot.getSite()
language_code = None
args = iter(pywikibot.handleArgs())
for arg in args:
  if arg == "--language" or arg == "-l":
    language_code = next(args, None)
    if language_code is None:
      print "Found language code parameter but no definition"

if language_code is None:
  print("Language code is not given.")
  sys.exit(1)
elif not re.search("^[A-Za-z]{2}(-[A-Za-z]{2})?$", language_code):
  print("Invalid language code format. Must be XX or XX-XX!")
  sys.exit(1)
elif language_code.lower() != language_code:
  language_code = language_code.lower()
  print("Found capital letters in language code. Changed it to '{}'".format(language_code))

comment_new = "+added {}".format(language_code)

mw_langlink = Page(site, "MediaWiki:langlink-{}".format(language_code))
if mw_langlink.exists():
  print("'{}' already exists. Skipped creation.".format(mw_langlink.title()))
else:
  mw_langlink.text = "{{{{mw-langlink|{}}}}}".format(language_code)
  if pywikibot.inputChoice("Create '{}'?".format(mw_langlink.title()), ['Yes', 'No'], ['y', 'n'], 'n') == 'y':
    mw_langlink.save(comment=comment_new)
insert_alphabetically(Page(site, "MediaWiki:Sidebar"), r"^\*\* langlink-$code\|.*$", language_code, "** langlink-$code|{{subst:#language:$code}}", comment_new)

def optional_prefix(code, match=None):
  ret = Template("{{mp-lang|$code}}").substitute(code=code) + "\n"
  if match is None:
    return ret
  elif match.start() == 0:
    return ret + "&middot; "
  else:
    return "&middot; " + ret

if len(language_code) == 5 and pywikibot.inputChoice("Is this a dialect language?", ['Yes', 'No'], ['y', 'n'], 'n') == 'y':
  dialects = Page(site, "Template:Main Page Layout/Language Box/dialects {}".format(language_code[:2]))
  if dialects.exists():
    insert_alphabetically(dialects, r"^(?:&middot; )?{{mp-lang\|$code}}$", language_code, optional_prefix, comment_new)
  else:
    dialects.text = optional_prefix(language_code)
    if pywikibot.inputChoice("Create '{}'?".format(dialects.title()), ['Yes', 'No'], ['y', 'n'], 'n') == 'y':
      dialects.save(comment=comment_new)
  print dialects.text
else:
  insert_alphabetically(Page(site, "Template:Main Page Layout/Language Box"), r"^&middot; {{mp-lang\|$code\|{{{1\|}}}}}$", language_code, "&middot; {{mp-lang|$code|{{{1|}}}}}", comment_new)

code_templates = {
  "lang": (r"$newline\|\s*$code\s*=\s*{{{[a-z]{2}(-[a-z]{2})?\|}}}", "| $code = {{{$code|}}}"),
  "if lang": (r"$newline\|\s*$code", "|$code"),
}

for k, v in code_templates.iteritems():
  cat = Category(site, "Category:BobBot {} type".format(k))
  print("Going through '{}'.".format(cat.title()))
  for article in cat.articles():
    if article.title().startswith("Template:"):
      insert_alphabetically(article, v[0], language_code, v[1], comment_new)
