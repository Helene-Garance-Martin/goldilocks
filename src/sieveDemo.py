# src/sieveDemo.py
# ============================================================
# 🫧 GOLDILOCKS — Sieve Animation (progress-driven)
# ============================================================
# Physics (after the soil-sieving diagram):
#   - open sieve: solid side walls, dotted mesh bottom, NO top rim
#   - irregular clumps of material sit inside, shrinking as work runs
#   - fine particles fall THROUGH the mesh, thinning over time
#   - the pile at the bottom thickens: ─ → ▀
#   - end state: a little coarse residue left in the mesh,
#     air clear, pile complete. stillness = done.
# ============================================================

import sys
import time
import random
import shutil
import threading

FRAME_DELAY = 0.05

SIEVE_WIDTH = 28
SIEVE_PAD = 12
WIDTH = 50

PARTICLES = ["·", "⋅", ".", "˙", ",", "¸"]
CLUMP_PARTICLES = ["●", "●", "•", "▪", "◦"]
PILE_CHARS = ["─", "▀", "▀"]

MOUND_HEIGHT = 3          # rows of material inside the sieve
FALL_ROWS = 8             # rows of falling space below the mesh


class SieveAnimation:
    """Runs in a background thread; fed by on_progress callbacks."""

    def __init__(self):
        self.progress = 0.0
        self.target = 0.0
        self.message = "starting"
        self.phase = "sieving"
        self._stop = threading.Event()
        self._thread = None
        self._frame = 0

        # fixed clump map — irregular islands of material, so the
        # mound reads as lumpy heaps rather than a smooth gradient
        self._clumps = self._make_clumps()

        size = shutil.get_terminal_size()
        self.term_height = size.lines
        self.term_width = size.columns

    def _make_clumps(self):
        """Random clump centres along the mesh — irregular heaps."""
        clumps = []
        x = 1
        while x < SIEVE_WIDTH - 3:
            width = random.randint(3, 8)
            height = random.randint(1, MOUND_HEIGHT)   # some heaps taller
            clumps.append((x, min(x + width, SIEVE_WIDTH - 1), height))
            x += width + random.randint(1, 4)          # gaps between heaps
        return clumps

    # ------------------------------------------------------
    # PUBLIC API — matches on_progress(phase, current, total, message)
    # ------------------------------------------------------

    def update(self, phase, current, total, message):
        base = 0.0 if phase == "sanitising" else 0.5
        self.target = base + (current / max(total, 1)) * 0.5
        self.phase = phase
        self.message = message

    def start(self):
        sys.stdout.write("\033[?1049h\033[?25l\033[H")
        sys.stdout.flush()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def finish(self, closing="🫧 sieved · just right"):
        self.target = 1.0
        time.sleep(FRAME_DELAY * 14)
        self._stop.set()
        self._thread.join()
        self._final_frame(closing)
        time.sleep(2.0)
        self._restore()

    def abort(self):
        self._stop.set()
        if self._thread:
            self._thread.join()
        self._restore()

    def _restore(self):
        sys.stdout.write("\033[?25h\033[?1049l")
        sys.stdout.flush()

    # ------------------------------------------------------
    # DRAWING PIECES
    # ------------------------------------------------------

    def _jitter(self, final=False):
        movement = [0, 1, 2, 1, 0, -1, -2, -1]
        return 0 if final else movement[self._frame % len(movement)]

    def _mound_row(self, row_from_top, jitter):
        """One row inside the sieve. row_from_top 0 = highest.
        Clumps are irregular islands; taller clumps reach higher rows.
        Material shrinks with progress, top rows emptying first."""
        p = self.progress
        row_life = min(1.0, max(0.0, (p * (MOUND_HEIGHT + 1)) - row_from_top))
        density = 0.85 * (1 - row_life)

        # which row of the mound is this, counted from the mesh up
        height_from_mesh = MOUND_HEIGHT - row_from_top

        content = [" "] * SIEVE_WIDTH
        for (start, end, clump_height) in self._clumps:
            if clump_height >= height_from_mesh:
                for x in range(start, end):
                    if random.random() < density:
                        content[x] = random.choice(CLUMP_PARTICLES)

        body = "".join(content)
        pad = SIEVE_PAD + jitter
        return " " * pad + "│" + body + "│"

    def _mesh_row(self, jitter):
        pad = SIEVE_PAD + jitter
        return " " * pad + "╰" + "·" * SIEVE_WIDTH + "╯"

    def _falling_row(self, closeness, jitter):
        p = self.progress
        density = 0.45 * (1 - p) * closeness
        row = "".join(
            random.choice(PARTICLES) if random.random() < density else " "
            for _ in range(WIDTH)
        )
        offset = int(jitter * (1 - closeness) * 0.6)
        if offset > 0:
            row = " " * offset + row
        elif offset < 0:
            row = row[abs(offset):]
        return row[:WIDTH].ljust(WIDTH)

    def _pile_row(self):
        p = self.progress
        char = PILE_CHARS[0] if p < 0.35 else PILE_CHARS[1] if p < 0.7 else PILE_CHARS[2]
        return char * WIDTH

    # ------------------------------------------------------
    # FRAME
    # ------------------------------------------------------

    def _draw(self, final=False):
        jitter = self._jitter(final)

        lines = []
        label = "" if final else f"  {self.phase} · {self.message}"
        lines.append(label[: self.term_width])
        lines.append("")

        # open sieve — no top rim, walls + mound + mesh
        for m in range(MOUND_HEIGHT):
            lines.append(f"  {self._mound_row(m, jitter)}")
        lines.append(f"  {self._mesh_row(jitter)}")
        lines.append("")

        for r in range(FALL_ROWS):
            closeness = (r + 1) / FALL_ROWS
            if final:
                lines.append("")
            else:
                lines.append(f"  {self._falling_row(closeness, jitter)}")

        lines.append(f"  {self._pile_row()}")

        sys.stdout.write("\033[H")
        for line in lines:
            sys.stdout.write(f"{line}\033[K\n")
        sys.stdout.write("\033[J")
        sys.stdout.flush()

    def _run(self):
        while not self._stop.is_set():
            self.progress += (self.target - self.progress) * 0.15
            self._draw()
            self._frame += 1
            time.sleep(FRAME_DELAY)

    def _final_frame(self, closing):
        self.progress = 1.0

        lines = []
        lines.append("")
        lines.append("")

        # nearly-empty open sieve — coarse residue left on the mesh
        for m in range(MOUND_HEIGHT):
            if m == MOUND_HEIGHT - 1:
                content = [" "] * SIEVE_WIDTH
                for (start, end, _h) in self._clumps:
                    if random.random() < 0.5:            # some clumps leave residue
                        cx = (start + end) // 2
                        content[cx] = "●"
                        if cx + 1 < SIEVE_WIDTH and random.random() < 0.5:
                            content[cx + 1] = "•"
                lines.append(f"  {' ' * SIEVE_PAD}│{''.join(content)}│")
            else:
                lines.append(f"  {' ' * SIEVE_PAD}│{' ' * SIEVE_WIDTH}│")

        lines.append(f"  {self._mesh_row(0)}")
        lines.append("")

        for r in range(FALL_ROWS):
            if r == FALL_ROWS - 1:
                dust = "".join(
                    random.choice(PARTICLES) if random.random() < 0.08 else " "
                    for _ in range(WIDTH)
                )
                lines.append(f"  {dust}")
            elif r == FALL_ROWS // 2:
                lines.append(f"  {closing}")
            else:
                lines.append("")

        lines.append(f"  {'▀' * WIDTH}")

        sys.stdout.write("\033[H")
        for line in lines:
            sys.stdout.write(f"{line}\033[K\n")
        sys.stdout.write("\033[J")
        sys.stdout.flush()


# ------------------------------------------------------------
# DEMO — run standalone: python src/sieveDemo.py
# ------------------------------------------------------------

if __name__ == "__main__":
    anim = SieveAnimation()
    anim.start()
    try:
        for i in range(6):
            anim.update("sanitising", i + 1, 6, f"pipeline_{i + 1}")
            time.sleep(0.6)
        for i in range(4):
            anim.update("anonymising", i + 1, 4, f"pass_{i + 1}")
            time.sleep(0.7)
        anim.finish()
    except KeyboardInterrupt:
        anim.abort()