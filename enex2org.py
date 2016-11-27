import xml.etree.ElementTree as ET
import base64
import hashlib
from collections import namedtuple, defaultdict
import argparse
import enml
import os
import sys
import uuid

class Resource:
    def __init__(self, base64data, data, mime, filename):
        if base64data is not None:
            self.base64data = base64data
            self.data = base64.b64decode(self.base64data)
        else:
            self.base64data = None
            self.data = data
        self.mime = mime
        md5 = hashlib.md5()
        md5.update(self.data)
        self.hash_ = md5.hexdigest()
        if filename:
            self.filename = filename
        else:
            self.filename = self.hash_ + '.' + self.mime.split('/')[1]

    @staticmethod
    def from_elt(relt):
        base64data = relt.find('data').text or ''
        mime = relt.find('mime').text
        filename_elt = relt.find('resource-attributes/file-name')
        if filename_elt is not None and filename_elt.text:
            filename = filename_elt.text
        else:
            filename = None
        return Resource(base64data, None, mime, filename)

class Note:
    def __init__(self, note_elt):
        self.title = note_elt.find('title').text
        self.content = ET.fromstring(clean(note_elt.find('content').text))
        self.tags = [elt.text for elt in note_elt.findall('tag')]
        self.resources = read_resources(note_elt)
        self.sourceurl = get_sourceurl(note_elt)
        self.uuid = str(uuid.uuid4())
        self.attachment_dir = os.path.join('data', self.uuid[:2], self.uuid[2:])

    def attachmentify(self):
        used_resource_hashes, html = enml.enml2xhtml(self.content, self.resources)
        for hsh in used_resource_hashes:
            del self.resources[hsh]
        note_as_attachment = Resource(None, html, None, 'original.html')
        self.resources[note_as_attachment.hash_] = note_as_attachment

        self.content = ET.Element('en-note')
        self.content.text = 'See '
        ET.SubElement(self.content, 'en-media', {'hash': note_as_attachment.hash_}).tail = ' in attachments. '
        ET.SubElement(self.content, 'a', {'href': self.sourceurl}).text = 'Source URL'

    def write(self, f, outpath):
        if self.resources:
            self.tags.append('ATTACH')

        f.write(format_title_and_tags(self.title, self.tags))

        if self.resources:
            abs_attachment_dir = os.path.join(outpath, self.attachment_dir)
            os.makedirs(abs_attachment_dir)
            filenames = []
            for res_hash, res in self.resources.items():
                filenames.append(res.filename)
                with open(os.path.join(abs_attachment_dir, res.filename), 'wb') as resf:
                    resf.write(res.data)
            f.write(':PROPERTIES:\n')
            f.write(':Attachments: ' + ' '.join(filenames) + '\n')
            f.write(':ID:       ' + self.uuid + '\n:END:\n')
        f.write(enml.enml2str(self))
        f.write('\n')

def iter_notes(enexpath):
    for _, elt in ET.iterparse(enexpath):
        if elt.tag == 'note':
            yield elt
            elt.clear() # release memory

def clean(s):
    s = s.replace('&nbsp;', ' ')
    s = s.replace('\u00A0', ' ')
    return s

def get_sourceurl(note_elt):
    sourceurl_elt = note_elt.find('note-attributes/source-url')
    if sourceurl_elt is not None:
        return sourceurl_elt.text or None
    else:
        return None

def format_title_and_tags(title, tags):
    if tags:
        tag_str = ':' + ':'.join(tags) + ':'
        num_spaces = max(1, 75 - len(title) - len(tag_str))
        return '* ' + title + ' '*num_spaces + tag_str + '\n'
    else:
        return '* ' + title + '\n'

def read_resources(note_elt):
    resources = [Resource.from_elt(resource_elt) for resource_elt in note_elt.findall('resource')]
    ensure_unique_filenames(resources)
    return {r.hash_: r for r in resources}

def ensure_unique_filenames(resources):
    used_filenames = set()
    for res in resources:
        if res.filename in used_filenames:
            suffix = 1
            proposed_filename = res.filename + '_' + str(suffix)
            while proposed_filename in used_filenames:
                suffix += 1
                proposed_filename = res.filename + '_' + str(suffix)
            res.filename = proposed_filename
        used_filenames.add(res.filename)

def run(enexpath, outpath):
    filename = os.path.basename(enexpath)
    if filename.endswith('.enex'):
        filename = filename[:-5]

    outfile = os.path.join(outpath, filename) + '.org'
    with open(outfile, 'w') as f:
        for note_elt in iter_notes(enexpath):
            note = Note(note_elt)
            if note.sourceurl:
                note.attachmentify()
            note.write(f, outpath)

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Convert .enex to .org')
    p.add_argument('input', help='enexpath to enex file')
    p.add_argument('output_dir', help='enexpath of directory to create')
    args = p.parse_args()
    if os.path.exists(args.output_dir):
        print('{} already exists.'.format(args.output_dir))
        sys.exit(1)
    os.makedirs(args.output_dir)
    run(args.input, args.output_dir)
