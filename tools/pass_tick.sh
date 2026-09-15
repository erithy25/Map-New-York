#!/usr/bin/env bash
# One tick of the comparison-sheet render pass.
#
# The pass takes eight to nine hours of wall time and the container it runs in does not live that
# long. Every restart kills the runner, and nothing used to start it again: over two days the pass
# advanced by two sheets instead of thirty. This script is what a restart needs -- commit whatever
# finished, then put the runner back -- and it is safe to run at any moment, including while the
# runner is working.
#
#   bash tools/pass_tick.sh            commit finished sheets, restart the runner if it is gone
#   bash tools/pass_tick.sh --status   report only, change nothing
#
# Two rules it will not break:
#   * Never a second runner. Two of them once rendered 17 sheets twice and threw away 154 minutes.
#   * Never delete the render lock while a runner is alive; the lock is what keeps a single Cycles
#     render in memory at a time, and three at once were killed by the kernel at 7.7 GB each.
set -u -o pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO" || exit 1

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
RUNNER_PATTERN='render_all_sheets.py --workers'
STATUS_ONLY=0
[ "${1:-}" = "--status" ] && STATUS_ONLY=1

runner_pid() { pgrep -f "$RUNNER_PATTERN" 2>/dev/null | head -1; }

state_counts() {
    python3 - <<'PY'
import json, pathlib, sys
p = pathlib.Path("blender_out/render_all_state.json")
if not p.exists():
    print("0 0 0 0"); raise SystemExit
d = json.loads(p.read_text())
n = lambda k: len(d.get(k) or []) if isinstance(d.get(k), list) else int(d.get(k) or 0)
# How many finished slugs carry a record of another generation than the renderer now writes.  This
# is normally 0 -- the runner drops them at startup -- and is printed because when it is not 0 the
# pass is counting sheets finished under a rule the finished pass will not carry (DEVIATIONS J119),
# which is invisible in the done count and cannot be put right while the runner is alive.
sys.path.insert(0, "blender/verify")
stale = 0
try:
    from render_sheets import RECORD_SHAPE
    base = pathlib.Path("docs/verification/comparison")
    for slug in (d.get("done") or []) + (d.get("declined") or []):
        try:
            rec = json.loads((base / slug / "render.json").read_text())
        except (OSError, ValueError):
            stale += 1
            continue
        if rec.get("record_shape") != RECORD_SHAPE:
            stale += 1
except Exception:
    stale = -1
print(n("done"), n("failed"), n("declined"), stale)
PY
}

free_mb() { df -m "$REPO" | tail -1 | awk '{print $4}'; }

read -r DONE FAILED DECLINED STALE <<<"$(state_counts)"
PID="$(runner_pid)"
echo "pass: ${DONE} of 172 rendered, ${FAILED} failed, ${DECLINED} declined; $(free_mb) MB free"
echo "runner: ${PID:-none}"
if [ "${STALE:-0}" != "0" ]; then
    echo "shape: ${STALE} finished sheet(s) carry a record of another renderer generation --"
    echo "shape: a runner restart requeues them; editing the state file now would be a no-op (J119)"
fi
# Disk is the pass's hard constraint, and the remedy is not obvious from a number.  Each committed
# sheet adds about 4 MB of loose git objects, so a full pass from here costs roughly 700 MB; the
# runner stops itself at FLOOR_BYTES = 300 MB.  Loose objects are the slack: `git count-objects -vH`
# reported 5,987 of them at 3.98 GiB against 3.40 GiB packed while this pass ran, and packing is the
# only large gain that throws nothing away.  Do it with no render running -- gc on a 4-core box
# already at load 3.5 takes cycles the renders need.
if [ "$(free_mb)" -lt 800 ]; then
    echo "disk: $(free_mb) MB free -- pack the loose objects before this gets to the 300 MB floor:"
    echo "disk:   stop the runner, then 'git gc --prune=now', then 'bash tools/pass_tick.sh'"
fi

if [ "$STATUS_ONLY" = 1 ]; then
    exit 0
fi

# --- 1. A lock with no runner behind it is the residue of a killed process. ------------------------
if [ -z "$PID" ] && [ -f blender_out/.render_lock ]; then
    rm -f blender_out/.render_lock
    echo "lock: removed (no runner held it)"
fi

# --- 2. Commit what finished. A restart should cost the sheet in the oven, not the ones before it. -
# Only the render's own artefacts. An assessment is prose written by hand and belongs in a commit
# that says what it found, not swept into a batch of sheets by a background tick.
ARTEFACTS=(
    'docs/verification/comparison/*/render.png'
    'docs/verification/comparison/*/sheet.png'
    'docs/verification/comparison/*/render.json'
    'docs/verification/comparison/*/frame_stats.json'
)
# git aborts the whole `add` on a pathspec that matches nothing -- and the first version of this
# script listed a directory that does not exist, so for several ticks it staged nothing, committed
# nothing, and printed that it had pushed eleven sheets.  Only existing paths are added.
[ -d docs/verification/sheets ] && ARTEFACTS+=('docs/verification/sheets')
CHANGED="$(git status --porcelain -- "${ARTEFACTS[@]}" 2>/dev/null | wc -l | tr -d ' ')"
if [ "$CHANGED" != "0" ]; then
    # The guard tells a truncated PNG from one a render is still writing, because the right answer
    # differs: a settled file that will not decode is a fault to look at, and a growing one is just
    # this tick arriving mid-write.  Deferring costs nothing -- the next tick commits it -- while
    # treating it as a fault costs a whole batch of finished sheets their commit, which is what
    # happened once on this pass.
    DECODE_OUT="$(python3 tools/png_decodes.py 2>&1)"
    DECODE_RC=$?
    echo "decode: $(printf '%s' "$DECODE_OUT" | tail -1)"
    case "$DECODE_RC" in
        0) ;;
        2) echo "commit: deferred -- a render is still writing a sheet; the next tick will take it"
           exit 0 ;;
        *) printf '%s\n' "$DECODE_OUT" | grep '^TRUNCATED' || true
           echo "decode: a changed PNG is truncated -- not committing, look at it by hand"
           exit 1 ;;
    esac
    SLUGS="$(git status --porcelain -- "${ARTEFACTS[@]}" 2>/dev/null |
             sed 's|.*comparison/||; s|/.*||' | sort -u | tr '\n' ' ')"
    COUNT="$(printf '%s' "$SLUGS" | wc -w | tr -d ' ')"
    if ! git add -A -- "${ARTEFACTS[@]}"; then
        echo "commit: git add refused the pathspec -- nothing staged, nothing committed"
        exit 1
    fi
    if git diff --cached --quiet; then
        echo "commit: ${COUNT} sheet(s) changed but nothing staged -- look at it by hand"
        exit 1
    fi
    git commit -q -F - <<MSG
verification: ${COUNT} sheet(s) from the v17 pass

$(printf '%s' "$SLUGS" | tr ' ' '\n' | sed '/^$/d' | sed 's/^/  /')

Rendered under the eight repairs the v16 pass's own records asked for: the
reference chooser's distance band and aim-error rank (J112), the instant read
from the photograph's own words (J114), a structure deck read as a street's
ceiling rather than a room (J115), a view short of the frame's own minimum as a
fourth trigger for the walk (J116), the sidestep ranked on the fan's hit count
(J111), the fan spanning the whole model across this camera's bearing (J113),
kit counted as built fabric in the clearance sample (J117a) and the clearance
note's agent clause filled from the record's own fields (J117b) -- on top of
the measured exposure (J83), the sightline verdict as a fraction of 13 rays
(J78), the walk scored on the subject's own sightline (J79) and the 43-ray
subject height (J74). Committed by tools/pass_tick.sh so a container restart
costs at most the sheet being rendered.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012rCzdfEp56Z5bDvSJLVsiQ
MSG
    COMMITTED="$(git rev-parse --short HEAD)"
    for attempt in 1 2 3 4; do
        if git push -q -u origin "$BRANCH" 2>/dev/null; then
            echo "commit: ${COUNT} sheet(s) committed as ${COMMITTED} and pushed"
            break
        fi
        [ "$attempt" = 4 ] && echo "commit: ${COUNT} sheet(s) committed as ${COMMITTED}, push failed four times"
        sleep $((2 ** attempt))
    done
else
    echo "commit: nothing new"
fi

# --- 3. Put the runner back, and only ever one. ---------------------------------------------------
# A declined subject is finished work, not outstanding work: the Grand Central concourse is an
# interior and this build models none, so the runner refuses it before a scene is built and will
# refuse it again on every tick.  Counting only `done` left the pass one short of its own target
# for ever, so every tick after the last render started a runner that had nothing to do.
if [ "$((DONE + DECLINED))" -ge 172 ]; then
    echo "runner: not started -- the pass is complete: ${DONE} rendered, ${DECLINED} declined"
    exit 0
fi
if [ -n "$PID" ]; then
    echo "runner: left alone (pid ${PID})"
    exit 0
fi
# Kept a little above the runner's own FLOOR_BYTES (300 MB, measured against the 13 MB of EXR
# scratch two workers actually hold) so the tick refuses first and the runner never starts a sheet
# it cannot finish.
if [ "$(free_mb)" -lt 350 ]; then
    echo "runner: not started -- $(free_mb) MB free, the runner needs room above its 300 MB floor"
    exit 1
fi

# **One log, and it lives with the run's other state.**  This wrote to blender_out/pass_v17.log
# while a runner started by hand wrote to blender_out/pass_v17.log, so the same job had two logs
# depending on who started it -- and a watch armed on one of them sat silent through three finished
# sheets.  /tmp is also the wrong place for it: the sheets, the state file and the failure logs are
# all under blender_out, and a log that outlives a container restart there is worth more than one
# that does not.  Appended, never truncated, so a restart keeps the history the mean-minutes
# summary below is computed from.
setsid nohup python3 tools/render_all_sheets.py --workers 2 >> blender_out/pass_v17.log 2>&1 < /dev/null &
sleep 6
NEW="$(runner_pid)"
if [ -n "$NEW" ]; then
    echo "runner: started (pid ${NEW})"
else
    echo "runner: failed to start -- tail blender_out/pass_v17.log"
    exit 1
fi
