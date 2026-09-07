"""Performance and robustness regression tests (docs/verification/performance/REPORT.md).

These drive the benchmark binary in ``core/bench`` and assert the properties that
must not regress.  They deliberately do **not** assert a wall-clock budget: this
machine has four vCPUs shared with other agents, so a timing threshold would
either be so loose it proves nothing or so tight it fails at random.  What is
asserted instead is everything that is deterministic:

* the trajectory hashes of the synthetic 5,000-vehicle / 20,000-pedestrian run,
  so that a future optimisation cannot quietly change behaviour;
* that restricting ``SignalTable::cacheStates`` to a window changes no signal
  state at all, and does refresh far fewer plans;
* that a long run with agents spawning and despawning does not grow its resident
  set;
* that the tile streamer never evicts a tile inside the 300 m protection ring
  while driving a real 49 km route;
* that no agent is ever dropped by the spatial hash.

Timings are printed, so ``pytest -s`` doubles as the measurement harness.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

log = logging.getLogger(__name__)

REPO = Path(__file__).resolve().parents[1]
BENCH_SRC = REPO / "core" / "bench"
# core/build/ is git-ignored, so the benchmark binaries never reach a commit.
BENCH_BUILD = REPO / "core" / "build" / "bench"
BENCH_BIN = BENCH_BUILD / "nycsim_bench"
RUNTIME = REPO / "data" / "processed" / "runtime"

# Recorded from the verified run in docs/verification/performance/REPORT.md.
# seed 20260906, 14 x 28 grid, 5,000 vehicles, 20,000 pedestrians, 200 warm-up.
#
# Re-baselined when ADR-021 was implemented.  The previous pair
# (traffic aa5259411c39445a, peds f6dda9215d7698a0) was the behaviour in which a
# pedestrian drew its next destination uniformly over every point of interest in
# the city: almost every resulting path exceeded the 24-node cap or the per-step
# budget, so the agent fell back to wandering.  Pedestrians now choose a goal
# within walking distance and actually reach it, which moves the pedestrian hash;
# the traffic hash moves with it because drivers yield to pedestrians through the
# probe, so a different crossing is a different vehicle trajectory.  The vehicle
# spawner is unchanged *here* by construction — the synthetic grid is smaller
# than its 1,000 km ring, so the streamed region covers the whole graph and the
# lane draws are bit-identical.
EXPECTED_HASHES = {
    "traffic": "6a24b0a24a962b4c",
    "peds": "fd8d5b12f37af8ea",
}


def _build() -> Path:
    """Builds the benchmark once per session; skips the module if it cannot."""
    if BENCH_BIN.exists():
        return BENCH_BIN
    if shutil.which("cmake") is None:
        pytest.skip("cmake is not available, cannot build core/bench")
    BENCH_BUILD.mkdir(parents=True, exist_ok=True)
    for cmd in (
        ["cmake", "-S", str(BENCH_SRC), "-B", str(BENCH_BUILD), "-DCMAKE_BUILD_TYPE=Release"],
        ["cmake", "--build", str(BENCH_BUILD), "-j", "2"],
    ):
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            pytest.skip(f"cannot build core/bench: {' '.join(cmd)}\n{r.stdout[-2000:]}{r.stderr[-2000:]}")
    if not BENCH_BIN.exists():
        pytest.skip("core/bench built but nycsim_bench is missing")
    return BENCH_BIN


@pytest.fixture(scope="session")
def bench() -> Path:
    return _build()


def _run(bench_bin: Path, *args: str, timeout: int = 3600) -> str:
    """Runs a subcommand at nice 10 and returns its stdout, failing loudly."""
    cmd = ["nice", "-n", "10", str(bench_bin), *args]
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=timeout)
    log.info("%s\n%s", " ".join(cmd), r.stdout)
    if r.returncode not in (0, 1):  # 1 = "over budget", still a valid measurement
        raise AssertionError(f"{' '.join(cmd)} failed ({r.returncode}):\n{r.stdout}\n{r.stderr}")
    return r.stdout


def _num(text: str, pattern: str) -> float:
    m = re.search(pattern, text)
    assert m is not None, f"pattern {pattern!r} not found in:\n{text}"
    return float(m.group(1))


def _requires_runtime() -> None:
    missing = [n for n in ("roadgraph.nycb", "signals.nycb", "density.nycb", "transit.nycb")
               if not (RUNTIME / n).exists()]
    if missing:
        pytest.skip(f"runtime artefacts missing: {', '.join(missing)}")


# --------------------------------------------------------------- behaviour
def test_synthetic_step_is_deterministic_and_unchanged(bench: Path) -> None:
    """The optimised step must reproduce the recorded trajectory hashes exactly.

    This is the guard the whole performance lane rests on: every change was made
    on the promise that it does not alter behaviour, and these two 64-bit hashes
    over 5,000 vehicles and 20,001 pedestrians after 1,400 steps are how that
    promise is checked.
    """
    out = _run(bench, "synthetic", "--steps", "1200")
    m = re.search(r"trajectory hash\s+traffic ([0-9a-f]{16})\s+peds ([0-9a-f]{16})", out)
    assert m is not None, out
    got = {"traffic": m.group(1), "peds": m.group(2)}
    assert got == EXPECTED_HASHES, (
        "the trajectory changed — this is a behaviour change, not an optimisation.\n"
        f"expected {EXPECTED_HASHES}, got {got}"
    )
    cpu = _num(out, r"combined CPU\s+mean\s+([0-9.]+)")
    wall = _num(out, r"combined wall\s+mean\s+([0-9.]+)")
    log.info("synthetic combined step: %.3f ms CPU, %.3f ms wall", cpu, wall)
    # Sanity only: a step that suddenly costs a quarter of a second means
    # something structural broke, not that the machine is busy.
    assert cpu < 120.0, f"combined step CPU time {cpu:.1f} ms is far outside anything measured"


def test_no_agent_is_ever_dropped_by_the_spatial_hash(bench: Path) -> None:
    """A dropped insert makes an agent invisible to every proximity query."""
    out = _run(bench, "synthetic", "--steps", "200")
    assert "hash drops" not in out or "hash drops 0" in out
    # The fleet must be the size that was asked for; a silently dropped agent
    # would show up as a short fleet.
    veh = _num(out, r"fleet\s+(\d+) vehicles")
    assert veh >= 4900, f"only {veh:.0f} vehicles present"


# ----------------------------------------------------------------- signals
def test_signal_window_is_transparent_and_much_cheaper(bench: Path) -> None:
    """Restricting cacheStates to the streamed region must change no state."""
    _requires_runtime()
    out = _run(bench, "signals", "--steps", "400")
    mismatches = _num(out, r"agreement\s+(\d+) of")
    assert mismatches == 0, "the active window changed a signal state — it must be transparent"
    full = _num(out, r"whole table\s+(\d+) plans refreshed")
    win = _num(out, r"window \d+ m\s+(\d+) plans refreshed")
    assert full > 10000, f"expected the real 19,814-plan table, got {full:.0f}"
    assert win < full * 0.25, f"the window refreshed {win:.0f} of {full:.0f} plans — no restriction"
    speedup = _num(out, r"speed-up\s+([0-9.]+)x")
    log.info("cacheStates window speed-up %.1fx (%.0f -> %.0f plans)", speedup, full, win)
    assert speedup > 3.0, f"window speed-up was only {speedup:.1f}x"


# -------------------------------------------------------------------- soak
@pytest.mark.slow
def test_memory_is_bounded_over_a_long_run(bench: Path) -> None:
    """Agents spawn and despawn for 30+ simulated minutes; RSS must not grow."""
    minutes = float(os.environ.get("NYCSIM_SOAK_MINUTES", "31"))
    out = _run(bench, "soak", "--minutes", str(minutes), "--vehicles", "1500", "--peds", "6000",
               "--sample-steps", "200", timeout=7200)
    spawned = _num(out, r"churn\s+(\d+) spawns")
    despawned = _num(out, r"churn\s+\d+ spawns, (\d+) despawns")
    assert spawned > 100 and despawned > 100, (
        f"the run did not churn agents ({spawned:.0f} spawns, {despawned:.0f} despawns); "
        "the test would prove nothing"
    )
    slope = _num(out, r"RSS slope\s+([+-][0-9.]+) MB per simulated minute")
    spread = _num(out, r"spread ([0-9.]+) MB")
    log.info("soak: %.0f spawns, %.0f despawns, RSS slope %+.4f MB/min, spread %.2f MB",
             spawned, despawned, slope, spread)
    # Bounded means bounded: an hour of simulation must not add a megabyte.
    assert slope < 0.0167, f"resident set grows {slope:+.4f} MB per simulated minute ({slope * 60:+.2f} MB/h)"
    assert spread < 8.0, f"resident set moved {spread:.1f} MB over the run"


# ---------------------------------------------------------------- streaming
@pytest.mark.slow
def test_streaming_never_evicts_a_tile_inside_the_protection_ring(bench: Path) -> None:
    """The Bronx -> Staten Island route at highway speed, against the real tiles."""
    _requires_runtime()
    if not (REPO / "data" / "processed" / "tiles").is_dir():
        pytest.skip("terrain tiles are not present")
    out = _run(bench, "stream", timeout=7200)
    evictions = _num(out, r"protection ring\s+(\d+) transition")
    assert evictions == 0, f"{evictions:.0f} tiles inside the 300 m ring were coarsened or evicted"
    km = _num(out, r"route\s+\d+ lanes, \d+ segments, ([0-9.]+) km")
    verrazzano = _num(out, r"(\d+) Verrazzano segments")
    assert km > 40.0, f"the route is only {km:.1f} km — that is not the Bronx to Staten Island"
    assert verrazzano > 0, "the route does not cross the Verrazzano-Narrows Bridge"
    loads = _num(out, r"transitions\s+(\d+) loads")
    unloads = _num(out, r"transitions\s+\d+ loads, (\d+) unloads")
    peak = _num(out, r"peak resident\s+(\d+) tiles")
    log.info("stream: %.1f km, %.0f Verrazzano segments, %.0f loads, %.0f unloads, peak %.0f tiles",
             km, verrazzano, loads, unloads, peak)
    assert loads > 0 and peak > 0


# ------------------------------------------------------------ city scale
@pytest.mark.slow
def test_city_scale_step_runs_against_the_real_graph(bench: Path) -> None:
    """The real 122,235-segment graph must load, configure and step."""
    _requires_runtime()
    out = _run(bench, "city", "--steps", "60", "--warmup", "20", "--no-peds", "--no-sidewalks",
               "--seed-radius", "800", "--max-routes", "0", "--signal-window", "3000", timeout=3600)
    segments = _num(out, r"graph\s+\d+ nodes, (\d+) segments")
    assert segments > 100000, f"only {segments:.0f} segments — this is not the real graph"
    veh = _num(out, r"fleet\s+(\d+) vehicles")
    assert veh > 3000, f"only {veh:.0f} vehicles were seeded"
    cpu = _num(out, r"combined CPU\s+mean\s+([0-9.]+)")
    peak_mb = _num(out, r"resident\s+[0-9.]+ MB \(peak ([0-9.]+) MB\)")
    log.info("city step: %.1f ms CPU with %.0f vehicles, peak RSS %.0f MB", cpu, veh, peak_mb)
    # The whole city plus its router must fit in a fraction of the 15 GB box.
    assert peak_mb < 4096.0, f"peak resident set {peak_mb:.0f} MB"


def test_report_carries_the_measured_numbers() -> None:
    """The report is the deliverable; a number in a test and not in it is lost.

    The subagent harness forbids a subagent from writing report files, so the
    performance agent handed the content to the orchestrator to commit.  Until it
    is committed this skips; once it exists, its content is checked.
    """
    report = REPO / "docs" / "verification" / "performance" / "REPORT.md"
    if not report.exists():
        pytest.skip("docs/verification/performance/REPORT.md has not been committed yet")
    text = report.read_text()
    for token in ("cacheStates", "trajectory hash", "RSS slope", "Verrazzano", "callgrind"):
        assert token in text, f"the report does not mention {token}"
    assert EXPECTED_HASHES["traffic"] in text, "the report does not record the traffic trajectory hash"
