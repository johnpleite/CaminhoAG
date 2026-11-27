import argparse
import os
import random
import tempfile
from pathlib import Path

Grid = list[list[int]]
PROJECT_DIR = Path(__file__).resolve().parent


def generate_grid(
    linhas: int = 15,
    colunas: int = 25,
    probabilidade_paredes: float = 0.25,
    seed: int | None = None,
) -> Grid:
    if linhas < 3 or colunas < 3:
        raise ValueError("Map dimensions must be at least 3 by 3.")
    if not 0 <= probabilidade_paredes <= 1:
        raise ValueError("Wall probability must be between 0 and 1.")

    rng = random.Random(seed)
    grid = [
        [int(rng.random() < probabilidade_paredes) for _ in range(colunas)]
        for _ in range(linhas)
    ]

    for linha in range(linhas):
        grid[linha][0] = grid[linha][-1] = 1
    for coluna in range(colunas):
        grid[0][coluna] = grid[-1][coluna] = 1

    linha_destino, coluna_destino = linhas - 2, colunas - 2
    for coluna in range(1, coluna_destino + 1):
        grid[1][coluna] = 0
    for linha in range(1, linha_destino + 1):
        grid[linha][coluna_destino] = 0
    return grid


def save_grid(mapa: Grid, caminho_mapa: Path) -> Path:
    caminho_mapa.parent.mkdir(parents=True, exist_ok=True)
    caminho_arquivo = caminho_mapa.with_name("mapa_antigo.txt")
    if caminho_mapa.resolve() == caminho_arquivo.resolve():
        raise ValueError("The output map cannot be named mapa_antigo.txt.")

    conteudo = "\n".join("".join(map(str, linha)) for linha in mapa) + "\n"
    caminho_temporario: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=caminho_mapa.parent,
            delete=False,
        ) as arquivo_temporario:
            arquivo_temporario.write(conteudo)
            caminho_temporario = Path(arquivo_temporario.name)

        if caminho_mapa.exists():
            os.replace(caminho_mapa, caminho_arquivo)
        os.replace(caminho_temporario, caminho_mapa)
    finally:
        if caminho_temporario is not None and caminho_temporario.exists():
            caminho_temporario.unlink()
    return caminho_mapa


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linhas", type=int, default=15)
    parser.add_argument("--colunas", type=int, default=25)
    parser.add_argument("--probabilidade-paredes", type=float, default=0.25)
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()

    try:
        mapa = generate_grid(
            args.linhas,
            args.colunas,
            args.probabilidade_paredes,
            args.seed,
        )
        caminho_mapa = save_grid(mapa, PROJECT_DIR / "mapa.txt")
    except (OSError, ValueError) as error:
        parser.error(str(error))

    print(f"Mapa gerado: {caminho_mapa}")
    print("Inicio: (1, 1)")
    print(f"Destino: ({args.linhas - 2}, {args.colunas - 2})")
    print("O mapa anterior está salvo em mapa_antigo.txt.")


if __name__ == "__main__":
    main()
