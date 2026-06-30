import time
import sys
import random

# ============================================================
# 🫧 GOLDILOCKS — Sieve Animation (top-to-bottom)
# ============================================================
# A horizontal bar thickens over time (the sieve).
# Particles fall from above, flurry to trickle.
# At completion the bar is at full thickness, the flurry
# has nearly stopped, and the closing line resolves.
# ============================================================

WIDTH = 50
HEIGHT = 6                # rows of falling space below the bar
PARTICLES = ['·', '⋅', '.', '˙', ',']
FRAMES = 80               # total animation length
FRAME_DELAY = 0.05        # seconds per frame


def new_row(density):
    """Generate one row of particles at the given density."""
    return [
        random.choice(PARTICLES) if random.random() < density else ' '
        for _ in range(WIDTH)
    ]


def render_bar(progress):
    """Return the sieve bar — thickens as progress increases."""
    if progress < 0.33:
        char = '─'
    elif progress < 0.66:
        char = '━'
    else:
        char = '▓'
    # tiny horizontal jitter so it reads as "being shaken"
    jitter = random.choice([0, 0, 1, -1, 0])
    pad = max(0, 2 + jitter)
    return ' ' * pad + char * WIDTH


def sieve_animate():
    # claim vertical space for the bar + falling rows + closing line
    rows = [new_row(0.4) for _ in range(HEIGHT)]
    for _ in range(HEIGHT + 2):
        print()

    for frame in range(FRAMES):
        progress = frame / FRAMES

        # density curve: starts at ~0.45 (flurry), ends near 0.02 (trickle)
        density = max(0.02, 0.45 * (1 - progress))

        # shift everything down — last row falls off
        rows = [new_row(density)] + rows[:-1]

        # move cursor up to overwrite previous frame
        sys.stdout.write(f"\033[{HEIGHT + 4}A")

        print()

        # draw the bar
        print(f"  {render_bar(progress)}")


        # draw falling particles below it
        for row in rows:
            print(f"  {''.join(row)}")

        # blank line at the bottom for breathing room
        print()

        sys.stdout.write("\033[K")  # clear any trailing artefacts
        time.sleep(FRAME_DELAY)

    # final state — bar at full thickness, sparse trickle, resolve
    sys.stdout.write(f"\033[{HEIGHT + 2}A")
    print(f"  {' ' * 2}{'▓' * WIDTH}")
    for _ in range(HEIGHT):
        print(f"  {''.join(new_row(0.02))}")

    print()

    print(f"  🫧 sieved · just right\n")


if __name__ == "__main__":
    sieve_animate()