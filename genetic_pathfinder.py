from __future__ import annotations

import argparse
import random
import time
from collections.abc import Sequence
from collections import deque
from dataclasses import dataclass
from pathlib import Path

Coordinate = tuple[int, int]
Genome = list[str]
Permutation = list[int]
RouteMatrix = dict[tuple[Coordinate, Coordinate], Genome]

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
    grid: list[list[int]],
    start: Coordinate,
    goal: Coordinate | Sequence[Coordinate],
    genome: Sequence[int] | Genome,
    routes: RouteMatrix | None = None,
) -> Evaluation:
    legacy_genome = (
        isinstance(goal, tuple)
        and len(goal) == 2
        and all(isinstance(value, int) for value in goal)
        and all(isinstance(direction, str) for direction in genome)
    )
    route_genome: Genome
    if legacy_genome:
        ordered_goals = (goal,)
        target = goal
        route_genome = [direction for direction in genome if isinstance(direction, str)]
    else:
        ordered_goals = _validate_goals(goal)
        order = tuple(index for index in genome if isinstance(index, int))
        if (
            len(order) != len(genome)
            or len(order) != len(ordered_goals)
            or set(order) != set(range(len(ordered_goals)))
        ):
            raise ValueError("Goal order must be a permutation of all goal indexes.")
        validate_endpoint(grid, start, "Start")
        for index, goal in enumerate(ordered_goals, start=1):
            validate_endpoint(grid, goal, f"Goal {index}")
        if start in ordered_goals:
            raise ValueError("Start coordinate cannot also be a goal.")
        route_matrix = routes or shortest_routes(grid, (start, *ordered_goals))
        route_genome = []
        pending = list(order)
        source = start
        while pending:
            target_index = pending.pop(0)
            target = ordered_goals[target_index]
            segment = route_matrix[(source, target)]
            route_genome.extend(segment)
            position = source
            for direction in segment:
                row_delta, column_delta = DIRECTIONS[direction]
                position = (position[0] + row_delta, position[1] + column_delta)
                pending = [
                    index for index in pending if ordered_goals[index] != position
                ]
            source = target

    position = start
    path = [start]
    turns = 0
    safety_penalty = 0
    previous_direction: str | None = None

    for direction in route_genome:
        if direction not in DIRECTIONS:
            break
        row_delta, column_delta = DIRECTIONS[direction]
        next_position = (position[0] + row_delta, position[1] + column_delta)
        row, column = next_position
        if not (
            0 <= row < len(grid)
            and 0 <= column < len(grid[0])
            and grid[row][column] == 0
        ):
            break

        if previous_direction is not None and direction != previous_direction:
            turns += 1
        position = next_position
        path.append(position)
        safety_penalty += safety_at(grid, position)
        previous_direction = direction
        if legacy_genome and position == target:
            break

    reached_all_goals = all(goal in path for goal in ordered_goals)
    return Evaluation(
        reached_goal=reached_all_goals
        and position == target,
        path=tuple(path),
        steps=len(path) - 1,
        turns=turns,
        safety_penalty=safety_penalty,
    )


def rank_key(evaluation: Evaluation) -> tuple[int, int]:
    return (0 if evaluation.reached_goal else 1, evaluation.cost)


def crossover_permutation(
    first: Permutation, second: Permutation, rng: random.Random
) -> Permutation:
    if (
        len(first) != len(second)
        or len(set(first)) != len(first)
        or set(first) != set(second)
    ):
        raise ValueError("Parents must contain the same permutation.")
    if len(first) < 2:
        return first.copy()

    start, end = sorted(rng.sample(range(len(first) + 1), 2))
    child = [-1] * len(first)
    child[start:end] = first[start:end]
    used = set(child[start:end])
    position = end % len(first)
    for value in second[end:] + second[:end]:
        if value in used:
            continue
        while child[position] != -1:
            position = (position + 1) % len(first)
        child[position] = value
        used.add(value)
    return child


def mutate_permutation(
    permutation: Permutation, rng: random.Random, rate: float = 0.08
) -> Permutation:
    mutated = permutation.copy()
    if len(mutated) > 1 and rng.random() < rate:
        first, second = rng.sample(range(len(mutated)), 2)
        mutated[first], mutated[second] = mutated[second], mutated[first]
    return mutated


def parse_goals(values: Sequence[str]) -> tuple[Coordinate, ...]:
    goals = tuple(parse_coordinate(value) for value in values)
    return _validate_goals(goals)


def _validate_goals(
    goals: Coordinate | Sequence[Coordinate],
) -> tuple[Coordinate, ...]:
    normalized = (
        (goals,)
        if isinstance(goals, tuple)
        and len(goals) == 2
        and all(isinstance(value, int) for value in goals)
        else tuple(goals)
    )
    if not normalized:
        raise ValueError("At least one goal must be provided.")
    if len(set(normalized)) != len(normalized):
        raise ValueError("Goal coordinates must be unique.")
    return normalized


def shortest_routes(
    grid: list[list[int]], points: Sequence[Coordinate]
) -> RouteMatrix:
    routes: RouteMatrix = {}
    for source in points:
        for target in points:
            routes[(source, target)] = shortest_route(grid, source, target)
    return routes


def _validate_search_parameters(
    population_size: int,
    max_generations: int,
    elite_count: int | None,
    mutation_rate: float,
) -> int:
    if population_size < 2:
        raise ValueError("Population size must be at least 2.")
    if max_generations < 0:
        raise ValueError("Maximum generations cannot be negative.")
    if elite_count is None:
        elite_count = min(6, population_size - 1)
    if not 1 <= elite_count < population_size:
        raise ValueError("Elite count must be between 1 and population size - 1.")
    if not 0 <= mutation_rate <= 1:
        raise ValueError("Mutation rate must be between 0 and 1.")
    return elite_count


def run_genetic_algorithm(
    grid: list[list[int]],
    start: Coordinate,
    goal: Coordinate | Sequence[Coordinate],
    population_size: int = 120,
    max_generations: int = 400,
    elite_count: int | None = None,
    mutation_rate: float = 0.08,
    seed: int | None = None,
) -> SearchResult:
    elite_count = _validate_search_parameters(
        population_size, max_generations, elite_count, mutation_rate
    )
    validate_endpoint(grid, start, "Start")
    ordered_goals = _validate_goals(goal)
    for index, goal in enumerate(ordered_goals, start=1):
        validate_endpoint(grid, goal, f"Goal {index}")
    if start in ordered_goals:
        raise ValueError("Start coordinate cannot also be a goal.")

    routes = shortest_routes(grid, (start, *ordered_goals))
    rng = random.Random(seed)
    initial_order = list(range(len(ordered_goals)))
    population = [initial_order.copy()]
    while len(population) < population_size:
        permutation = initial_order.copy()
        rng.shuffle(permutation)
        population.append(permutation)

    started_at = time.perf_counter()
    best: Evaluation | None = None
    generations = 0
    for generation in range(max_generations + 1):
        ranked = sorted(
            (
                (evaluate(grid, start, ordered_goals, order, routes), order)
                for order in population
            ),
            key=lambda item: rank_key(item[0]),
        )
        best = ranked[0][0]
        generations = generation
        if generation == max_generations or len(ordered_goals) == 1:
            break

        parent_pool = ranked[: max(elite_count, population_size // 2)]
        next_population = [order.copy() for _, order in ranked[:elite_count]]
        while len(next_population) < population_size:
            first = rng.choice(parent_pool)[1]
            second = rng.choice(parent_pool)[1]
            child = crossover_permutation(first, second, rng)
            next_population.append(mutate_permutation(child, rng, mutation_rate))
        population = next_population

    if best is None:
        raise RuntimeError("The algorithm did not evaluate a population.")
    return SearchResult(best, generations, time.perf_counter() - started_at)


def ordered_goals_from_path(
    path: Sequence[Coordinate], goals: Sequence[Coordinate]
) -> tuple[Coordinate, ...]:
    goal_set = set(goals)
    found: list[Coordinate] = []
    for point in path:
        if point in goal_set and point not in found:
            found.append(point)
    return tuple(found)


def alphabetic_label(index: int) -> str:
    if index < 0:
        raise ValueError("Label index cannot be negative.")
    label = ""
    while index >= 0:
        index, remainder = divmod(index, 26)
        label = chr(ord("A") + remainder) + label
        index -= 1
    return label


def render_grid(
    grid: list[list[int]],
    path: tuple[Coordinate, ...],
    start: Coordinate,
    goal: Coordinate | Sequence[Coordinate],
) -> str:
    goals = _validate_goals(goal)
    display = [["#" if cell else "." for cell in row] for row in grid]
    for row, column in path:
        point = (row, column)
        if point != start and point not in goals:
            display[row][column] = "*"
    display[start[0]][start[1]] = "A"
    for index, point in enumerate(goals, start=1):
        display[point[0]][point[1]] = alphabetic_label(index)
    return "\n".join("".join(row) for row in display)


def parse_coordinate(value: str) -> Coordinate:
    try:
        row, column = (int(part.strip()) for part in value.split(","))
    except (ValueError, TypeError) as error:
        raise argparse.ArgumentTypeError("Use row,column. For example, 1,1.") from error
    return row, column


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mapa",
        type=Path,
        default=Path(__file__).parent / "mapa.txt",
    )
    parser.add_argument(
        "--inicio",
        type=parse_coordinate,
        default=(1, 1),
    )
    parser.add_argument(
        "--destinos",
        nargs="+",
    )
    parser.add_argument(
        "--populacao",
        type=int,
        default=120,
    )
    parser.add_argument(
        "--geracoes",
        type=int,
        default=400,
    )
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    try:
        grid = load_grid(args.mapa)
        if args.destinos is not None:
            goals = parse_goals(args.destinos)
        else:
            goal = (len(grid) - 2, len(grid[0]) - 2)
            goals = (goal,)
        result = run_genetic_algorithm(
            grid,
            args.inicio,
            goals,
            population_size=args.populacao,
            max_generations=args.geracoes,
            seed=args.seed,
        )
        route_goals = ordered_goals_from_path(result.evaluation.path, goals)
        if len(route_goals) != len(goals):
            raise RuntimeError("The completed route did not visit every goal.")
        if len(route_goals) > 1:
            print("Ordem dos objetivos: " + " -> ".join(map(str, route_goals)))
    except (argparse.ArgumentTypeError, ValueError) as error:
        parser.error(str(error))

    evaluation = result.evaluation
    print(render_grid(grid, evaluation.path, args.inicio, route_goals))
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
