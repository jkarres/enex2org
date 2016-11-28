import copy
import sys
import xml.etree.ElementTree as ET
import os.path
from contextlib import contextmanager

def enml2xhtml(root, resd):
    """Convert the given ET.Element into html.  Return that html along with
    a set containing the hashes of the resources that were incorporated
    into that html (so we don't bother writing them out as attachments
    unnecessarily).

    root -- the ET.Element
    resd -- the hash->resource dict
    """
    used_resource_hashes = set()
    for elt in root.iter():
        if elt.tag == 'en-note':
            elt.tag = 'body'
        elif elt.tag == 'en-media':
            used_resource_hashes.add(elt.attrib['hash'])
            mime_type = elt.attrib.get('type', '/')
            data_str = 'data:{};base64,{}'.format(
                mime_type,
                resd[elt.attrib['hash']].base64data)
            if mime_type.split('/')[0] == 'image':
                elt.tag = 'img'
                elt.attrib['src'] = data_str
            else:
                elt.tag = 'a'
                elt.attrib['href'] = data_str
                elt.text = resd[elt.attrib['hash']].filename
        elif elt.tag == 'en-crypt':
            elt.tag = 'div'
        elif elt.tag == 'en-todo':
            elt.tag = 'div'
    return used_resource_hashes, ET.tostring(root)


INDENT = object()
DEDENT = object()
START_ROW = object()
END_ROW = object()
LIST_ITEM = object()
BEGIN_ORDERED = object()
END_ORDERED = object()
BEGIN_UNORDERED = object()
END_UNORDERED = object()

@contextmanager
def italics(rv, elt, note):
    rv.append('/')
    yield
    rv.append('/')

@contextmanager
def list_item(rv, elt, note):
    rv.append(LIST_ITEM)
    rv.append(INDENT)
    yield
    rv.append(DEDENT)

@contextmanager
def todo(rv, elt, note):
    rv.append('[ ] ')
    yield

@contextmanager
def underline(rv, elt, note):
    rv.append('_')
    yield
    rv.append('_')

@contextmanager
def bold(rv, elt, note):
    rv.append('*')
    yield
    rv.append('*')

@contextmanager
def link(rv, elt, note):
    rv.append('[[')
    rv.append(elt.attrib.get('href', '') or '')
    rv.append('][')
    yield
    rv.append(']]')

@contextmanager
def table_row(rv, elt, note):
    rv.append('\n')
    rv.append(START_ROW)
    yield
    rv.append(END_ROW)

@contextmanager
def table_cell(rv, elt, note):
    rv.append('| ')
    yield

@contextmanager
def table(rv, elt, note):
    rv.append('\n|-')
    yield
    rv.append('\n|-')

@contextmanager
def add_newline(rv, elt, note):
    if rv and rv[-1] and rv[-1][-1] != '\n':
        rv.append('\n')
    yield
    rv.append('\n')

@contextmanager
def horizontal_rule(rv, elt, note):
    rv.append('\n----------\n')
    yield

@contextmanager
def unordered_list(rv, elt, note):
    rv.append(BEGIN_UNORDERED)
    yield
    rv.append(END_UNORDERED)

@contextmanager
def ordered_list(rv, elt, note):
    rv.append(BEGIN_ORDERED)
    yield
    rv.append(END_ORDERED)

@contextmanager
def br(rv, elt, note):
    rv.append('\n')
    yield

@contextmanager
def media(rv, elt, note):
    filename = note.resources[elt.attrib['hash']].filename
    rv.append('[[file:{}][{}]]'.format(
        os.path.join(note.attachment_dir, filename),
        filename))
    yield

@contextmanager
def default(rv, elt, note):
    yield

tag2contextmgr = {
    'i': italics,
    'li': list_item,
    'en-todo': todo,
    'strong': bold,
    'a': link,
    'u': underline,
    'b': bold,
    'tr': table_row,
    'td': table_cell,
    'th': table_cell,
    'table': table,
    'div': add_newline,
    'hr': horizontal_rule,
    'ul': unordered_list,
    'ol': ordered_list,
    'br': br,
    'en-media': media,
}

def note2org(note):
    """Convert the content of a Note object into a string."""
    root = note.content
    resd = note.resources
    def process_elt(elt, rv):
        with tag2contextmgr.get(elt.tag, default)(rv, elt, note):
            if elt.text:
                rv.append(elt.text.replace('\n', ''))
            for c in elt:
                if elt.tag == 'div' and c.tag == 'br':
                    # you'll get stuff like <div><br/></div> where you'll only
                    # want a single newline
                    pass
                else:
                    process_elt(c, rv)
                if c.tail:
                    rv.append(c.tail.replace('\n', ''))

    indent_level = 0 # for keeping track of nested lists
    in_row = False # are we currently in a table row?
    new_strs = [] # we're going to cat these together as our final answer
    lists = [] # used as a stack to track nested sublists
               # an int represents the position in an ordered list
               # a None represents an unordered list
    rv = [] # gets passed through the process_elt function
    process_elt(root, rv)
    for item in rv:
        if item is None:
            continue
        if item is INDENT:
            indent_level += 1
        if item is DEDENT:
            indent_level -= 1
        if item is START_ROW:
            in_row = True
        if item is END_ROW:
            in_row = False
        if item is BEGIN_ORDERED:
            lists.append(1)
        if item is END_ORDERED:
            lists.pop()
        if item is BEGIN_UNORDERED:
            lists.append(None)
        if item is END_UNORDERED:
            lists.pop()
        if item is LIST_ITEM:
            if lists[-1]: # are we in an ordered list?
                item = '\n' + str(lists[-1]) + '. '
                lists[-1] += 1
            else:
                item = '\n- '

        # take care of indentation
        if isinstance(item, str):
            if in_row:
                to_add = item.replace('\n', '')
            else:
                to_add = item.replace('\n', '\n' + '  '*indent_level)
            new_strs.append(to_add)
    return ''.join(new_strs)
