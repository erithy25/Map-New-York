"""Street-tree height from species and trunk diameter (DBH).

The 2015 Street Tree Census records species and DBH (inches) but no height. Height is **estimated** with a
saturating (monomolecular / Chapman–Richards with shape exponent 1) allometric curve:

    height_m = 1.37 + H_max(species) * (1 - exp(-k(species) * DBH_cm))

* ``1.37 m`` is breast height, where DBH is measured, so the curve passes through the measurement datum.
* ``H_max`` is the asymptotic (mature, open-grown urban) height of the species; values are the typical mature
  street-tree heights published for the species in the NYC Parks "Approved Species List for Street Tree Planting"
  size classes and Dirr's *Manual of Woody Landscape Plants* (large canopy 24–30 m, medium 18–22 m, small/ornamental
  7–13 m). They are reference values, not measurements from these trees.
* ``k`` controls how quickly the asymptote is approached; it is set per species so that a 10 cm DBH tree is
  ~5–8 m tall and a 60 cm DBH tree reaches ~75–80 % of ``H_max`` — the shape reported for urban shade trees by
  McPherson, van Doorn & Peper (2016, USDA FS GTR-PSW-253 "Urban tree database and allometric equations").

A saturating form was chosen over the log-log / polynomial fits of the urban tree database because the census
contains DBH outliers up to 450 in; a power law would extrapolate to absurd heights, the saturating curve cannot
exceed ``H_max``. Every height produced here carries ``height_source = 1`` (allometry) in the props table.
Unknown DBH (0 in the census) is treated as a 5 cm sapling and flagged in ``attrs``.
"""
from __future__ import annotations

import math
from typing import Iterable

import numpy as np

# (H_max metres, k per cm). Keys: exact ``spc_latin`` first, then genus (first word), then default.
SPECIES_PARAMS: dict[str, tuple[float, float]] = {
    "Platanus x acerifolia": (30.0, 0.025),
    "Platanus occidentalis": (30.0, 0.025),
    "Gleditsia triacanthos var. inermis": (22.0, 0.030),
    "Pyrus calleryana": (13.0, 0.045),
    "Quercus palustris": (24.0, 0.028),
    "Quercus rubra": (24.0, 0.026),
    "Quercus bicolor": (20.0, 0.030),
    "Quercus alba": (24.0, 0.026),
    "Quercus phellos": (22.0, 0.028),
    "Quercus robur": (22.0, 0.028),
    "Quercus macrocarpa": (22.0, 0.028),
    "Quercus velutina": (22.0, 0.028),
    "Quercus coccinea": (22.0, 0.028),
    "Quercus imbricaria": (18.0, 0.030),
    "Acer platanoides": (20.0, 0.030),
    "Acer platanoides 'Crimson King'": (18.0, 0.032),
    "Acer rubrum": (22.0, 0.030),
    "Acer saccharinum": (26.0, 0.025),
    "Acer saccharum": (24.0, 0.028),
    "Acer pseudoplatanus": (22.0, 0.028),
    "Acer campestre": (12.0, 0.045),
    "Acer ginnala": (7.0, 0.060),
    "Acer negundo": (15.0, 0.035),
    "Acer x freemanii": (22.0, 0.030),
    "Acer palmatum": (7.0, 0.060),
    "Acer griseum": (8.0, 0.060),
    "Acer buergerianum": (10.0, 0.050),
    "Acer truncatum": (10.0, 0.050),
    "Acer tataricum": (7.0, 0.060),
    "Acer": (20.0, 0.030),
    "Tilia cordata": (20.0, 0.030),
    "Tilia americana": (24.0, 0.028),
    "Tilia tomentosa": (20.0, 0.030),
    "Tilia": (20.0, 0.030),
    "Prunus": (10.0, 0.050),
    "Prunus cerasifera": (8.0, 0.060),
    "Prunus virginiana": (8.0, 0.060),
    "Prunus serrulata": (9.0, 0.055),
    "Prunus sargentii": (10.0, 0.050),
    "Prunus x yedoensis": (9.0, 0.055),
    "Prunus subhirtella": (8.0, 0.060),
    "Prunus serotina": (18.0, 0.032),
    "Zelkova serrata": (22.0, 0.030),
    "Ginkgo biloba": (24.0, 0.025),
    "Styphnolobium japonicum": (18.0, 0.030),
    "Sophora japonica": (18.0, 0.030),
    "Fraxinus pennsylvanica": (20.0, 0.030),
    "Fraxinus americana": (22.0, 0.028),
    "Fraxinus": (20.0, 0.030),
    "Liquidambar styraciflua": (24.0, 0.028),
    "Ulmus americana": (26.0, 0.025),
    "Ulmus parvifolia": (15.0, 0.035),
    "Ulmus pumila": (18.0, 0.032),
    "Ulmus": (22.0, 0.028),
    "Syringa reticulata": (8.0, 0.060),
    "Malus": (7.0, 0.060),
    "Crataegus": (7.0, 0.060),
    "Cornus": (7.0, 0.060),
    "Amelanchier": (7.0, 0.060),
    "Carpinus betulus": (14.0, 0.040),
    "Carpinus caroliniana": (10.0, 0.050),
    "Celtis occidentalis": (20.0, 0.030),
    "Cercis canadensis": (8.0, 0.060),
    "Cercidiphyllum japonicum": (15.0, 0.035),
    "Gymnocladus dioicus": (20.0, 0.028),
    "Koelreuteria paniculata": (10.0, 0.050),
    "Liriodendron tulipifera": (28.0, 0.025),
    "Magnolia": (10.0, 0.050),
    "Metasequoia glyptostroboides": (25.0, 0.025),
    "Nyssa sylvatica": (15.0, 0.035),
    "Ostrya virginiana": (12.0, 0.040),
    "Pinus": (18.0, 0.030),
    "Picea": (18.0, 0.030),
    "Populus": (25.0, 0.025),
    "Robinia pseudoacacia": (18.0, 0.030),
    "Salix": (15.0, 0.035),
    "Taxodium distichum": (20.0, 0.028),
    "Betula": (15.0, 0.035),
    "Catalpa": (15.0, 0.035),
    "Ailanthus altissima": (18.0, 0.030),
    "Morus": (12.0, 0.040),
    "Aesculus": (18.0, 0.030),
    "Aesculus hippocastanum": (20.0, 0.028),
    "Juglans nigra": (22.0, 0.028),
    "Paulownia tomentosa": (14.0, 0.040),
    "Phellodendron amurense": (12.0, 0.040),
    "Cladrastis kentukea": (12.0, 0.040),
    "Maclura pomifera": (12.0, 0.040),
    "Eucommia ulmoides": (14.0, 0.040),
    "Halesia": (8.0, 0.060),
    "Parrotia persica": (8.0, 0.060),
    "Tsuga canadensis": (18.0, 0.030),
    "Thuja": (12.0, 0.040),
    "Juniperus": (10.0, 0.050),
    "Ilex": (8.0, 0.060),
    "Chionanthus": (6.0, 0.070),
    "Corylus colurna": (12.0, 0.040),
    "Alnus": (15.0, 0.035),
    "Larix": (18.0, 0.030),
    "Pseudotsuga menziesii": (20.0, 0.028),
    "Sassafras albidum": (14.0, 0.040),
    "Diospyros virginiana": (12.0, 0.040),
    "Fagus": (24.0, 0.026),
    "Carya": (22.0, 0.028),
    "Castanea": (18.0, 0.030),
    "Cedrus": (18.0, 0.030),
    "Abies": (18.0, 0.030),
    "Elaeagnus": (6.0, 0.070),
    "Pseudocydonia": (6.0, 0.070),
    "Maackia": (8.0, 0.060),
    "Oxydendrum": (10.0, 0.050),
    "Stewartia": (8.0, 0.060),
    "Tetradium": (12.0, 0.040),
    "Broussonetia": (10.0, 0.050),
    "Quercus": (22.0, 0.028),
}
DEFAULT_PARAMS = (18.0, 0.030)
BREAST_HEIGHT_M = 1.37
UNKNOWN_DBH_CM = 5.0
INCH_M = 0.0254


def params_for(species: str | None) -> tuple[float, float]:
    """Species -> (H_max, k). Exact latin name, then genus, then default."""
    if not species:
        return DEFAULT_PARAMS
    s = species.strip()
    if s in SPECIES_PARAMS:
        return SPECIES_PARAMS[s]
    genus = s.split(" ")[0]
    return SPECIES_PARAMS.get(genus, DEFAULT_PARAMS)


def height_m(species: str | None, dbh_cm: float) -> float:
    hmax, k = params_for(species)
    d = UNKNOWN_DBH_CM if (dbh_cm is None or not math.isfinite(dbh_cm) or dbh_cm <= 0) else dbh_cm
    return BREAST_HEIGHT_M + hmax * (1.0 - math.exp(-k * d))


def height_array(species: Iterable[str | None], dbh_cm: np.ndarray) -> np.ndarray:
    """Vectorised version of :func:`height_m`."""
    sp = list(species)
    hk = np.array([params_for(s) for s in sp], dtype=float)
    d = np.asarray(dbh_cm, dtype=float)
    d = np.where(np.isfinite(d) & (d > 0), d, UNKNOWN_DBH_CM)
    return BREAST_HEIGHT_M + hk[:, 0] * (1.0 - np.exp(-hk[:, 1] * d))


def crown_diameter_m(height: np.ndarray, species: Iterable[str | None]) -> np.ndarray:
    """Crown spread estimate: ornamental/small species are wider than tall (ratio 1.0), canopy trees ~0.6 × height.

    Used only as a rendering hint (``attrs.crown_m``); flagged as estimate like the height.
    """
    ratio = np.array([1.0 if params_for(s)[0] <= 10.0 else 0.6 for s in species], dtype=float)
    return np.asarray(height, dtype=float) * ratio


def dbh_inches_to_cm(dbh_in: np.ndarray) -> np.ndarray:
    return np.asarray(dbh_in, dtype=float) * INCH_M * 100.0
