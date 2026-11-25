
# Algoritmo Genético de Path Finding

Algoritmo genético feito em Python para encontrar o menor caminho viável  
entre dois pontos de um mapa, que é representado como uma matriz 2D.

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
python genetic_pathfinder.py --map mapa.txt --start 1,1 --goal 13,23 --population 120 --generations 400 --seed 7
```

## Gerador de mapa

O gerador cria um mapa aleatório de padrão sendo 15 por 25, e garante um corredor entre o topo esquerdo e o fundo direito do mapa, para sempre ser um mapa válido pro algoritmo.

As dimensões e a probabilidade de paredes podem ser alteradas:

```powershell
python generate_random_map.py --rows 20 --columns 30 --wall-probability 0.3
```

## Aptidão e algoritmo

A aptidão utilizada é a soma dos passos, curvas e das penalidades de segurança.  
Cada posição na matriz que o caminho passa é considerada um passo.  
Uma curva é classificada como uma mudança de direção entre dois passos.  
E para cada posição percorrida (exceto o ponto inicial), cada parede nos anéis de distância de  
Chebyshev 1 e 2 adiciona um ponto de penalidade, determinada como uma penalidade de segurança.

A população inicial parte de uma rota válida mais curta, calculada por busca em  
largura, e cria variações dela. Em cada geração, os melhores indivíduos são  
preservados (elitismo) e os demais são criados com crossover de um ponto entre  
dois pais e mutação por substituição aleatória de direções. 
O algoritmo para quando a rota inicial é completa, ou ao atingir o limite de gerações.

Após terminar, os dados do algoritmo são mostrados para o usuário, sendo uma representação
do caminho encontrado, os passos, as penalidades de segurança (por estar perto de paredes), 
a aptidão (sendo a soma das penalidades), a quantidade de gerações, e o tempo percorrido pelo algoritmo.
