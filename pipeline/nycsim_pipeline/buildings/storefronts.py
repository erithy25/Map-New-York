"""Storefront names/kinds from DCWP issued licences (w7w3-xahh) and DOHMH restaurant inspections (43nn-pn8j),
and the ``has_storefront`` rule.

Business -> building matching, in order: BIN (when the BIN exists in the footprints), nearest footprint within 25 m
of the record's coordinates, then BBL (primary building on the lot). DCWP categories are split into *street-level*
(always attached: tobacco/e-cigarette dealers, stoop-line stands, electronics stores, garages, car washes,
pawnbrokers, laundries, hotels, amusement, cabarets) and *conditional* (attached only when the building is a
store/mixed-use class or a low-rise <= 6 floors: secondhand dealers, appliance service, products for the disabled)
because the latter are frequently upper-floor offices. Contractor, agency, tow-truck, games-of-chance, delivery,
warehouse and vendor licences are not storefronts and are excluded. DOHMH establishments are kept when their latest
inspection is within the last 3 years or they are new (never inspected, date 1900-01-01).

Kind assignment: DCWP category / DOHMH cuisine first, then refined by a business-name keyword table.
"""
from __future__ import annotations

import datetime as dt
import logging
import re
from pathlib import Path

import numpy as np
import polars as pl
import shapely

from ..crs import lonlat_to_tm
from .schema import StorefrontKind as K

log = logging.getLogger("nycsim.buildings.storefronts")

MATCH_RADIUS_M = 25.0
MAX_NAMES_PER_BUILDING = 32
DOHMH_ACTIVE_YEARS = 3
SOURCE_DCWP, SOURCE_DOHMH = 1, 2

# DCWP category -> (kind, tier) ; tier 0 = street level, 1 = conditional
DCWP_CATEGORIES: dict[str, tuple[int, int]] = {
    "Tobacco Retail Dealer": (K.BODEGA, 0),
    "Electronic Cigarette Dealer": (K.BODEGA, 0),
    "Stoop Line Stand": (K.GROCERY, 0),
    "Electronics Store": (K.ELECTRONICS, 0),
    "Electronic & Home Appliance Service Dealer": (K.ELECTRONICS, 1),
    "Garage & Parking Lot": (K.GARAGE_DOOR, 0),
    "Garage": (K.GARAGE_DOOR, 0),
    "Parking Lot": (K.GARAGE_DOOR, 0),
    "Car Wash": (K.GARAGE_DOOR, 0),
    "Secondhand Dealer - General": (K.GENERIC_RETAIL, 1),
    "Secondhand Dealer - Auto": (K.GENERIC_RETAIL, 1),
    "Secondhand Dealer - Firearms": (K.GENERIC_RETAIL, 1),
    "Pawnbroker": (K.GENERIC_RETAIL, 0),
    "Dealer In Products For The Disabled": (K.PHARMACY, 1),
    "Laundry": (K.LAUNDROMAT, 0),
    "Laundries": (K.LAUNDROMAT, 0),
    "Laundry Jobber": (K.DRY_CLEANER, 1),
    "Hotel": (K.OFFICE_LOBBY, 0),
    "Amusement Arcade": (K.GENERIC_RETAIL, 0),
    "Amusement Device Permanent": (K.GENERIC_RETAIL, 0),
    "Gaming Cafe": (K.GENERIC_RETAIL, 0),
    "Pool or Billiard Hall": (K.BAR, 0),
    "Cabaret": (K.BAR, 0),
    "Catering Establishment": (K.RESTAURANT, 0),
    "Sidewalk Cafe": (K.RESTAURANT, 0),
    "Locksmith": (K.HARDWARE, 0),
    "Newsstand": (K.GENERIC_RETAIL, 0),
}

DOHMH_CUISINES: dict[str, int] = {
    "Coffee/Tea": K.COFFEE, "Bakery Products/Desserts": K.COFFEE, "Bakery": K.COFFEE, "Donuts": K.COFFEE,
    "Frozen Desserts": K.COFFEE, "Juice, Smoothies, Fruit Salads": K.COFFEE, "Bagels/Pretzels": K.DELI,
    "Pizza": K.PIZZA, "Pizza/Italian": K.PIZZA,
    "Sandwiches": K.DELI, "Sandwiches/Salads/Mixed Buffet": K.DELI, "Delicatessen": K.DELI,
    "Soups & Sandwiches": K.DELI, "Soups/Salads/Sandwiches": K.DELI, "Soups": K.DELI, "Salads": K.DELI,
    "Bottled Beverages": K.BODEGA, "Nuts/Confectionary": K.BODEGA, "Candy": K.BODEGA,
}

# name keyword refinement: (regex, kind). First match wins; applied after category/cuisine.
NAME_RULES: list[tuple[re.Pattern, int]] = [(re.compile(p, re.I), k) for p, k in [
    (r"\b(PHARMACY|DRUGS?|DRUG STORE|CHEMIST|RX|DUANE READE|WALGREENS|CVS|RITE AID)\b", K.PHARMACY),
    (r"\b(LAUNDROMAT|LAUNDRY|WASH & FOLD|LAUNDERETTE)\b", K.LAUNDROMAT),
    (r"\b(DRY CLEAN\w*|CLEANERS|TAILOR\w*)\b", K.DRY_CLEANER),
    (r"\b(NAILS?|SALON|BARBER\w*|HAIR|BEAUTY|SPA|BROWS?|LASHES|WAXING)\b", K.NAIL_HAIR),
    (r"\b(BANK|CHASE|CITIBANK|CAPITAL ONE|TD BANK|WELLS FARGO|CREDIT UNION|SAVINGS|BANCORP|HSBC|SANTANDER)\b", K.BANK),
    (r"\b(HARDWARE|LOCKSMITH|PAINTS?|LUMBER|PLUMBING SUPPLY|TOOLS?)\b", K.HARDWARE),
    (r"\b(PIZZA|PIZZERIA|SLICE)\b", K.PIZZA),
    (r"\b(COFFEE|CAFE|CAFÉ|ESPRESSO|STARBUCKS|DUNKIN\w*|BAKERY|PATISSERIE|BAGELS?|DONUTS?|TEA HOUSE|BUBBLE TEA|BOBA)\b", K.COFFEE),
    (r"\b(BAR|PUB|TAVERN|LOUNGE|SALOON|BREWERY|TAPROOM|BEER GARDEN|WINE BAR|ALE HOUSE|BIERGARTEN)\b", K.BAR),
    (r"\b(DELI|DELICATESSEN|GOURMET DELI|BODEGA|MINI ?MART|CONVENIENCE|CANDY STORE|SMOKE SHOP|7-ELEVEN|NEWS ?STAND)\b", K.BODEGA),
    (r"\b(SUPERMARKET|GROCERY|GROCERIES|FOOD MARKET|FRUIT|PRODUCE|FARM|MEAT MARKET|BUTCHER|FISH MARKET|KEY FOOD|C-TOWN|ASSOCIATED|FOODTOWN|TRADER JOE|WHOLE FOODS|MORTON WILLIAMS|GRISTEDES|WESTSIDE MARKET|FAIRWAY|ALDI|LIDL)\b", K.GROCERY),
    (r"\b(RESTAURANT|DINER|GRILL|KITCHEN|BISTRO|TRATTORIA|STEAKHOUSE|SUSHI|RAMEN|TACOS?|TAQUERIA|NOODLES?|DUMPLINGS?|BBQ|BURGERS?|CHICKEN|WINGS|FALAFEL|HALAL|THAI|INDIAN|CHINESE|MEXICAN|CUISINE|EATERY|CANTINA|OSTERIA|BRASSERIE)\b", K.RESTAURANT),
    (r"\b(CLOTHING|APPAREL|FASHION|BOUTIQUE|SHOES?|SNEAKERS?|FOOTWEAR|DRESS\w*|MENSWEAR|JEANS|OUTFITTERS|GAP|ZARA|H&M|UNIQLO|OLD NAVY|FOOT LOCKER)\b", K.CLOTHING),
    (r"\b(WIRELESS|CELLULAR|MOBILE|PHONES?|ELECTRONICS|COMPUTERS?|T-MOBILE|VERIZON|AT&T|METRO ?PCS|BEST BUY|APPLE STORE|GAME ?STOP)\b", K.ELECTRONICS),
    (r"\b(PARKING|GARAGE|AUTO REPAIR|AUTO BODY|TIRE|CAR WASH|COLLISION|MUFFLER|AUTOMOTIVE)\b", K.GARAGE_DOOR),
    (r"\b(HOTEL|INN|SUITES|MARRIOTT|HILTON|HYATT|SHERATON|HOLIDAY INN)\b", K.OFFICE_LOBBY),
]]

STOREFRONT_CLASSES_RE = re.compile(r"^(K\d|S\d|C7|D6|D7|RK|L8|RC)$")
LAND_USE_MIXED_RES_COMMERCIAL = 4
_WS = re.compile(r"\s+")


def _norm_name(s: str) -> str:
    return _WS.sub(" ", s.strip())


def load_dcwp(path: Path) -> tuple[pl.DataFrame, dict]:
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError(f"DCWP csv missing or empty: {path}")
    df = pl.read_csv(path, infer_schema_length=0)
    n_raw = df.height
    df = df.filter((pl.col("License Status") == "Active") & (pl.col("License Type") == "Premises"))
    n_active = df.height
    cats = pl.DataFrame({"Business Category": list(DCWP_CATEGORIES), "_kind": [int(v[0]) for v in DCWP_CATEGORIES.values()],
                         "_tier": [int(v[1]) for v in DCWP_CATEGORIES.values()]})
    df = df.join(cats, on="Business Category", how="inner", maintain_order="left")
    name = pl.when(pl.col("DBA/Trade Name").fill_null("").str.strip_chars() != "").then(pl.col("DBA/Trade Name")).otherwise(pl.col("Business Name"))
    out = df.select([
        name.fill_null("").str.strip_chars().alias("name"),
        pl.col("_kind").cast(pl.Int8).alias("kind"),
        pl.col("_tier").cast(pl.Int8).alias("tier"),
        pl.col("BIN").cast(pl.Int64, strict=False).alias("bin"),
        pl.col("BBL").cast(pl.Int64, strict=False).alias("bbl"),
        pl.col("Longitude").cast(pl.Float64, strict=False).alias("lon"),
        pl.col("Latitude").cast(pl.Float64, strict=False).alias("lat"),
        pl.lit(SOURCE_DCWP).cast(pl.Int8).alias("source"),
        pl.col("Business Category").alias("category"),
    ]).filter(pl.col("name") != "")
    stats = {"rows": n_raw, "active_premises": n_active, "storefront_categories": out.height,
             "street_level_tier": int((out["tier"] == 0).sum()), "conditional_tier": int((out["tier"] == 1).sum())}
    log.info("dcwp: %d active premises licences, %d in storefront categories", n_active, out.height)
    return out, stats


def load_dohmh(path: Path, today: dt.date) -> tuple[pl.DataFrame, dict]:
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError(f"DOHMH csv missing or empty: {path}")
    df = (pl.scan_csv(path, infer_schema_length=0)
          .select(["CAMIS", "DBA", "CUISINE DESCRIPTION", "INSPECTION DATE", "Latitude", "Longitude", "BIN", "BBL"]).collect())
    n_raw = df.height
    df = df.with_columns(pl.col("INSPECTION DATE").str.to_date("%m/%d/%Y", strict=False).alias("_d"))
    latest = df.sort("_d", descending=True, nulls_last=True).unique(subset=["CAMIS"], keep="first")
    cutoff = today.replace(year=today.year - DOHMH_ACTIVE_YEARS)
    latest = latest.filter((pl.col("_d") >= cutoff) | (pl.col("_d") <= dt.date(1901, 1, 1)) | pl.col("_d").is_null())
    cuis = pl.DataFrame({"CUISINE DESCRIPTION": list(DOHMH_CUISINES), "_kind": [int(v) for v in DOHMH_CUISINES.values()]})
    latest = latest.join(cuis, on="CUISINE DESCRIPTION", how="left", maintain_order="left")
    out = latest.select([
        pl.col("DBA").fill_null("").str.strip_chars().alias("name"),
        pl.col("_kind").fill_null(int(K.RESTAURANT)).cast(pl.Int8).alias("kind"),
        pl.lit(0).cast(pl.Int8).alias("tier"),
        pl.col("BIN").cast(pl.Int64, strict=False).alias("bin"),
        pl.col("BBL").cast(pl.Int64, strict=False).alias("bbl"),
        pl.col("Longitude").cast(pl.Float64, strict=False).alias("lon"),
        pl.col("Latitude").cast(pl.Float64, strict=False).alias("lat"),
        pl.lit(SOURCE_DOHMH).cast(pl.Int8).alias("source"),
        pl.col("CUISINE DESCRIPTION").fill_null("").alias("category"),
    ]).filter(pl.col("name") != "")
    stats = {"rows": n_raw, "establishments": int(df["CAMIS"].n_unique()), "active_or_new": out.height, "cutoff": cutoff.isoformat()}
    log.info("dohmh: %d establishments, %d active since %s or new", stats["establishments"], out.height, cutoff)
    return out, stats


def refine_kinds(names: np.ndarray, kinds: np.ndarray, sources: np.ndarray) -> np.ndarray:
    """Name-keyword refinement. DOHMH records can only move within food kinds unless the name is unambiguous."""
    out = kinds.copy()
    food = {int(K.RESTAURANT), int(K.COFFEE), int(K.PIZZA), int(K.DELI), int(K.BODEGA), int(K.BAR), int(K.GROCERY)}
    for i, nm in enumerate(names):
        for rx, k in NAME_RULES:
            if rx.search(nm):
                if sources[i] == SOURCE_DOHMH and int(k) not in food:
                    break
                out[i] = int(k)
                break
    return out


def match_businesses(biz: pl.DataFrame, attrs: pl.DataFrame, tree: shapely.STRtree) -> tuple[pl.DataFrame, dict]:
    """Attach each business to a footprint row. Returns rows (row, name, kind, source, method)."""
    n_biz = biz.height
    # BIN -> row (part 0 of the footprint; placeholder BINs excluded)
    fp = attrs.select([pl.int_range(pl.len(), dtype=pl.Int64).alias("row"), "bin", "bbl", "part_index", "is_primary_on_lot",
                       "pl_bldgclass", "pl_numfloors"])
    bin_rows = fp.filter((pl.col("part_index") == 0) & (pl.col("bin") % 1_000_000 != 0)).select(["bin", "row"]).unique(subset=["bin"])
    bbl_rows = fp.filter(pl.col("is_primary_on_lot")).select(["bbl", pl.col("row").alias("row_bbl")]).unique(subset=["bbl"])

    b = biz.with_columns(pl.int_range(pl.len(), dtype=pl.Int64).alias("_i"))
    b = b.join(bin_rows, on="bin", how="left", maintain_order="left")
    row = b["row"].to_numpy().astype(np.float64)
    method = np.where(np.isfinite(row), 1, 0).astype(np.int8)

    # coordinates -> nearest footprint within 25 m
    lon = b["lon"].to_numpy().astype(np.float64)
    lat = b["lat"].to_numpy().astype(np.float64)
    need = ~np.isfinite(row) & np.isfinite(lon) & np.isfinite(lat) & (lon < -70) & (lon > -75) & (lat > 40) & (lat < 41.5)
    if need.any():
        x, y = lonlat_to_tm(lon[need], lat[need])
        pts = shapely.points(x, y)
        q, t = tree.query_nearest(pts, max_distance=MATCH_RADIUS_M, all_matches=False)
        idx_need = np.nonzero(need)[0]
        row[idx_need[q]] = t
        method[idx_need[q]] = 2

    # BBL -> primary building on lot
    b = b.join(bbl_rows, on="bbl", how="left", maintain_order="left")
    row_bbl = b["row_bbl"].to_numpy().astype(np.float64)
    use_bbl = ~np.isfinite(row) & np.isfinite(row_bbl)
    row[use_bbl] = row_bbl[use_bbl]
    method[use_bbl] = 3

    matched = np.isfinite(row)
    b = b.with_columns([pl.Series("row", np.where(matched, row, -1).astype(np.int64)), pl.Series("method", method)]).filter(pl.col("row") >= 0)

    # conditional tier: keep only for store/mixed-use classes or low-rise buildings
    b = b.join(fp.select(["row", "pl_bldgclass", "pl_numfloors"]), on="row", how="left", maintain_order="left")
    cls = b["pl_bldgclass"].fill_null("").to_numpy().astype(str)
    is_store_class = np.array([bool(STOREFRONT_CLASSES_RE.match(c)) for c in cls])
    nf = b["pl_numfloors"].to_numpy().astype(np.float64)
    low_rise = ~np.isfinite(nf) | (nf <= 6)
    not_office_hotel = ~np.char.startswith(cls, "O") & ~np.char.startswith(cls, "H")
    keep = (b["tier"].to_numpy() == 0) | is_store_class | (low_rise & not_office_hotel)
    n_cond_dropped = int((~keep).sum())
    b = b.filter(pl.Series(keep))

    names = np.array([_norm_name(s) for s in b["name"].to_list()], dtype=object)
    kinds = refine_kinds(names, b["kind"].to_numpy().astype(np.int64), b["source"].to_numpy())
    out = b.select(["row", "source", "method"]).with_columns([pl.Series("name", names.astype(str)), pl.Series("kind", kinds.astype(np.int8))])
    stats = {"businesses": n_biz, "matched": int(matched.sum()), "matched_by_bin": int((method == 1).sum()),
             "matched_by_coords_25m": int((method == 2).sum()), "matched_by_bbl": int((method == 3).sum()),
             "unmatched": int((~matched).sum()), "conditional_dropped_office_or_highrise": n_cond_dropped, "attached": out.height}
    log.info("storefront match: %s", stats)
    return out, stats


def storefront_lists(matches: pl.DataFrame, n_rows: int) -> tuple[list[list[str]], list[list[int]], list[list[int]], dict]:
    """Per-row deduplicated name / kind / source lists (DOHMH first, then DCWP; capped)."""
    names: list[list[str]] = [[] for _ in range(n_rows)]
    kinds: list[list[int]] = [[] for _ in range(n_rows)]
    sources: list[list[int]] = [[] for _ in range(n_rows)]
    seen: list[set[str]] = [set() for _ in range(n_rows)]
    m = matches.sort(["source"], descending=True)  # DOHMH (2) before DCWP (1)
    capped = 0
    for row, nm, kd, src in zip(m["row"].to_list(), m["name"].to_list(), m["kind"].to_list(), m["source"].to_list()):
        key = nm.upper()
        if key in seen[row]:
            continue
        if len(names[row]) >= MAX_NAMES_PER_BUILDING:
            capped += 1
            continue
        seen[row].add(key)
        names[row].append(nm)
        kinds[row].append(int(kd))
        sources[row].append(int(src))
    stats = {"buildings_with_names": sum(1 for x in names if x), "names_total": sum(len(x) for x in names), "names_dropped_by_cap": capped}
    return names, kinds, sources, stats


def has_storefront_rule(attrs: pl.DataFrame) -> tuple[np.ndarray, dict]:
    """Ground-floor commercial evidence from PLUTO for the primary building on the lot."""
    cls = attrs["pl_bldgclass"].fill_null("").to_numpy().astype(str)
    primary = attrs["is_primary_on_lot"].to_numpy()
    garage = attrs["feature_code"].to_numpy() == 5110
    by_class = np.array([bool(STOREFRONT_CLASSES_RE.match(c)) for c in cls]) & primary & ~garage
    by_landuse = (attrs["pl_landuse"].to_numpy() == LAND_USE_MIXED_RES_COMMERCIAL) & primary & ~garage
    by_retail = (attrs["pl_retailarea"].to_numpy() > 0) & primary & ~garage
    rule = by_class | by_landuse | by_retail
    stats = {"by_class": int(by_class.sum()), "by_landuse_mixed": int(by_landuse.sum()), "by_retailarea": int(by_retail.sum()), "rule_total": int(rule.sum())}
    return rule, stats
