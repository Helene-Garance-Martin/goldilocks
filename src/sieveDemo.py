import time
import sys
import random

WIDTH = 50
HEIGHT = 8
FRAMES = 80
FRAME_DELAY = 0.05

PARTICLES = ["·", "⋅", ".", "˙", ",", "¸"]
PILE_CHARS = ["─", "━", "▓"]


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


def sieve_line(frame):
    jitter = [0, 1, 2, 1, 0, -1, -2, -1][frame % 8]
    return " " * (4 + jitter) + "-" * 28, jitter


def pile_row(progress):
    if progress < 0.35:
        char = PILE_CHARS[0]
    elif progress < 0.7:
        char = PILE_CHARS[1]
    else:
        char = PILE_CHARS[2]

    return char * WIDTH


def sieve_animate():
    total_lines = HEIGHT + 5

    for _ in range(total_lines):
        print()

    for frame in range(FRAMES):
        progress = frame / (FRAMES - 1)
        density = 0.08 + (progress * 0.45)

        sys.stdout.write(f"\033[{total_lines}A")

        line, jitter = sieve_line(frame)
        print(f"  {line}\033[K")
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

    sys.stdout.write(f"\033[{total_lines}A")

    final_line, _ = sieve_line(FRAMES)
    print(f"  {final_line}\033[K")
    print("\033[K")

    for _ in range(HEIGHT):
        print(f"  {' ' * WIDTH}\033[K")

    print(f"  {'━' * WIDTH}\033[K")
    print()
    print("  🫧 sieved · just right")
    print()


if __name__ == "__main__":
    sieve_animate()