import time
import sys
import random

# ============================================================
# 🫧 GOLDILOCKS — Sieve Animation (bottom-up settling)
# ============================================================

WIDTH = 50
HEIGHT = 8
FRAMES = 80
FRAME_DELAY = 0.05

PARTICLES = ["·", "⋅", ".", "˙", ",", "¸"]
PILE_CHARS = ["─", "━", "▓"]


def particle_row(density):
    return "".join(
        random.choice(PARTICLES) if random.random() < density else " "
        for _ in range(WIDTH)
    )


def pile_row(progress):
    """
    The bottom line thickens as particles settle.
    Starts thin, becomes dense.
    """
    if progress < 0.35:
        char = PILE_CHARS[0]
    elif progress < 0.7:
        char = PILE_CHARS[1]
    else:
        char = PILE_CHARS[2]

    return char * WIDTH


def sieve_animate():
    # Reserve terminal space
    for _ in range(HEIGHT + 4):
        print()

    for frame in range(FRAMES):
        progress = frame / (FRAMES - 1)

        # Flurry gets heavier toward the bottom/finish
        density = 0.08 + (progress * 0.45)

        # Move cursor back up
        sys.stdout.write(f"\033[{HEIGHT + 4}A")

        # Falling particles above the settling line
        for row_index in range(HEIGHT):
            closeness_to_bottom = row_index / HEIGHT
            row_density = density * closeness_to_bottom
            print(f"  {particle_row(row_density)}\033[K")

        # Settled layer at the bottom
        print(f"  {pile_row(progress)}\033[K")

        # No completion message yet
        print("\033[K")
        print("\033[K")

        time.sleep(FRAME_DELAY)

    # Final settled state
    sys.stdout.write(f"\033[{HEIGHT + 4}A")

    for _ in range(HEIGHT):
        print(f"  {'▓' * WIDTH}\033[K")

    print(f"  {'▓' * WIDTH}\033[K")
    print()
    print("  🫧 sieved ")
    print()


if __name__ == "__main__":
    sieve_animate()