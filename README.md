# ember-ci

Cross-platform checks for ember, a private hobby engine (Rust + wgpu). This repo holds only the
workflow, its scripts and reference images; the engine's code is checked out at run time with a
read-only deploy key and is never stored here.

Each run (started by hand from the Actions tab, with an ember branch or commit) does, on Linux,
Windows and macOS, each on x86-64 and ARM64:

1. the size and lint gate, the tests, and a release build;
2. a CPU-only physics run;
3. headless renders of the test scenes on a software GPU (Mesa lavapipe on Linux, WARP on
   Windows; macOS runners may lack Metal), compared with `reference/` (rendered on an Apple M4 Pro).

Different GPUs round and rasterise slightly differently, so the comparison allows a few
differing pixels (`scripts/compare.py`). Screenshots, difference maps and logs are uploaded as
run artifacts.
