# NYCSim first-drive content — update-03

**This package is complete in itself.** Unlike update-01 and update-02 it is not a delta:
unpack it alone, on a clean checkout, and do not lay the older updates over it.

It carries the 45-tile first-drive region as the world now stands — the metered development
(DEVIATIONS J83), the kerb-side props facing their own kerb (J84), the Hudson Yards platform as a
terrain deck (J85), the woodland canopy declared procedural (J86) and the Citi Bike stations
(Stage 40).


`data/processed/` and `blender_out/` are gitignored, so a clone of this repository has the code and
none of the city. These parts are the city.

    git fetch origin dist/first-drive
    git checkout dist/first-drive -- dist/first-drive/update-03
    cat dist/first-drive/update-03/part_*.tar.gz | tar -xzvf - -i -C .

Git for Windows ships `tar`, so nothing else needs installing. The `-i` matters: `cat` of several
gzip members is a valid stream, and `tar` needs telling to read past the first end-of-archive marker.

To check what arrived:

    python3 tools/package_content.py --verify dist/first-drive/update-03

Then, from the repository root:

    python3 unreal/tools/gen_core_unity.py --check     # already committed; this only re-checks
    <UnrealEditor-Cmd> NYCSim.uproject -run=NYCImport -stages=validate,stage,assets,levels
    <UnrealEditor> NYCSim.uproject                     # open /Game/NYCSim/Maps/NYC and press Play

`unreal/README.md` has the long version, including the one manual step the editor's Python cannot do.
