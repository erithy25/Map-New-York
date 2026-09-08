# Update 01 for the first-drive package

The package in `dist/first-drive` is a snapshot, and the world moved after it: the stations stage put 1,053
elevated station placements and 277 at grade into the per-tile structure files, and the manifest was
regenerated over them. These 1 part(s) carry only the 165 files that changed.

Lay them over an existing unpack, from the repository root, **after** unpacking the base package:

    git fetch origin dist/first-drive
    git checkout dist/first-drive -- dist/first-drive/update-01
    cat dist/first-drive/update-01/part_*.tar.gz | tar -xzvf - -i -C .

Files are replaced in place, so the order is base first, then this. `index.json` lists every file.
