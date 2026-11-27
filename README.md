
# Algoritmo Genético de Path Finding

Algoritmo genético feito em Python para encontrar uma rota viável em um mapa
representado como uma matriz 2D, com suporte a vários objetivos.

## Executar

Requer Python 3.10+ e não usa dependências externas.  
Para gerar um mapa pro algoritmo:

```powershell
python generate_map.py --seed 7
```

Para rodar o algoritmo em si:

```powershell
python genetic_pathfinder.py
```

Quando se gera um mapa, ele é salvo em mapa.txt e já é utilizado como padrão pelo algoritmo.

Para personalizar os parâmetros do algoritmo:

```powershell
python genetic_pathfinder.py --mapa mapa.txt --inicio 1,1 --destinos 13,23 --populacao 120 --geracoes 400 --seed 7
```

Informe um ou mais objetivos com `--destinos`:

```powershell
python genetic_pathfinder.py --mapa mapa.txt --inicio 1,1 --destinos 3,4 8,12 10,2 --populacao 120 --geracoes 400 --seed 7
```

## Gerador de mapa

O gerador cria um mapa aleatório de padrão sendo 15 por 25, e garante um corredor entre o topo esquerdo e o fundo direito do mapa, para sempre ser um mapa válido pro algoritmo.

As dimensões e a probabilidade de paredes podem ser alteradas:

```powershell
python generate_map.py --linhas 20 --colunas 30 --probabilidade-paredes 0.3
```

## Aptidão e algoritmo

A aptidão utilizada é a soma dos passos, curvas e das penalidades de segurança.  
Cada posição na matriz que o caminho passa é considerada um passo.  
Uma curva é classificada como uma mudança de direção entre dois passos.  
E para cada posição percorrida (exceto o ponto inicial), cada parede nos anéis de distância de  
Chebyshev 1 e 2 adiciona um ponto de penalidade, determinada como uma penalidade de segurança.

A população inicial contém permutações de todos os objetivos presentes. A busca em largura
calcula os trechos viáveis entre cada par de pontos. A aptidão soma passos,
curvas e penalidades de segurança na rota completa. Em cada geração, os
melhores indivíduos são preservados (elitismo) e os demais são criados com
crossover e mutação de permutação. Para um objetivo, existe apenas uma ordem e
a avaliação termina após a primeira geração. Porém, com vários objetivos a evolução
continua até o limite configurado de gerações.

Após terminar, os dados do algoritmo são mostrados para o usuário, sendo uma representação
do caminho encontrado, os passos, as penalidades de segurança (por estar perto de paredes), 
a aptidão (sendo a soma das penalidades), a quantidade de gerações, e o tempo percorrido pelo algoritmo.
