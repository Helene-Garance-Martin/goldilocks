import time
import sys
import random

# ============================================================
# 🫧 GOLDILOCKS — Sieve Animation
# top solid line, dotted mesh, left/right tilt, settles centre
# ============================================================

WIDTH = 50
HEIGHT = 8
FRAMES = 80
FRAME_DELAY = 0.05

SIEVE_WIDTH = 28
SIEVE_PAD = 12

PARTICLES = ["·", "⋅", ".", "˙", ",", "¸"]
PILE_CHARS = ["─", "▀", "▀"]


def particle_row(density, offset=0):
    row = "".join(
        random.choice(PARTICLES) if random.random() < density else " "
        for _ in range(WIDTH)
    )

    if offset > 0:
        row = " " * offset + row
    elif offset < 0:
        row = row[abs(offset):]

    return row[:WIDTH].ljust(WIDTH)


def sieve_lines(frame, final=False):
    """
    Draw a two-line sieve:
    - top line is continuous
    - bottom line is dotted mesh
    - whole sieve jitters left/right
    - tilt changes during the animation
    """

    movement = [0, 1, 2, 1, 0, -1, -2, -1]
    jitter = 0 if final else movement[frame % len(movement)]

    progress = frame / (FRAMES - 1)

    if final:
        tilt = 0
    elif progress < 0.25:
        tilt = -2       # tilt left
    elif progress < 0.5:
        tilt = 0        # centre
    elif progress < 0.75:
        tilt = 2        # tilt right
    else:
        tilt = -2       # final little left shake before settling

    pad = SIEVE_PAD + jitter

    top_pad = pad + max(tilt, 0)
    bottom_pad = pad + max(-tilt, 0)

    top = " " * top_pad + "╭" + "─" * SIEVE_WIDTH + "╮"
    bottom = " " * bottom_pad + "╰" + "·" * SIEVE_WIDTH + "╯"

    return top, bottom, jitter


def pile_row(progress):
    if progress < 0.35:
        char = PILE_CHARS[0]
    elif progress < 0.7:
        char = PILE_CHARS[1]
    else:
        char = PILE_CHARS[2]

    return char * WIDTH


def sieve_animate():
    total_lines = HEIGHT + 6

    for _ in range(total_lines):
        print()

    for frame in range(FRAMES):
        progress = frame / (FRAMES - 1)

        # flurry rises, then fades near the end
        if progress < 0.7:
            density = 0.08 + (progress * 0.45)
        else:
            density = 0.22 * (1 - progress)

        sys.stdout.write(f"\033[{total_lines}A")

        top, bottom, jitter = sieve_lines(frame)
        print(f"  {top}\033[K")
        print(f"  {bottom}\033[K")
        print("\033[K")

        for row_index in range(HEIGHT):
            closeness_to_bottom = row_index / HEIGHT
            row_density = density * closeness_to_bottom

            lag = row_index // 2
            offset = int(jitter * (1 - lag / HEIGHT))

            print(f"  {particle_row(row_density, offset)}\033[K")

        print(f"  {pile_row(progress)}\033[K")
        print("\033[K")
        print("\033[K")

        time.sleep(FRAME_DELAY)

    # final state — sieve centred, no particles, settled bar
    sys.stdout.write(f"\033[{total_lines}A")

    top, bottom, _ = sieve_lines(FRAMES - 1, final=True)
    print(f"  {top}\033[K")
    print(f"  {bottom}\033[K")
    print("\033[K")

    for _ in range(HEIGHT):
        print(f"  {' ' * WIDTH}\033[K")

    print(f"  {'▀' * WIDTH}\033[K")
    print()
    print("  🫧 sieved · just right")
    print()


if __name__ == "__main__":
    sieve_animate()