# GrilleCipher
A python script to create grille-type word puzzles.  
In the python script, you can specify words to be put into your puzzle. The according letters will then be mixed into a grid of random letters. To once again find the words, a mask for each word is created.  
This is meant as a print template. You print out the grid and the corresponding masks.
After you cut out the mask you can overlay it on the grid to reveal the letters. This makes for a fun puzzle. 

![alt text](https://github.com/Tempus14/GrilleCipher/blob/main/example_solution.svg?raw=true)

## Requirements
- Python 3.8 or newer
- The `reportlab` package (PDF generation)

## Installation
- Install the dependency with: `pip install reportlab`

## Usage
- Run the script: `python GrilleCipher.py`
- Generated files are written to the `output/` directory by default.

## Configuration
- Edit the top of `GrilleCipher.py` to change settings: `GRID_SIZE`, `WORDS`, `OUTPUT_DIR`, `PAPER_SIZE`, `CELL_SIZE_MM`, `RANDOM_SEED`, `GRAYSCALE_SVG`, `ENABLE_SOLUTION_OVERLAY`.

## Outputs
- `buchstabensalat.pdf` and `buchstabensalat.svg` (letter grid)
- `schablone_*.pdf` (masks for each word)
- `schablone_mask_*.svg` or `schablone_*.svg` (Cricut-ready SVG masks)
- `solution_overlay.svg` and `solution_overlay.pdf` (optional colored solution overlay)

## Example
- Set `WORDS = ["CAT", "DOG"]`, run `python GrilleCipher.py`, and check the `output/` folder for generated PDFs and SVGs.

