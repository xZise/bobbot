#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import os.path
import codecs

"""
A module is one basic block within curly brackets:

    PART
    {

    }

It contains two lists:
 - All value associations (name = RAPIER)
 - All submodules containing objects of this class
"""
class Module(object):
    GET_ALL = False
    GET_SINGLE = 1
    GET_SAME = 2

    def __init__(self, name, parent):
        self._name = name
        self._parent = parent
        self._attributes = []
        self._modules = []
        if self._parent:
            self._parent._modules.append(self)

    @property
    def name(self):
        return self._name

    @property
    def parent(self):
        return self._parent

    @property
    def is_root(self):
        return self._parent is None

    @property
    def attributes(self):
        return iter(self._attributes)

    @property
    def attribute_count(self):
        return len(self._attributes)

    @property
    def modules(self):
        return iter(self._modules)

    def module(self, index):
        return self._modules[index]

    @property
    def module_count(self):
        return len(self._modules)

    """
    Returns the attributes with the given name.

    The single_only parameter can be:
        - GET_ALL (or False): Returns a list all values given by the name
        - GET_SAME: Returns the entry if all entries found are the same, otherwise None (multiple entries with different values OR no entries at all)
        - GET_SINGLE: Returns the value if there is only one entry with that name, otherwise None
    It returns a list in GET_ALL and only the value otherwise.
    """
    def get(self, name, single_only=GET_SAME):
        found = []
        for entry in self.attributes:
            if name == entry[0]:
                found.append(entry[1])
        if single_only:
            if len(found) == 1:
                return found[0]
            elif len(found) > 1 and single_only == GET_SAME:
                first = None
                for entry in found:
                    if not first:
                        first = entry
                    elif first != entry:
                        return None
            else:
                return None
        else:
            return found

commentary = re.compile(r"^[ \t]*//.*$")
section_matcher = re.compile(r"^([ \t]*)(\w+)[ \t]*({)?[ \t]*$")
value_matcher = re.compile(r"^[ \t]*(\w+)[ \t]*=[ \t]*(.*[^ \t])[ \t]*$")
bracket_matcher = re.compile(r"^([ \t]*){[ \t]*$")

def read(content, root_list=False, module_same_indentation=False, return_actual_module=True):
    if content.startswith(codecs.BOM_UTF8):
        content = content[3:]
    content = content.splitlines()
    possible_section = None
    current = root = Module(None, None)
    for line in content:
        if not commentary.match(line):
            value_match = value_matcher.match(line)
            if value_match:
                possible_section = None
                if not current.is_root or root_list:
                    current._attributes.append(tuple(value_match.groups()))
            else:
                section_match = section_matcher.match(line)
                if section_match:
                    if section_match.group(3):
                        current = Module(section_match.group(2), current)
                    else:
                        possible_section = (len(section_match.group(1)), section_match.group(2))
                elif possible_section:
                    bracket_match = bracket_matcher.match(line)
                    if bracket_match and (len(bracket_match.group(1)) == possible_section[0] or not module_same_indentation):
                        current = Module(possible_section[1], current)
                else:
                    count = line.count("}")
                    while count > 0 and not current.is_root:
                        count -= 1
                        current = current.parent
    if return_actual_module:
        if root.attribute_count > 0:
            raise Exception("Root module has a non empty attributes list.")
        if root.module_count > 1:
            raise Exception("Root module has multiple modules.")
        if root.module_count == 0:
            raise Exception("Root module has no modules.")
        root = root.module(0)
    return root

def read_configuration(filename, root_list=False, module_same_indentation=False, return_actual_module=True):
    root = None
    if os.path.isdir(filename):
        filename = os.path.join(filename, "part.cfg")
    with open(filename) as f:
        content = f.read()
    return read(content, root_list, module_same_indentation, return_actual_module)
