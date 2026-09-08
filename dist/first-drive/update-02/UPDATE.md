# Update 02 for the first-drive package

The package in `dist/first-drive` is a snapshot and the world moved again. Since update 01: the surveyed curb
ramps are cut into the pavement of every tile in the region, the open-space ground exists (park
lawn, court, ball field, pool, track and rink surfaces), the elevated rail structures and station
platforms stand on measured ground, the rooftop plant sits on the roof it was surveyed on rather
than at street level, every vehicle carries real tyre, seat, carpet and trim textures, and
`pois.nycb` carries 85,023 named places the GPS can search.

These 38 parts carry only the 349 files that changed --
2722 MB raw instead of the package's 4.09 GB.

Lay them over an existing unpack, from the repository root, **after** unpacking the base package:

    git fetch origin dist/first-drive
    git checkout dist/first-drive -- dist/first-drive/update-02
    cat dist/first-drive/update-02/part_*.tar.gz | tar -xzvf - -i -C .

Files are replaced in place, so the order is the base package, then update-01, then this.
`index.json` lists every file and every part's SHA-256; to check what arrived:

    python3 tools/package_content.py --verify dist/first-drive/update-02
