from __future__ import annotations

import argparse
import random
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

Coordinate = tuple[int, int]
Genome = list[str]

DIRECTIONS: dict[str, Coordinate] = {
    "U": (-1, 0),
    "D": (1, 0),
    "L": (0, -1),
    "R": (0, 1),
}


@dataclass(frozen=True)
class Evaluation:
    reached_goal: bool
    path: tuple[Coordinate, ...]
    steps: int
    turns: int
    safety_penalty: int

    @property
    def cost(self) -> int:
        return self.steps + self.turns + self.safety_penalty


@dataclass(frozen=True)
class SearchResult:
    evaluation: Evaluation
    generations: int
    elapsed_seconds: float


def load_grid(path: Path) -> list[list[int]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ValueError(f"Could not read map file: {path}") from error

    if not lines:
        raise ValueError("The map is empty.")

    grid: list[list[int]] = []
    width = len(lines[0].strip())
    if width == 0:
        raise ValueError("The map contains an empty row.")
    for row_number, line in enumerate(lines, start=1):
        row = line.strip()
        if len(row) != width:
            raise ValueError(f"Map row {row_number} has a different width.")
        if any(cell not in "01" for cell in row):
            raise ValueError(f"Map row {row_number} contains a character other than 0 or 1.")
        grid.append([int(cell) for cell in row])
    return grid


def validate_endpoint(grid: list[list[int]], point: Coordinate, label: str) -> None:
    row, column = point
    if not (0 <= row < len(grid) and 0 <= column < len(grid[0])):
        raise ValueError(f"{label} coordinate {point} is outside the map.")
    if grid[row][column] == 1:
        raise ValueError(f"{label} coordinate {point} is a wall.")


def shortest_route(
    grid: list[list[int]], start: Coordinate, goal: Coordinate
) -> Genome:
    queue = deque([start])
    predecessors: dict[Coordinate, tuple[Coordinate, str] | None] = {start: None}

    while queue:
        current = queue.popleft()
        if current == goal:
            break
        for direction, (row_delta, column_delta) in DIRECTIONS.items():
            neighbor = (current[0] + row_delta, current[1] + column_delta)
            row, column = neighbor
            if not (
                0 <= row < len(grid)
                and 0 <= column < len(grid[0])
                and grid[row][column] == 0
                and neighbor not in predecessors
            ):
                continue
            predecessors[neighbor] = (current, direction)
            queue.append(neighbor)

    if goal not in predecessors:
        raise ValueError(f"No path exists from {start} to {goal}.")

    route: Genome = []
    current = goal
    while current != start:
        parent = predecessors[current]
        if parent is None:
            raise RuntimeError("Route reconstruction failed.")
        current, direction = parent
        route.append(direction)
    route.reverse()
    return route


def safety_at(grid: list[list[int]], point: Coordinate) -> int:
    row, column = point
    penalty = 0
    for row_offset in range(-2, 3):
        for column_offset in range(-2, 3):
            if max(abs(row_offset), abs(column_offset)) not in (1, 2):
                continue
            neighbor_row = row + row_offset
            neighbor_column = column + column_offset
            if (
                0 <= neighbor_row < len(grid)
                and 0 <= neighbor_column < len(grid[0])
                and grid[neighbor_row][neighbor_column] == 1
            ):
                penalty += 1
    return penalty


def evaluate(
    grid: list[list[int]], start: Coordinate, goal: Coordinate, genome: Genome
) -> Evaluation:
    position = start
    path = [start]
    turns = 0
    safety_penalty = 0
    previous_direction: str | None = None

    for direction in genome:
        if direction not in DIRECTIONS:
            break
        row_delta, column_delta = DIRECTIONS[direction]
        next_position = (position[0] + row_delta, position[1] + column_delta)
        row, column = next_position
        if not (0 <= row < len(grid) and 0 <= column < len(grid[0])):
            break
        if grid[row][column] == 1:
            break

        if previous_direction is not None and direction != previous_direction:
            turns += 1
        position = next_position
        path.append(position)
        safety_penalty += safety_at(grid, position)
        previous_direction = direction
        if position == goal:
            break

    return Evaluation(
        reached_goal=position == goal,
        path=tuple(path),
        steps=len(path) - 1,
        turns=turns,
        safety_penalty=safety_penalty,
    )


def rank_key(evaluation: Evaluation) -> tuple[int, int]:
    return (0 if evaluation.reached_goal else 1, evaluation.cost)


def crossover(first: Genome, second: Genome, rng: random.Random) -> Genome:
    first_cut = rng.randrange(len(first) + 1)
    second_cut = rng.randrange(len(second) + 1)
    return first[:first_cut] + second[second_cut:]


def mutate(genome: Genome, rng: random.Random, rate: float = 0.08) -> Genome:
    return [
        rng.choice(tuple(DIRECTIONS)) if rng.random() < rate else direction
        for direction in genome
    ]


def run_genetic_algorithm(
    grid: list[list[int]],
    start: Coordinate,
    goal: Coordinate,
    population_size: int = 120,
    max_generations: int = 400,
    elite_count: int = 6,
    mutation_rate: float = 0.08,
    seed: int | None = None,
) -> SearchResult:
    if population_size < 2:
        raise ValueError("Population size must be at least 2.")
    if max_generations < 0:
        raise ValueError("Maximum generations cannot be negative.")
    if not 1 <= elite_count < population_size:
        raise ValueError("Elite count must be between 1 and population size - 1.")
    if not 0 <= mutation_rate <= 1:
        raise ValueError("Mutation rate must be between 0 and 1.")
    validate_endpoint(grid, start, "Start")
    validate_endpoint(grid, goal, "Goal")

    rng = random.Random(seed)
    seed_route = shortest_route(grid, start, goal)
    population = [seed_route.copy()]
    while len(population) < population_size:
        population.append(mutate(seed_route, rng, rate=0.12))

    started_at = time.perf_counter()
    generations = 0
    best: Evaluation | None = None
    for generation in range(max_generations + 1):
        ranked = sorted(
            ((evaluate(grid, start, goal, genome), genome) for genome in population),
            key=lambda item: rank_key(item[0]),
        )
        best = ranked[0][0]
        generations = generation
        if generation == max_generations or not best.reached_goal:
            break

        parent_pool = ranked[: max(elite_count, population_size // 2)]
        next_population = [genome.copy() for _, genome in ranked[:elite_count]]
        while len(next_population) < population_size:
            first = rng.choice(parent_pool)[1]
            second = rng.choice(parent_pool)[1]
            child = crossover(first, second, rng)
            next_population.append(mutate(child, rng, mutation_rate))
        population = next_population

    if best is None:
        raise RuntimeError("The algorithm did not evaluate a population.")
    return SearchResult(best, generations, time.perf_counter() - started_at)


def render_grid(
    grid: list[list[int]], path: tuple[Coordinate, ...], start: Coordinate, goal: Coordinate
) -> str:
    display = [["#" if cell else "." for cell in row] for row in grid]
    for row, column in path:
        if (row, column) not in (start, goal):
            display[row][column] = "*"
    display[start[0]][start[1]] = "A"
    display[goal[0]][goal[1]] = "B"
    return "\n".join("".join(row) for row in display)


def parse_coordinate(value: str) -> Coordinate:
    try:
        row, column = (int(part.strip()) for part in value.split(","))
    except (ValueError, TypeError) as error:
        raise argparse.ArgumentTypeError("Use row,column. For example, 1,1.") from error
    return row, column


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, default=Path(__file__).parent / "mapa.txt")
    parser.add_argument("--start", type=parse_coordinate, default=(1, 1))
    parser.add_argument("--goal", type=parse_coordinate)
    parser.add_argument("--population", type=int, default=120)
    parser.add_argument("--generations", type=int, default=400)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    try:
        grid = load_grid(args.map)
        goal = (
            args.goal
            if args.goal is not None
            else (len(grid) - 2, len(grid[0]) - 2)
        )
        result = run_genetic_algorithm(
            grid,
            args.start,
            goal,
            population_size=args.population,
            max_generations=args.generations,
            seed=args.seed,
        )
    except ValueError as error:
        parser.error(str(error))

    evaluation = result.evaluation
    print(render_grid(grid, evaluation.path, args.start, goal))
    print(f"\nCaminho encontrado: {'sim' if evaluation.reached_goal else 'nao'}")
    print(f"Quantidade de passos: {evaluation.steps}")
    print(f"Quantidade de curvas: {evaluation.turns}")
    print(f"Penalidade de segurança: {evaluation.safety_penalty}")
    print(f"Aptidão: {evaluation.cost}")
    print(f"Quantidade de gerações: {result.generations}")
    print(f"Tempo percorrido: {result.elapsed_seconds:.6f} s")
    if evaluation.reached_goal:
        print("Coordenadas (linha,coluna): " + " -> ".join(map(str, evaluation.path)))


if __name__ == "__main__":
    main()
