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
import json, pathlib
p = pathlib.Path("blender_out/render_all_state.json")
if not p.exists():
    print("0 0 0"); raise SystemExit
d = json.loads(p.read_text())
n = lambda k: len(d.get(k) or []) if isinstance(d.get(k), list) else int(d.get(k) or 0)
print(n("done"), n("failed"), n("declined"))
PY
}

free_mb() { df -m "$REPO" | tail -1 | awk '{print $4}'; }

read -r DONE FAILED DECLINED <<<"$(state_counts)"
PID="$(runner_pid)"
echo "pass: ${DONE} of 172 rendered, ${FAILED} failed, ${DECLINED} declined; $(free_mb) MB free"
echo "runner: ${PID:-none}"

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
    DECODE="$(python3 tools/png_decodes.py 2>&1 | tail -1)"
    echo "decode: ${DECODE}"
    case "$DECODE" in
        *", 0 do not,"*) ;;
        *) echo "decode: a changed PNG does not decode -- not committing, look at it by hand"; exit 1 ;;
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
verification: ${COUNT} sheet(s) from the v16 pass

$(printf '%s' "$SLUGS" | tr ' ' '\n' | sed '/^$/d' | sed 's/^/  /')

Rendered under the measured exposure (J83), the sightline verdict as a fraction
of 13 rays (J78), the walk scored on the subject's own sightline (J79) and the
43-ray subject height (J74). Committed by tools/pass_tick.sh so a container
restart costs at most the sheet being rendered.

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
if [ "$DONE" -ge 172 ]; then
    echo "runner: not started -- all 172 sheets are rendered"
    exit 0
fi
if [ -n "$PID" ]; then
    echo "runner: left alone (pid ${PID})"
    exit 0
fi
if [ "$(free_mb)" -lt 800 ]; then
    echo "runner: not started -- $(free_mb) MB free, the runner needs room above its 700 MB floor"
    exit 1
fi

setsid nohup python3 tools/render_all_sheets.py --workers 2 >> /tmp/render_all_v16.log 2>&1 < /dev/null &
sleep 6
NEW="$(runner_pid)"
if [ -n "$NEW" ]; then
    echo "runner: started (pid ${NEW})"
else
    echo "runner: failed to start -- tail /tmp/render_all_v16.log"
    exit 1
fi
