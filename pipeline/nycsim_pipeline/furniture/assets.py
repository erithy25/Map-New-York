"""Which exported asset a ``props.parquet`` row is.

``props.parquet`` stores ``kind`` as the int16 code of :mod:`nycsim_pipeline.furniture.catalog`, and
that code is not the name of any file.  Turning a row into a mesh needs three lookups and two
vocabularies that do not quite agree:

1. ``data/processed/furniture/props_catalog.json`` maps the int16 code to a kind **name**;
2. ``blender_out/props/props_asset_catalog.json`` groups the exported assets by ``dataset_kind``,
   which spells several kinds differently (``utility_pole`` is exported as ``sign_post``) and does
   not have an asset at all for a dozen more (``billboard``, ``curb_ramp``, ...);
3. a tree is not chosen by kind at all but by its species and its measured height.

``blender/verify/scene.py`` worked this out once, for the renders.  Nothing else did, and
``build_levels.py`` -- the one consumer that puts props into the game -- took ``kind`` for a mesh
name and looked for ``/Game/NYCSim/Props/14/SM_14``.  Every prop in the world failed to resolve, and
the 44,427 street trees of the first-drive region failed twice over, because ``str(0 or "")`` is the
empty string and kind 0 is the tree.

This module is that logic, in one place, with no ``bpy`` in it, so the renderer, the manifest and
the editor's Python all answer the question the same way.  The manifest resolves each row here and
writes the answer into ``props.json``; the editor never has to know that ``sign_post`` is what a
utility pole is called.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: Prop ``kind`` name -> ``dataset_kind`` of the exported asset catalogue.  The two vocabularies
#: agree for most kinds; the entries here are the ones that do not spell the same, and ``None``
#: marks a kind that has no exported prop asset -- either because another stage models it (the road
#: stage builds curb ramps into the pavement) or because it is not modelled at all.
PROP_KIND_ALIASES: dict[str, str | None] = {
    "waste_basket": "waste_basket",
    "street_lamp": "street_lamp",
    # Its own asset since J58.  Aliased to ``road_sign`` before that, which resolves over the seven
    # regulatory signs and takes the alphabetically first: every one of the 13,341 GTFS bus stops
    # was a bare 12 x 18 in parking regulation plate, 0.23 m tall, with no post under it.
    "bus_stop_sign": "bus_stop_sign",
    # A real-time passenger information sign is a screen on a pole and there is no asset for one, so
    # the 491 rows stay unplaced rather than become a parking plate, which is what ``road_sign``
    # made them.  Same rule as ``billboard`` below (docs/DEVIATIONS.md J22, J58).
    "rtpi_sign": None,
    # An 11 m wooden distribution pole carrying power and telecom, drawn as a 2.44 m galvanised
    # u-channel sign post: not the wrong variant, the wrong object, and 4.5x the wrong size. The
    # kit has no utility pole, so the 924 rows stay unplaced until it does (J58).
    "utility_pole": None,
    # An OSM advertising=billboard node is a roadside bulletin on posts. The kit has
    # billboard_rooftop and billboard_wall_mounted, and both are wrong at street level, so these 15
    # rows stay unplaced rather than become the wrong object (docs/DEVIATIONS.md J22).
    "billboard": None,
    # Modelled by the road stage, and this time that is true: ``blender/roads/build_pavement.py``
    # cuts each surveyed ramp into the kerb from its own published width and running slope
    # (pavement kind 8, docs/DEVIATIONS.md J21). It was not true when this table first said it --
    # the pavement had no ramp kind at all and the comment had never been checked against it.
    "curb_ramp": None,
    "artwork": None,
    "memorial": None,
    "drinking_fountain": None,
    "payphone": None,
    "vending_machine": None,
    "bike_shelter": "bus_shelter",
    "parks_comfort_station": None,
    "parks_recreation_center": None,
    "parks_building": None,
    "cooling_tower": None,
    "swimming_pool": None,
    "misc_structure": None,
    "subway_emergency_exit": "subway_vent_grate",
    "steam_vent": "steam_vent",
}

#: Street-tree species key used in the exported asset ids, keyed by the lower-cased Latin genus
#: or species found in ``props.parquet``.
TREE_SPECIES_KEYS: dict[str, str] = {
    "styphnolobium japonicum": "sophora",
    "sophora japonica": "sophora",
    "zelkova serrata": "zelkova",
    "gleditsia triacanthos": "honeylocust",
    "gleditsia triacanthos var. inermis": "honeylocust",
    "platanus x acerifolia": "planetree",
    "platanus acerifolia": "planetree",
    "pyrus calleryana": "callery_pear",
    "quercus palustris": "pin_oak",
    "acer platanoides": "norway_maple",
    "acer rubrum": "red_maple",
    "tilia cordata": "littleleaf_linden",
    "ginkgo biloba": "ginkgo",
}

#: Fallback when the census species has no modelled asset: the commonest NYC street tree.
TREE_FALLBACK_KEY = "honeylocust"

#: Prop kinds whose modelled asset lives in the **facade kit** rather than the props catalogue.
#:
#: The planimetric rooftop cooling towers are a surveyed dataset -- real footprints on real roofs --
#: and ``hvac_cooling_tower`` is a real modelled piece. It was placed nowhere: the procedural rooftop
#: set in ``facade/placements.py`` draws from bulkheads, AC units, exhaust fans, vent pipes and
#: satellite dishes, and never picks the cooling tower. So these rows add surveyed objects and
#: duplicate nothing.
#: Kinds that have no prop asset **on purpose**, because another stage builds them as part of
#: something else. Counting these as "no asset" made two reports say the wrong thing at once: the
#: renderer listed 81 curb ramps as unmapped on a Bronx sheet whose pavement had every one of them
#: cut into it, and the manifest's ``prop_kinds_without_an_asset`` carried them as a gap. A row that
#: is deliberately built by a different stage is not a missing asset, and the two have to be
#: countable apart or the gap number stops meaning anything.
BUILT_ELSEWHERE: dict[str, str] = {
    "curb_ramp": "cut into the pavement mesh by blender/roads/build_pavement.py (J21)",
}
BUILT_ELSEWHERE_REASON = "built_elsewhere"


def is_built_elsewhere(reason: str) -> bool:
    """Does this ``resolve`` reason mean "another stage builds it" rather than "no asset"?"""
    return str(reason).split(":", 1)[0] == BUILT_ELSEWHERE_REASON

KIND_TO_KIT_PIECE: dict[str, str] = {
    "cooling_tower": "hvac_cooling_tower",
}

#: The two height thresholds that pick a tree's size class, in metres.
#:
#: These are **not** the heights the props kit's three sizes actually stand at, and treating them
#: as if they were is what put 2,248 km of surplus canopy over the city (docs/DEVIATIONS.md J70).
#: A pin oak's three exported assets are 11.8, 18.3 and 22.6 m tall and a plane tree's are 20.7,
#: 24.0 and 27.7 m, so a census tree measured at 8 m -- between these edges -- was drawn with the
#: "medium" asset and stood 18.3 or 24.0 m over the street.  They survive only as the fallback
#: ordering for a species whose assets are not in the catalogue; :func:`tree_asset` reads the real
#: exported heights and picks the nearest.
TREE_SIZE_EDGES = (7.0, 12.0)

#: How far an instance may be scaled away from the asset it was cut from.  Uniform scale is
#: honest for a tree -- crown spread tracks height within a species -- but a scale far from 1
#: means the wrong asset was picked or the measured height is wrong, and stretching a mesh that
#: far would be inventing a tree rather than drawing the measured one.  Outside the band the
#: nearest asset is drawn at its own size, the reason says so, and the row is counted.
#:
#: The band is set from the requirement, not from taste.  With the nearest exported size chosen
#: by its own height the scale the 651,023 census and OSM trees actually ask for runs 0.156 to
#: 2.765 with a median of **0.953**: most trees barely move, and the tail is young trees of a
#: species whose smallest exported asset is already large (the kit's smallest plane tree is
#: 20.7 m).  0.30 to 2.20 covers all but **2,922 rows, 0.45 %**, which keep the asset's own size.
TREE_SCALE_MIN, TREE_SCALE_MAX = 0.30, 2.20

#: Height used when a tree row carries none -- the median of the 2015 census after allometry.
TREE_DEFAULT_HEIGHT_M = 8.0


def tree_asset_id(species: str, height_m: float, leaf_off: bool = False) -> tuple[str, bool]:
    """``(asset id, species was modelled)`` for a street tree.

    A species with no modelled asset falls back to the honeylocust rather than dropping the tree:
    a wrong species is a deviation, an absent tree is a hole in the street.
    """
    key = TREE_SPECIES_KEYS.get((species or "").strip().lower())
    exact = key is not None
    key = key or TREE_FALLBACK_KEY
    if height_m >= TREE_SIZE_EDGES[1]:
        size = "large"
    elif height_m >= TREE_SIZE_EDGES[0]:
        size = "medium"
    else:
        size = "small"
    return f"tree_{key}_{size}{'_bare' if leaf_off else ''}", exact


def clean_height(value: Any) -> float:
    """A row's ``height_m`` as a usable number, NaN and null included."""
    try:
        h = float(value)
    except (TypeError, ValueError):
        return TREE_DEFAULT_HEIGHT_M
    if math.isnan(h) or h <= 0.0:
        return TREE_DEFAULT_HEIGHT_M
    return h


#: ``dataset_kind`` -> the variant code a row falls back to when its own code names no asset.
#:
#: This is a **rule, not a measurement**.  For ``street_lamp`` it is 1, the NYC DOT standard
#: octagonal pole with a cobra head on a davit arm, because that is the fixture the city puts on
#: an ordinary street and 14,690 of the 16,971 OSM lamp nodes say nothing at all about what they
#: carry (docs/DEVIATIONS.md J56).  It used to be whatever sorted first, which for lamps was the
#: ornamental Bishop's Crook -- a fixture NYC has a few thousand of, on named historic blocks.
DEFAULT_VARIANT: dict[str, int] = {"street_lamp": 1}


#: Tag an exported asset carries to declare which ``variant`` code it *is*, e.g. ``variant:2``.
VARIANT_TAG = re.compile(r"variant:(\d+)")


def declared_variants(entries: list[dict]) -> dict[int, str]:
    """``{variant code: asset id}`` from the ``variant:N`` tags a kind's assets carry.

    Empty where a kind declares nothing, which is every kind but ``street_lamp`` today.
    """
    out: dict[int, str] = {}
    for e in entries:
        for tag in e.get("tags") or []:
            m = VARIANT_TAG.fullmatch(str(tag))
            if m:
                out[int(m.group(1))] = str(e["id"])
    return out


@dataclass(frozen=True)
class PropAssets:
    """The exported prop assets, indexed the two ways a lookup needs them."""

    by_id: dict[str, dict]
    by_kind: dict[str, list[dict]]
    kind_names: dict[int, str]
    #: ``catalog_id`` -> kit piece, for the kinds whose asset is a facade kit piece.
    kit_by_id: dict[str, dict]
    #: ``dataset_kind`` -> ``{variant code: asset id}``, read from the assets' own ``variant:N``
    #: tags.  Empty for a kind that declares none, which is every kind but ``street_lamp`` today.
    variants_by_kind: dict[str, dict[int, str]] = field(default_factory=dict)
    #: ``asset id`` -> the height in metres of the mesh that was exported under it, read from the
    #: catalogue's own bounds.  Empty when the catalogue is not on disk.
    asset_height_m: dict[str, float] = field(default_factory=dict)

    def name_of(self, kind_id: int) -> str:
        return self.kind_names.get(int(kind_id), str(int(kind_id)))

    def tree_asset(self, species: str, height_m: Any, leaf_off: bool = False) -> tuple[dict | None, str, float]:
        """``(catalogue entry, reason, uniform scale)`` for one tree of a measured height.

        The measured height is real: the census records a trunk diameter and ``allometry.height_m``
        turns it into a height by a published species curve.  Until J70 that number only chose one
        of three bins and was then thrown away, so the tree drawn was whatever size the kit had
        exported -- 651,023 trees at a median 1.26x their measured height, 185,837 of them at 1.5x
        or more.  Now the nearest exported size is chosen by its *own* height and the remainder is
        taken up by a uniform scale, so the tree in the frame is the height the census measured.
        """
        want = clean_height(height_m)
        asset_id, exact = tree_asset_id(str(species or ""), want, leaf_off)
        entry = self.by_id.get(asset_id)
        if entry is None:
            return None, "tree", 1.0
        # Prefer the exported size nearest the measured height: it keeps the scale nearest 1, so
        # the leaves and bark stay nearest the size they were modelled at.
        prefix = asset_id.rsplit("_", 2)[0] if leaf_off else asset_id.rsplit("_", 1)[0]
        suffix = "_bare" if leaf_off else ""
        best, best_h = entry, self.asset_height_m.get(asset_id)
        for size in ("small", "medium", "large"):
            cand_id = f"{prefix}_{size}{suffix}"
            cand = self.by_id.get(cand_id)
            ch = self.asset_height_m.get(cand_id)
            if cand is None or ch is None or ch <= 0.0:
                continue
            if best_h is None or best_h <= 0.0 or abs(ch - want) < abs(best_h - want):
                best, best_h = cand, ch
        why = "ok" if exact else "species_substituted"
        if not best_h or best_h <= 0.0:
            return best, why, 1.0
        scale = want / best_h
        if scale < TREE_SCALE_MIN or scale > TREE_SCALE_MAX:
            return best, f"{why}:scale_out_of_band", 1.0
        return best, why, scale

    def resolve(self, kind_id: int, *, variant: Any = 0, species: str = "",
                height_m: Any = None, leaf_off: bool = False) -> tuple[dict | None, str]:
        """``(catalogue entry, reason)``; the entry is ``None`` when the row has no asset.

        ``reason`` is ``"ok"``, ``"species_substituted"``, ``"built_elsewhere"`` or the kind name
        that could not be mapped, so a caller can count what it dropped instead of dropping it
        silently -- and can tell a gap from a division of labour.

        A caller that *draws* the row must use :meth:`resolve_scaled` instead: a tree carries a
        measured height and the asset it resolves to does not stand at that height (J70).
        """
        return self.resolve_scaled(kind_id, variant=variant, species=species,
                                   height_m=height_m, leaf_off=leaf_off)[:2]

    def resolve_scaled(self, kind_id: int, *, variant: Any = 0, species: str = "",
                       height_m: Any = None, leaf_off: bool = False) -> tuple[dict | None, str, float]:
        """:meth:`resolve` plus the uniform scale the instance is to be drawn at.

        The scale is 1.0 for every kind but ``tree``, whose rows carry a measured height that the
        exported asset does not stand at.  Everything that draws or exports a prop goes through
        this, so the renderer, the Unreal manifest and the editor cannot disagree about the size
        of the same object.
        """
        name = self.name_of(kind_id)
        if name in BUILT_ELSEWHERE:
            return None, f"{BUILT_ELSEWHERE_REASON}:{name}", 1.0
        if name == "tree":
            return self.tree_asset(str(species or ""), height_m, leaf_off)
        piece = KIND_TO_KIT_PIECE.get(name)
        if piece is not None:
            entry = self.kit_by_id.get(piece)
            return (entry, "ok", 1.0) if entry is not None else (None, name, 1.0)
        alias = PROP_KIND_ALIASES.get(name, name)
        if alias is None:
            return None, name, 1.0
        choices = self.by_kind.get(alias) or []
        if not choices:
            return None, name, 1.0
        try:
            v = int(variant)
        except (TypeError, ValueError):
            v = 0
        declared = self.variants_by_kind.get(alias) or {}
        if declared:
            asset_id = declared.get(v)
            if asset_id is not None:
                entry = self.by_id.get(asset_id)
                if entry is not None:
                    return entry, "ok", 1.0
            # The code is outside the declared set -- 0 "unknown" for a kind whose assets all name
            # a real fixture, or a code no asset claims.  Fall back to the kind's own default and
            # say so, rather than let a modulo pick whichever id happens to sort into that slot.
            fallback = DEFAULT_VARIANT.get(alias)
            entry = self.by_id.get(declared.get(fallback, "")) if fallback is not None else None
            if entry is not None:
                return entry, f"variant_default:{v}", 1.0
            return choices[0], f"variant_unmapped:{v}", 1.0
        # No kind but street_lamp declares a map today; position in the id-sorted list is all
        # there is to go on, and it is only ever right by coincidence -- so it is not a modulo any
        # more either: a code past the end is reported, not wrapped.
        if 0 <= v < len(choices):
            return choices[v], "ok", 1.0
        return choices[0], f"variant_out_of_range:{v}", 1.0


def load(processed: Path, blender_out: Path) -> PropAssets:
    """Read the two catalogues.  Missing files give an empty index rather than an exception."""
    by_id: dict[str, dict] = {}
    by_kind: dict[str, list[dict]] = {}
    asset_height_m: dict[str, float] = {}
    cat_path = Path(blender_out) / "props" / "props_asset_catalog.json"
    if cat_path.is_file():
        doc = json.loads(cat_path.read_text())
        for e in doc.get("entries", []):
            by_id[e["id"]] = e
            by_kind.setdefault(str(e.get("dataset_kind") or ""), []).append(e)
            b = e.get("bounds") or {}
            try:
                asset_height_m[str(e["id"])] = float(b["max"][2]) - float(b["min"][2])
            except (KeyError, IndexError, TypeError, ValueError):
                pass
    for entries in by_kind.values():
        entries.sort(key=lambda e: e["id"])
    variants_by_kind = {k: declared_variants(v) for k, v in by_kind.items()}
    variants_by_kind = {k: v for k, v in variants_by_kind.items() if v}
    kind_names: dict[int, str] = {}
    kinds_path = Path(processed) / "furniture" / "props_catalog.json"
    if kinds_path.is_file():
        doc = json.loads(kinds_path.read_text())
        kind_names = {int(k["id"]): str(k["name"]) for k in doc.get("kinds", [])}
    kit_by_id: dict[str, dict] = {}
    kit_path = Path(processed) / "facade" / "kit_ids.json"
    if kit_path.is_file():
        for piece in json.loads(kit_path.read_text()).get("pieces", []):
            cid = piece.get("catalog_id")
            if cid:
                kit_by_id[str(cid)] = {"id": cid, "glb": piece.get("glb"),
                                       "category": piece.get("category"), "source": "kit"}
    return PropAssets(by_id=by_id, by_kind=by_kind, kind_names=kind_names, kit_by_id=kit_by_id,
                      variants_by_kind=variants_by_kind, asset_height_m=asset_height_m)
