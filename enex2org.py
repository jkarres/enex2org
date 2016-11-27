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
    def __init__(self, relt):
        self.base64data = relt.find('data').text or ''
        self.data = base64.b64decode(self.base64data)
        self.mime = relt.find('mime').text
        md5 = hashlib.md5()
        md5.update(self.data)
        self.hash_ = md5.hexdigest()
        filename_elt = relt.find('resource-attributes/file-name')
        if filename_elt is not None and filename_elt.text:
            self.filename = filename_elt.text
        else:
            self.filename = self.hash_

Note = namedtuple('Note', 'title content tags resources sourceurl uuid attachment_dir')

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

def convert_note_with_sourceurl(note, f, outputdir):
    os.makedirs(os.path.join(outputdir, note.attachment_dir))
    used_resource_hashes, html = enml.enml2xhtml(note.content, note.resources)
    with open(os.path.join(outputdir, note.attachment_dir, 'original.html'), 'wb') as html_f:
        html_f.write(html)
    attached_filenames = ['original.html']
    note.tags.append('ATTACH')

    for res_hash, res in note.resources.items():
        if res_hash in used_resource_hashes:
            continue
        if res.filename:
            res_filename = res.filename
        else:
            res_filename = res_hash + '.' + res.mime.split('/')[1]
        attached_filenames.append(res_filename)
        with open(os.path.join(outputdir, note.attachment_dir, res_filename), 'wb') as resf:
            resf.write(res.data)

    tag_str = ':' + ':'.join(note.tags) + ':'
    num_spaces = max(1, 75 - len(note.title) - len(tag_str))
    f.write('* ' + note.title + ' '*num_spaces + tag_str + '\n')

    f.write(':PROPERTIES:\n')
    f.write(':Attachments: ' + ' '.join(attached_filenames) + '\n')
    f.write(':ID:       ' + note.uuid + '\n:END:\n')
    f.write('See [[file:{}][{}]] in attachments. [[{}][Source URL]]\n'.format(
        os.path.join(note.attachment_dir, 'original.html'),
        'original.html',
        note.sourceurl))

def convert_regular_note(note, f, outputdir):
    if note.resources:
        note.tags.append('ATTACH')

    if note.tags:
        tag_str = ':' + ':'.join(note.tags) + ':'
        num_spaces = max(1, 75 - len(note.title) - len(tag_str))
        f.write('* ' + note.title + ' '*num_spaces + tag_str + '\n')
    else:
        f.write('* ' + note.title + '\n')

    if note.resources:
        os.makedirs(os.path.join(outputdir, note.attachment_dir))
        filenames = []
        for res_hash, res in note.resources.items():
            if res.filename:
                res_filename = res.filename
            else:
                res_filename = res_hash + '.' + res.mime.split('/')[1]
            filenames.append(res_filename)
            with open(os.path.join(outputdir, note.attachment_dir, res_filename), 'wb') as resf:
                resf.write(res.data)
        f.write(':PROPERTIES:\n')
        f.write(':Attachments: ' + ' '.join(filenames) + '\n')
        f.write(':ID:       ' + note.uuid + '\n:END:\n')
    f.write(enml.enml2str(note))
    f.write('\n')

def read_resources(note_elt):
    resources = [Resource(resource_elt) for resource_elt in note_elt.findall('resource')]
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
            note_uuid = str(uuid.uuid4())
            note = Note(
                title=note_elt.find('title').text,
                content=ET.fromstring(clean(note_elt.find('content').text)),
                tags=[elt.text for elt in note_elt.findall('tag')],
                resources=read_resources(note_elt),
                sourceurl=get_sourceurl(note_elt),
                uuid=note_uuid,
                attachment_dir=os.path.join('data', note_uuid[:2], note_uuid[2:]),
            )

            if note.sourceurl:
                convert_note_with_sourceurl(note, f, outpath)
            else:
                convert_regular_note(note, f, outpath)

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
