# Importando bibliotecas

import pandas as pd

import csv

import numpy as np

# Caminho do arquivo CSV

arquivo = "../dataset/dataset.csv"

# Abrindo o arquivo CSV

df = pd.read_csv(arquivo, sep = ",")

# Visualizando as 5 primeiras linhas do DataFrame

print(df.head(10))

###########

# TRATAMENTO DE DADOS #

###########

# Exportando o arquivo CSV após tratamento de dados

df.to_csv('../dataset/dataset_tratado.csv', 
          index = False, 
          quoting = csv.QUOTE_MINIMAL)