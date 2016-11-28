# enex2org
Tool to convert Evernote export files into orgmode.

## What does it do?
It converts your Evernote export file into an orgmode file and also extracts out
your attachments, saving them as orgmode attachments.  (Use C-c C-a to see your
attachments.)

Notes that were created with a source URL (e.g., created using the web clipper)
are presumed to have relatively complicated formatting and so are saved as html
files (with links in the org file).

Notes without a source URL are presumed to have been written manually and so
are converted into orgmode formatting.

Tables are halfway implemented:  assuming your table is not too complicated,
the output will contain something looking like

    |-
    | 1 | 2
    | 3 | 4
    |-

Opening the file in Emacs, positioning your cursor in the table, and
pressing tab should be enough to have orgmode finish the formatting.

Use `--separate sometag` to output notes tagged `sometag` into their own file.

## What does it not do (yet)?
- encryption
- links to other Evernote notes

## How do you run it?
    python3 enex2org.py mynotes1.enex mynotes2.enex ... outputdir
