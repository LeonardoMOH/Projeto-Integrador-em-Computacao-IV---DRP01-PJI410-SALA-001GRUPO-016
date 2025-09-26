# Projeto Integrador em Computação IV - DRP01-PJI410-SALA-001GRUPO-016

Repositório da disciplina do Projeto Integrador em Computação IV pela Univesp do grupo DRP-01-PJI410-SALA-001GRUPO-016.

## Sumário
1. [Tema](#tema)
2. [Problema](#problema)
3. [Objetivo](#objetivo)
4. [Recursos de Dados](#recursos-de-dados)
   - [Dataset Entrada e Saída em CSV](analise_dados_flask\dataset\csv_estacionamento.csv)
   - [Dataset Entrada e Saída em CSV Tratado](analise_dados_flask\dataset\csv_estacionamento_tratado.csv)
   - [Dataset Pagamento em CSV](analise_dados_flask\dataset\pagamentos_placas.csv)
   - [Dataset Pagamento em CSV Tratado](analise_dados_flask\dataset\pagamentos_placas_tratado.csv)
5. [Aplicativo Flask para Análise de Dados de Estacionamento](#aplicativo-flask-para-análise-de-dados-de-estacionamento)
   - [Funcionalidades](#funcionalidades)
6. [Detalhes do Código](#detalhes-do-código)
   - [`app.py`](#apppy)
   - [`index.html`](#indexhtml)
7. [Resultados](#resultados)

---

## Tema

Desenvolvimento de interface para Análise de Dados de um sistema de controle de estacionamento utilizado instituição religiosa. Disponibilizando Análise Descritiva, Análise Preditiva, Análise Exploratória e Machine Learning.

## Problema

Uma instituição religiosa possui um amplo estacionamento onde o uso por seus membros é franqueado, mas, existe procura por pessoas que se tornam mensalistas devido à boa localização (Próxima à estação Mogi das Cruzes e na rota das linhas de ônibus executivos). Neste cenário, a movimentação diária com entradas e saídas de veículos, além da necessidade de controle financeiro, geram acúmulo de dados que precisam ser mais bem aproveitados para tomadas de decisões embasadas em uma visão clara dos dados.

## Objetivo

Transformar registros operacionais em informações estratégicas, permitindo:
* Identificação de horários de pico e períodos de baixa demanda;
* Monitoramento da rotatividade e tempo médio de permanência;
* Classificação de perfis de usuários inadimplentes;
* Detecção de comportamentos atípicos ou recorrentes;
* Apoio à tomada de decisões para melhorias operacionais.

Também faz parte do objetivo cumprir, por meio deste projeto, todos os requisitos da disciplina acadêmica.

## Recursos de Dados

* [**Dataset Entrada e Saída em CSV**](analise_dados_flask\dataset\csv_estacionamento.csv)
* [**Dataset Entrada e Saída em CSV Tratado**](analise_dados_flask\dataset\csv_estacionamento_tratado.csv)
* [**Dataset Pagamento em CSV**](analise_dados_flask\dataset\pagamentos_placas.csv)
* [**Dataset Pagamento em CSV Tratado**](analise_dados_flask\dataset\pagamentos_placas_tratado.csv)

## Aplicativo Flask para Análise de Dados de Estacionamento

Este é um aplicativo web simples construído com Flask para realizar a análise exploratória de dados de registros de estacionamento. Ele processa um arquivo CSV, trata os dados e gera diversos gráficos para visualizar padrões de duração de permanência por dia da semana, média geral, distribuição de duração e padrões de uso ao longo do dia.

### Funcionalidades

* **Processamento de Dados:** Lê dados de estacionamento de um arquivo CSV.
* **Tratamento de Dados:**
    * Converte strings de data e hora em objetos `datetime`.
    * Calcula a duração da permanência em horas.
    * Extrai o mês, o dia da semana e a hora de entrada.
    * Trata casos de saída no dia seguinte e valores ausentes.
    * Cria um arquivo CSV tratado no diretório `dataset` do projeto.
* **Análise Exploratória de Dados (EDA):** Gera os seguintes gráficos:
    1.  **Média de Duração por Dia da Semana:** Um gráfico de barras mostrando a duração média de permanência em cada dia da semana.
    2.  **Média de Duração Geral:** Um gráfico de barras simples exibindo a duração média de permanência em todo o conjunto de dados.
    3.  **Histograma da Duração de Permanência:** Um histograma para visualizar a distribuição das durações de permanência.
    4.  **Box Plot da Duração por Mês:** Um box plot que mostra a distribuição da duração de permanência para cada mês.
    5.  **Mapa de Calor da Duração Média por Hora de Entrada e Dia da Semana:** Um mapa de calor que visualiza a duração média de permanência em diferentes horas do dia e dias da semana, identificando horários de pico ou padrões de uso.
* **Visualização Web:** Apresenta os gráficos e estatísticas (como o total de registros) de forma interativa em uma página web.

## Detalhes do Código

### `app.py`

Este arquivo contém a lógica de backend do aplicativo.

  * **Importações**: Carrega todas as bibliotecas utilizadas no arquivo python, como `pandas` (manipulação de dados), `numpy` (operações numéricas), `matplotlib` e `seaborn` (geração de gráficos), `flask` (framework web), `io` e `base64` (para codificar imagens dos gráficos).
  * **`formatar_duracao_numerica(td)`**: Função auxiliar que converte objetos `Timedelta` (diferenças de tempo) em um valor numérico representando a duração em horas.
  * **`tratar_dados_estacionamento(df)`**: A função principal de pré-processamento de dados. Ela realiza:
      * Combinação de 'Data' com 'Entrada' e 'Saida' para criar *timestamps* completos.
      * Cálculo da `Duracao` da permanência em horas.
      * Extração de 'Marca' e 'Modelo' da coluna 'Marca/Modelo'.
      * Adição de colunas auxiliares como 'Mes', 'Dia\_Semana' e 'Hora\_Entrada' para análises.
      * Tratamento de casos onde a saída ocorre no dia seguinte à entrada.
      * Remoção de linhas com valores ausentes (`NaN`) em colunas críticas.
  * **`gerar_grafico(fig, ax, title, xlabel, ylabel, show_values_on_bars)`**: Uma função utilitária que encapsula a geração e codificação de gráficos. Ela recebe uma figura e um eixo do Matplotlib, configura títulos e rótulos, e opcionalmente adiciona valores nas barras. O gráfico é salvo em um *stream* de memória, codificado em Base64 e retornado como uma string, permitindo a incorporação direta no HTML.
  * **`realizar_analise_completa()`**: função principal de análise de dados:
      * Tenta carregar o `csv_estacionamento.csv` do diretório `dataset/`. Em caso de erro (ex: arquivo não encontrado), retorna uma mensagem de erro.
      * Invoca `tratar_dados_estacionamento()` para preparar o DataFrame.
      * Gera os 5 gráficos de análise exploratória descritos nas [Funcionalidades](#funcionalidades), utilizando Matplotlib/Seaborn e a função `gerar_grafico()`.
      * Salva o DataFrame tratado como `csv_estacionamento_tratado.csv` na pasta `dataset/`.
      * Retorna um dicionário com estatísticas (atualmente, `total_registros`) e as strings Base64 de todos os gráficos gerados.
  * **`@app.route('/')` (função `index()`):** Define a rota para a página inicial (`/`). Quando acessada, ela:
      * Chama `realizar_analise_completa()` para obter os dados processados e os gráficos.
      * Verifica se houve um erro na leitura ou tratamento do CSV e, se sim, renderiza a página `erro.html`.
      * Caso contrário, renderiza o template `index.html`, passando todas as estatísticas e os gráficos para exibição.

### `index.html`

Este é o template HTML que compõe a interface do usuário.

  * **Exibição de Estatísticas**: Mostra o `Total de Registros` utilizando a sintaxe `{{ estatisticas.total_registros }}`
  * **Estrutura de Gráficos**: Cada gráfico é encapsulado em uma `div` com a classe `chart` para organização.
  * **Incorporação de Imagens**: Utiliza a tag `<img>` com o atributo `src="data:image/png;base64,{{ nome_da_variavel_do_grafico }}"` para incorporar as imagens dos gráficos diretamente no HTML. Isso elimina a necessidade de salvar arquivos de imagem temporários no servidor.
  * **Mensagens de Erro**: Inclui blocos condicionais do Jinja (`{% if ... %}`) para exibir mensagens de erro amigáveis caso um gráfico específico não possa ser gerado (e.g., por falta de dados).

## Resultados

Abaixo, algumas imagens dos gráficos gerados pelo aplicativo:

*Gráfico 1: Média de Duração por Dia da Semana*
![resultado](imagens\resultados_1.png)

*Gráfico 2: Média de Duração Geral e Histograma da Duração de Permanência*
![resultado](imagens\resultados_2.png)

*Gráfico 3: Box Plot da Duração por Mês e Mapa de Calor da Duração Média*
![resultado](imagens\resultados_3.png)