"""Generate a random map while keeping a route between the default endpoints."""

import argparse
import os
import random
import tempfile
from pathlib import Path

Grid = list[list[int]]
PROJECT_DIR = Path(__file__).resolve().parent


def generate_grid(
    rows: int = 15,
    columns: int = 25,
    wall_probability: float = 0.25,
    seed: int | None = None,
) -> Grid:
    if rows < 3 or columns < 3:
        raise ValueError("Map dimensions must be at least 3 by 3.")
    if not 0 <= wall_probability <= 1:
        raise ValueError("Wall probability must be between 0 and 1.")

    rng = random.Random(seed)
    grid = [
        [int(rng.random() < wall_probability) for _ in range(columns)]
        for _ in range(rows)
    ]

    for row in range(rows):
        grid[row][0] = grid[row][-1] = 1
    for column in range(columns):
        grid[0][column] = grid[-1][column] = 1

    goal_row, goal_column = rows - 2, columns - 2
    for column in range(1, goal_column + 1):
        grid[1][column] = 0
    for row in range(1, goal_row + 1):
        grid[row][goal_column] = 0
    return grid


def save_grid(grid: Grid, map_path: Path) -> Path:
    map_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path = map_path.with_name("mapa_antigo.txt")
    if map_path.resolve() == archive_path.resolve():
        raise ValueError("The output map cannot be named mapa_antigo.txt.")

    content = "\n".join("".join(map(str, row)) for row in grid) + "\n"
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=map_path.parent,
            delete=False,
        ) as temporary_file:
            temporary_file.write(content)
            temporary_path = Path(temporary_file.name)

        if map_path.exists():
            os.replace(map_path, archive_path)
        os.replace(temporary_path, map_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return map_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=15)
    parser.add_argument("--columns", type=int, default=25)
    parser.add_argument("--wall-probability", type=float, default=0.25)
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()

    try:
        grid = generate_grid(
            args.rows,
            args.columns,
            args.wall_probability,
            args.seed,
        )
        map_path = save_grid(grid, PROJECT_DIR / "mapa.txt")
    except (OSError, ValueError) as error:
        parser.error(str(error))

    print(f"Mapa gerado: {map_path}")
    print("Inicio: (1, 1)")
    print(f"Destino: ({args.rows - 2}, {args.columns - 2})")
    print("O mapa anterior está salvo em mapa_antigo.txt.")


if __name__ == "__main__":
    main()
