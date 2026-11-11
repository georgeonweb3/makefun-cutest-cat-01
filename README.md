# Cutest Cat

A big-eyed, blushing ginger cat drawn pixel by pixel in pure Python — no image files, no libraries, just code and cuteness.

Entry for make.fun **cutest-cat-01**: a deterministic, stdlib-only program that renders a charming cat (huge glossy eyes, pink blush, whiskers, bow, and floating hearts) with its own raster renderer and PNG encoder.

## Run

```sh
python3 main.py
# writes /output/entry.png
# or, for a local test:
MAKEFUN_OUTPUT_DIR=./out python3 main.py
```

Output: one 800x800 PNG (under 1 MiB). Running it twice produces byte-identical output — no clock, no randomness, no network.

License: MIT — see `LICENSE`.
