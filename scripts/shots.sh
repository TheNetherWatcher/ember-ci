#!/usr/bin/env bash
# Renders ember's test scenes headless: shots.sh <ember binary> <out dir>
# Run from the ember checkout (scenes read assets/ relative to it).
set -u
bin=$1; out=$2; mkdir -p "$out"
fails=0
run() {
    local name=$1; shift
    if ! env EMBER_HEADLESS=${EMBER_HEADLESS:-1280x720} EMBER_BENCH=1 EMBER_FRAMES=${FRAMES:-20} \
        EMBER_SCREENSHOT="$out/$name.bmp" "$@" "$bin" > "$out/$name.log" 2>&1 || [ ! -s "$out/$name.bmp" ]; then
        echo "FAIL $name"; tail -20 "$out/$name.log"; fails=$((fails + 1))
    else
        echo "ok   $name ($(grep -o 'adapter: .*' "$out/$name.log" | head -1))"
    fi
}
run cubes
run city EMBER_SHAPE=city
run sphere EMBER_SHAPE=sphere EMBER_CUBES=2000
run terrain EMBER_SHAPE=terrain EMBER_BODIES=300
run pick EMBER_SHAPE=terrain EMBER_PICK=640,400
run helmet EMBER_SCENE=assets/models/DamagedHelmet.glb
run sponza EMBER_SCENE=assets/models/sponza/Sponza.gltf
exit $fails
