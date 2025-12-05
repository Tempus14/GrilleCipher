import random
import string
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A5, LETTER, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics


# ============================================================
#   CONFIGURATION (CENTRAL)
# ============================================================

GRID_SIZE = 10                         # Width/height of the letter grid
WORDS = ["Ring", "Sword", "Pony", "Mountain", "Eye", "White"]  # Words to hide

OUTPUT_DIR = "output"                  # Output directory

# Layout
PAPER_SIZE = A5
CELL_SIZE_MM = 10                      # Cell size for PDF (mm)
MARGIN_MM = 20                         # Outer margin (mm)
FONT_SIZE = 12                         # Font size

ENABLE_SOLUTION_OVERLAY = True        # If True: also create a solution overlay (SVG + PDF)

# Reproducibility: None or an integer seed
RANDOM_SEED = None                     # e.g. 1337 for reproducible puzzles

# If False: export masks as Cricut-friendly SVGs (default).
# If True: use the legacy grayscale/filled SVG variant (`save_mask_svg`).
GRAYSCALE_SVG = False


# ============================================================
#   Helper functions
# ============================================================

def generate_letter_grid(size):
    """Generate a square grid filled with random letters."""
    letters = string.ascii_uppercase + "ÄÖÜß"
    return [[random.choice(letters) for _ in range(size)] for _ in range(size)]


def place_word_scattered(word, size, grid, forbidden):
    """
    Assign as many random positions to the word as the number of letters.
    The positions are later sorted in reading order.

    `forbidden` contains coordinates that are already occupied.
    A collision is allowed only if the exact same letter would be placed
    at that position.
    """
    attempts = 0
    max_attempts = 5000

    # First we pick a set of suitable cells (without immediately assigning
    # letters). We then sort the selected positions in reading order and
    # check whether any already-occupied positions (in `forbidden`) contain
    # the same letter that would appear there after sorting. If not,
    # the selection is discarded and a new attempt is made.
    while True:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError(f"Could not find positions for word '{word}'.")

        positions = []
        chosen = set()

        # random selection without immediate assignment
        while len(positions) < len(word):
            r = random.randint(0, size - 1)
            c = random.randint(0, size - 1)

            if (r, c) in chosen:
                continue

            # Allow selecting already-occupied cells only if the existing
            # letter is contained in this word. (Completely excluding
            # occupied cells would create too many dead-ends.)
            if (r, c) in forbidden and grid[r][c] not in word:
                continue

            chosen.add((r, c))
            positions.append((r, c))

        # Now sort in reading order and assign letters to the positions
        sorted_positions = sorted(positions, key=lambda pos: (pos[0], pos[1]))

        # Check whether an already-occupied cell contains the same letter
        valid = True
        for (r, c), ch in zip(sorted_positions, word):
            if (r, c) in forbidden:
                existing = grid[r][c]
                if existing != ch:
                    valid = False
                    break

        if valid:
            return sorted_positions
        # otherwise try again


def apply_word_to_grid(grid, positions, word):
    """Apply the word to the grid at the given positions."""
    for (r, c), ch in zip(positions, word):
        grid[r][c] = ch


# ============================================================
#   PDF output
# ============================================================

def save_grid_pdf(grid, filename):
    c = canvas.Canvas(filename, pagesize=PAPER_SIZE)
    size = len(grid)
    cell = CELL_SIZE_MM * mm
    margin = MARGIN_MM * mm

    width, height = PAPER_SIZE

    for r in range(size):
        for col in range(size):
            x = margin + col * cell
            y = height - margin - (r + 1) * cell  # bottom-left corner of cell
            c.setFont("Helvetica", FONT_SIZE)
            # center the letter inside the cell
            text = grid[r][col]
            text_w = c.stringWidth(text, "Helvetica", FONT_SIZE)
            tx = x + (cell - text_w) / 2
            ty = y + (cell - FONT_SIZE) / 2
            c.drawString(tx, ty, text)

    # Draw outer frame on top
    outer_size = size * cell
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1)
    # Bottom-left corner is at height - margin - size * cell
    c.rect(margin, height - margin - size * cell, outer_size, outer_size, fill=False, stroke=True)

    c.save()


def save_mask_pdf(mask, size, filename):
    c = canvas.Canvas(filename, pagesize=PAPER_SIZE)
    cell = CELL_SIZE_MM * mm
    margin = MARGIN_MM * mm

    width, height = PAPER_SIZE

    for r in range(size):
        for col in range(size):
            x = margin + col * cell
            y = height - margin - (r + 1) * cell  # bottom-left corner of cell

            # Interpret `mask` as the set of hole positions. Draw non-mask
            # cells as filled (material) and mask cells as transparent/
            # white with a stroke so holes do not visually cover the
            # letters when overlaid.
            if (r, col) in mask:
                c.setFillGray(1)  # white (hole)
                c.setStrokeColorRGB(0, 0, 0)
                c.rect(x, y, cell, cell, fill=True, stroke=True)
            else:
                c.setFillGray(0.85)  # material
                c.setStrokeColorRGB(0, 0, 0)
                c.rect(x, y, cell, cell, fill=True, stroke=True)

    # Draw outer frame on top
    outer_size = size * cell
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(2)
    # Bottom-left corner is at height - margin - size * cell
    c.rect(margin, height - margin - size * cell, outer_size, outer_size, fill=False, stroke=True)

    c.save()


# ============================================================
#   SVG output
# ============================================================

def save_grid_svg(grid, filename):
    size = len(grid)
    cell = CELL_SIZE_MM * 3  # slightly larger scaling for SVG
    margin = MARGIN_MM * 3
    width = size * cell + 2 * margin
    height = size * cell + 2 * margin

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<style> text { font-family: monospace; font-size: 16px; } </style>',
        '<rect width="100%" height="100%" fill="white"/>'
    ]

    for r in range(size):
        for c in range(size):
            # center text in cell using text-anchor and dominant-baseline
            x = margin + c * cell + cell / 2
            y = margin + r * cell + cell / 2
            svg.append(
                f'<text x="{x}" y="{y}" text-anchor="middle" dominant-baseline="middle">{grid[r][c]}</text>'
            )

    svg.append('</svg>')

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))


def save_masks_for_cricut(masks, size, base_filename):
    """Create a Cricut-friendly SVG for each mask.

    - Dimensions in `mm` (width/height attribute) so Cricut Design Space
      interprets the real-world size correctly.
    - Grid is drawn as thin black strokes (no fills).
    - Holes are red, unfilled rectangles (strokes) — so red paths can be
      assigned to 'Cut' and black paths to 'Draw' inside Cricut Design
      Space.
    - Outer square cutout (red stroke) for the entire grid boundary.
    """
    cell_mm = CELL_SIZE_MM
    margin_mm = MARGIN_MM
    width_mm = size * cell_mm + 2 * margin_mm
    height_mm = width_mm

    for idx, mask in enumerate(masks, start=1):
        filename = f"{base_filename}_mask_{idx}.svg"
        svg = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_mm}mm" height="{height_mm}mm" viewBox="0 0 {width_mm} {height_mm}">',
            '<!-- Cricut-ready SVG: black strokes = raster (draw), red strokes = cut -->',
            f'<rect width="100%" height="100%" fill="white"/>',
        ]

        # draw outer square cutout (red stroke) for the entire grid boundary
        outer_x = margin_mm
        outer_y = margin_mm
        outer_size = size * cell_mm
        svg.append(
            f'<rect x="{outer_x}" y="{outer_y}" width="{outer_size}" height="{outer_size}" fill="none" stroke="#FF0000" stroke-width="0.8"/>'
        )

        # draw grid cells as thin stroked rectangles (draw)
        for r in range(size):
            for c in range(size):
                x = margin_mm + c * cell_mm
                y = margin_mm + r * cell_mm
                svg.append(
                    f'<rect x="{x}" y="{y}" width="{cell_mm}" height="{cell_mm}" fill="none" stroke="black" stroke-width="0.2"/>'
                )

        # draw cut rectangles for the holes (red stroke, no fill)
        for (r, c) in sorted(mask, key=lambda p: (p[0], p[1])):
            x = margin_mm + c * cell_mm
            y = margin_mm + r * cell_mm
            svg.append(
                f'<rect x="{x}" y="{y}" width="{cell_mm}" height="{cell_mm}" fill="none" stroke="#FF0000" stroke-width="0.8"/>'
            )

        svg.append('</svg>')

        outdir = os.path.dirname(filename)
        if outdir:
            os.makedirs(outdir, exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(svg))


def save_mask_svg(mask, size, filename):
    cell = CELL_SIZE_MM * 3
    margin = MARGIN_MM * 3
    width = size * cell + 2 * margin
    height = size * cell + 2 * margin

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="white"/>'
    ]

    for r in range(size):
        for c in range(size):
            x = margin + c * cell
            y = margin + r * cell
            # mask = hole -> draw white/transparent (hole); non-mask = material
            if (r, c) in mask:
                svg.append(
                    f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="white" stroke="black"/>'
                )
            else:
                svg.append(
                    f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="#cccccc" stroke="black"/>'
                )

    svg.append('</svg>')

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))


def save_solution_overlay_svg(grid, masks, word_positions, words, filename):
    size = len(grid)
    cell = CELL_SIZE_MM * 3
    margin = MARGIN_MM * 3

    # Legend layout: compute font and line height, allow extra space
    legend_count = len(words)
    legend_font = 12
    max_lines = int(margin / 10)
    if legend_count > max_lines:
        legend_font = max(8, int((margin - 6) / legend_count * 0.8))
    line_h = legend_font + 4
    legend_margin = 6

    # expand SVG height to fit legend below the grid
    extra_height = 0
    if legend_count > 0:
        extra_height = legend_margin + legend_count * line_h

    width = size * cell + 2 * margin
    height = size * cell + 2 * margin + extra_height

    color_list = ["red", "green", "blue", "orange", "purple", "cyan", "magenta"]
    opacity = 0.35

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<style> text { font-family: monospace; font-size: 14px; } </style>',
        '<rect width="100%" height="100%" fill="white"/>'
    ]

    # draw masks first so letters remain visible on top
    for i, mask in enumerate(masks):
        color = color_list[i % len(color_list)]
        for (r, c) in sorted(mask, key=lambda p: (p[0], p[1])):
            x = margin + c * cell
            y = margin + r * cell
            svg.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{color}" fill-opacity="{opacity}" stroke="black"/>')

    # letters on top of masks
    for r in range(size):
        for c in range(size):
            x = margin + c * cell + cell / 2
            y = margin + r * cell + cell / 2
            svg.append(f'<text x="{x}" y="{y}" text-anchor="middle" dominant-baseline="middle">{grid[r][c]}</text>')

    # outlines for original positions
    for i, mask in enumerate(masks):
        color = color_list[i % len(color_list)]
        for (r, c) in word_positions[i]:
            x = margin + c * cell
            y = margin + r * cell
            svg.append(f'<rect x="{x+2}" y="{y+2}" width="{cell-4}" height="{cell-4}" fill="none" stroke="{color}" stroke-width="2"/>')

    # legend below the grid: one word per line extending downward
    if legend_count > 0:
        svg.append(f'<g font-size="{legend_font}" font-family="monospace">')
        lx = margin + 5
        start_y = margin + size * cell + legend_margin + legend_font
        # determine box size from font (use at most 12px for compactness)
        box_size = min(12, legend_font)
        text_gap = 6
        for i, word in enumerate(words):
            color = color_list[i % len(color_list)]
            count = len(masks[i])
            ly = start_y + i * line_h
            # draw color box vertically centered on the text baseline
            rect_y = ly - (box_size / 2)
            svg.append(f'<rect x="{lx}" y="{rect_y}" width="{box_size}" height="{box_size}" fill="{color}" fill-opacity="0.6" stroke="black"/>')
            text_x = lx + box_size + text_gap
            # use middle baseline so text is centered vertically with the box
            svg.append(f'<text x="{text_x}" y="{ly}" dominant-baseline="middle">{word}: {count} cells</text>')
        svg.append('</g>')

    svg.append('</svg>')
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))


def save_solution_overlay_pdf(grid, masks, word_positions, words, filename):
    c = canvas.Canvas(filename, pagesize=PAPER_SIZE)
    size = len(grid)
    cell = CELL_SIZE_MM * mm
    margin = MARGIN_MM * mm
    width, height = PAPER_SIZE

    color_rgbs = [
        (1, 0, 0), (0, 0.6, 0), (0, 0, 1), (1, 0.5, 0), (0.6, 0, 0.6), (0, 0.6, 0.6), (1, 0, 1)
    ]
    opacity = 0.35

    # draw letters
    c.setFont("Helvetica", FONT_SIZE)
    for r in range(size):
        for col in range(size):
            x = margin + col * cell
            y = height - margin - r * cell
            text = grid[r][col]
            text_w = c.stringWidth(text, "Helvetica", FONT_SIZE)
            tx = x + (cell - text_w) / 2
            ty = y + (cell - FONT_SIZE) / 2
            c.drawString(tx, ty, text)

    # draw masks first so letters will be drawn on top
    for i, mask in enumerate(masks):
        rgb = color_rgbs[i % len(color_rgbs)]
        blended = tuple((v * opacity) + (1.0 - opacity) * 1.0 for v in rgb)
        c.setFillColorRGB(*blended)
        c.setStrokeColorRGB(*rgb)
        c.setLineWidth(0.5)
        for (r, cpos) in sorted(mask, key=lambda p: (p[0], p[1])):
            x = margin + cpos * cell
            y = height - margin - r * cell
            c.rect(x, y, cell, cell, fill=True, stroke=True)

    # draw letters on top of masks
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", FONT_SIZE)
    for r in range(size):
        for col in range(size):
            x = margin + col * cell
            y = height - margin - r * cell
            text = grid[r][col]
            text_w = c.stringWidth(text, "Helvetica", FONT_SIZE)
            tx = x + (cell - text_w) / 2
            ty = y + (cell - FONT_SIZE) / 2
            c.drawString(tx, ty, text)

    # outline original positions (use same color)
    for i, mask in enumerate(masks):
        rgb = color_rgbs[i % len(color_rgbs)]
        c.setLineWidth(2)
        c.setStrokeColorRGB(*rgb)
        for (r, cpos) in word_positions[i]:
            x = margin + cpos * cell
            y = height - margin - r * cell
            c.rect(x + 2, y + 2, cell - 4, cell - 4, fill=False, stroke=True)

    # legend directly below the grid: one word per line extending downward
    if words:
        # Determine legend font and line height
        legend_font = max(8, int(FONT_SIZE * 0.9))
        line_h = legend_font + 4

        # space between grid bottom and first legend line
        legend_margin = 6 * mm

        # compute grid bottom (y coordinate) in PDF coords
        grid_top = height - margin
        grid_bottom = grid_top - (size * cell)

        # available vertical space between grid_bottom and bottom margin
        available = grid_bottom - margin - legend_margin

        # if not enough vertical space, reduce font to fit all lines
        if available > 0:
            max_lines = int(available // line_h)
            if len(words) > max_lines and max_lines > 0:
                legend_font = max(6, int((available) / len(words)))
                line_h = legend_font + 4
        else:
            # no room below grid; fall back to placing inside bottom margin
            legend_font = max(6, int(FONT_SIZE * 0.7))
            line_h = legend_font + 4

        c.setFont("Helvetica", legend_font)

        # starting baseline y (first line) just below grid
        start_y = grid_bottom - legend_margin

        for i, word in enumerate(words):
            lx = margin + 5
            ly = start_y - i * line_h
            # ensure we don't draw below the bottom margin
            if ly < margin + 2:
                ly = margin + 2 + (i - max(0, i - int((start_y - margin) // line_h))) * line_h
            text = f"{word}: {len(masks[i])} cells"
            # compute ascent so box top = cap height and bottom = baseline
            ascent = pdfmetrics.getAscent("Helvetica") * legend_font / 1000.0
            box_height = ascent
            box_width = box_height
            box_x = lx
            box_y = ly
            rgb = color_rgbs[i % len(color_rgbs)]
            blended = tuple((v * opacity) + (1.0 - opacity) * 1.0 for v in rgb)
            c.setFillColorRGB(*blended)
            c.rect(box_x, box_y, box_width, box_height, fill=True, stroke=0)
            c.setStrokeColorRGB(0, 0, 0)
            c.rect(box_x, box_y, box_width, box_height, fill=False, stroke=1)
            text_x = lx + box_width + 6
            c.setFillColorRGB(0, 0, 0)
            c.drawString(text_x, ly, text)

    c.save()


# ============================================================
#   Main program
# ============================================================

if __name__ == "__main__":

    if RANDOM_SEED is not None:
        random.seed(RANDOM_SEED)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Word search (letter grid)
    grid = generate_letter_grid(GRID_SIZE)
    forbidden = set()
    masks = []
    word_positions = []

    
    # Normalize user-provided words: convert to uppercase so inserted letters match the grid
    WORDS = [w.upper() for w in WORDS]

    for word in WORDS:
        positions = place_word_scattered(word, GRID_SIZE, grid, forbidden)
        apply_word_to_grid(grid, positions, word)
        forbidden.update(positions)
        # Mask consists only of the original word positions
        mask = set(positions)
        masks.append(mask)
        word_positions.append(positions)

    # Outputs
    save_grid_pdf(grid, f"{OUTPUT_DIR}/buchstabensalat.pdf")
    for i, mask in enumerate(masks, 1):
        save_mask_pdf(mask, GRID_SIZE, f"{OUTPUT_DIR}/schablone_{i}.pdf")

    save_grid_svg(grid, f"{OUTPUT_DIR}/buchstabensalat.svg")
    # SVG masks: default = Cricut-friendly export (no fills, mm units,
    # red stroke = cut). If GRAYSCALE_SVG is True, keep legacy filled SVGs.
    if GRAYSCALE_SVG:
        for i, mask in enumerate(masks, 1):
            save_mask_svg(mask, GRID_SIZE, f"{OUTPUT_DIR}/schablone_{i}.svg")
    else:
        # produces files like "output/schablone_mask_1.svg", etc.
        save_masks_for_cricut(masks, GRID_SIZE, f"{OUTPUT_DIR}/schablone")

    if ENABLE_SOLUTION_OVERLAY:
        try:
            save_solution_overlay_svg(grid, masks, word_positions, WORDS, f"{OUTPUT_DIR}/solution_overlay.svg")
            save_solution_overlay_pdf(grid, masks, word_positions, WORDS, f"{OUTPUT_DIR}/solution_overlay.pdf")
            print(f"Solution overlay saved as: {OUTPUT_DIR}/solution_overlay.svg and {OUTPUT_DIR}/solution_overlay.pdf")
        except Exception as e:
            print("Error creating solution overlay:", e)


    print("Done! Files are in folder:", OUTPUT_DIR)
