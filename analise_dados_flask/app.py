# Importação de bibliotecas utilizadas no projeto
import pandas as pd
import numpy as np
import io
import base64
from datetime import datetime, date, time, timedelta
from flask import Flask, render_template
import csv
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

# Configuração da aplicação Flask
app = Flask(__name__)

# Função para formatar a duração em um valor numérico (horas)
def formatar_duracao_numerica(td):
    if pd.isna(td):
        return np.nan
    return td.total_seconds() / 3600

# Função para categorizar o período do dia (será usada para agrupar os resultados de ocupação horária)
def categorizar_periodo_agrupamento(hora_int):
    if 6 <= hora_int < 12:
        return 'Manhã'
    elif 12 <= hora_int < 18:
        return 'Tarde'
    else: # 18:00 até 05:59 do dia seguinte
        return 'Noite'

# Função para o tratamento de dados
def tratar_dados_estacionamento(df):
    df['Entrada_Completa'] = pd.to_datetime(df['Data'] + ' ' + df['Entrada'], format='%d/%m/%Y %H:%M', errors='coerce')
    df['Saida_Completa'] = pd.to_datetime(df['Data'] + ' ' + df['Saida'], format='%d/%m/%Y %H:%M', errors='coerce')
    df.dropna(subset=['Entrada_Completa', 'Saida_Completa'], inplace=True)
    df.loc[df['Saida_Completa'] < df['Entrada_Completa'], 'Saida_Completa'] += pd.Timedelta(days=1)
    df['Duracao_temp'] = df['Saida_Completa'] - df['Entrada_Completa']
    df['Marca'], df['Modelo'] = df['Marca/Modelo'].str.split('/', expand=True)
    df['Duracao'] = df['Duracao_temp'].apply(formatar_duracao_numerica)
    df['Mes'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce').dt.month
    df['Hora_Entrada'] = df['Entrada_Completa'].dt.hour
    df['Dia_Semana'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce').dt.day_name()
    df.dropna(subset=['Duracao', 'Mes', 'Dia_Semana', 'Hora_Entrada'], inplace=True)
    
    # print("\n--- Debug Tratamento de Dados Estacionamento ---")
    # print(f"df_tratado após tratamento ({len(df)} linhas):\n", df.head())
    # print("------------------------------------------------\n")
    return df

# --- Função para tratamento de dados de pagamento ---
def tratar_dados_pagamento(df_pagamentos):
    df_pagamentos['Data_Limite_Pagamento_DT'] = pd.to_datetime(df_pagamentos['Data do Pagamento'], format='%d/%m/%Y', errors='coerce')
    df_pagamentos['Dia_Efetuado'] = pd.to_numeric(df_pagamentos['Dia de Pagamento'], errors='coerce')
    df_pagamentos.dropna(subset=['Data_Limite_Pagamento_DT', 'Dia_Efetuado'], inplace=True)
    df_pagamentos['Dia_Limite'] = df_pagamentos['Data_Limite_Pagamento_DT'].dt.day
    df_pagamentos['Mes'] = df_pagamentos['Data_Limite_Pagamento_DT'].dt.month
    df_pagamentos['Ano'] = df_pagamentos['Data_Limite_Pagamento_DT'].dt.year

    df_pagamentos['Status_Pagamento'] = df_pagamentos.apply(
        lambda row: 'Em Dia' if row['Dia_Efetuado'] <= row['Dia_Limite'] else 'Inadimplente',
        axis=1
    )
    # print("\n--- Debug Tratamento de Dados Pagamento (NOVA LÓGICA) ---")
    # print(f"df_pagamentos_tratado após tratamento ({len(df_pagamentos)} linhas):\n")
    # print(df_pagamentos[['Placa', 'Dia de Pagamento', 'Dia_Efetuado', 'Data do Pagamento', 'Dia_Limite', 'Mes', 'Ano', 'Status_Pagamento']].head())
    # print("Contagem de Status de Pagamento:\n", df_pagamentos['Status_Pagamento'].value_counts())
    # print("----------------------------------------------------------\n")
    return df_pagamentos

# Recebe a figura e o eixo (função auxiliar para gráficos gerais)
def gerar_grafico(fig, ax, title="", xlabel="", ylabel="", show_values_on_bars=False, plot_type='bar', data=None, labels=None, colors=None, autopct=None):
    if plot_type == 'bar':
        ax.set_title(title)
        ax.grid(axis='y', linestyle='--', alpha=0.7)

        if show_values_on_bars:
            if hasattr(ax, 'patches') and ax.patches:
                for p in ax.patches:
                    if p.get_height() > 0:
                        ax.annotate(f"{p.get_height():.2f}", (p.get_x() + p.get_width() / 2., p.get_height()),
                                    ha='center', va='center', xytext=(0, 10), textcoords='offset points', fontsize=10)

    img_stream = io.BytesIO()
    fig.savefig(img_stream, format='png', bbox_inches='tight')
    img_stream.seek(0)
    img_base64 = base64.b64encode(img_stream.read()).decode('utf-8')
    plt.close(fig)
    return img_base64

# --- Função para gerar gráfico de setores de pagamento ---
def gerar_grafico_status_pagamento(df_pagamentos):
    if df_pagamentos.empty or 'Status_Pagamento' not in df_pagamentos.columns:
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.text(0.5, 0.5, "Sem dados para o gráfico de status de pagamento", horizontalalignment='center', verticalalignment='center', fontsize=12, color='gray')
        ax.axis('off')
        return gerar_grafico(fig, ax, title='Status de Pagamento dos Mensalistas', plot_type='bar')

    contagem_status = df_pagamentos['Status_Pagamento'].value_counts()
    
    ordered_labels = ['Em Dia', 'Inadimplente']
    actual_labels = [label for label in ordered_labels if label in contagem_status.index]
    actual_sizes = [contagem_status[label] for label in actual_labels]

    if not actual_sizes or sum(actual_sizes) == 0:
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.text(0.5, 0.5, "Sem dados para o gráfico de status de pagamento", horizontalalignment='center', verticalalignment='center', fontsize=12, color='gray')
        ax.axis('off')
        return gerar_grafico(fig, ax, title='Status de Pagamento dos Mensalistas', plot_type='bar')

    cmap = plt.get_cmap('RdYlGn')
    assigned_colors = []
    
    if 'Em Dia' in actual_labels and 'Inadimplente' in actual_labels:
        color_map_indices = [0.8 if label == 'Em Dia' else 0.2 for label in actual_labels]
        assigned_colors = [cmap(idx) for idx in color_map_indices]
    elif 'Em Dia' in actual_labels:
        assigned_colors.append(cmap(0.8))
    elif 'Inadimplente' in actual_labels:
        assigned_colors.append(cmap(0.2))

    explode = [0] * len(actual_labels)
    if 'Inadimplente' in actual_labels:
        explode[actual_labels.index('Inadimplente')] = 0.08
            
    if len(actual_labels) == 1:
        explode = (0,)

    fig, ax = plt.subplots(figsize=(8, 8))
    
    wedges, texts, autotexts = ax.pie(actual_sizes,
                                      colors=assigned_colors,
                                      autopct='%1.1f%%',
                                      startangle=90,
                                      wedgeprops={'edgecolor': 'black'},
                                      explode=explode)

    ax.set_title('Status de Pagamento dos Mensalistas')
    ax.axis('equal')

    legend_labels_with_count = [f'{l}: {s}' for l, s in zip(actual_labels, actual_sizes)]
    ax.legend(wedges, legend_labels_with_count,
              title="Status",
              loc="center left",
              bbox_to_anchor=(1, 0, 0.5, 1))

    for autotext in autotexts:
        autotext.set_color('black')
        autotext.set_fontsize(10)
    
    for text in texts:
        text.set_text('')

    img_stream = io.BytesIO()
    fig.savefig(img_stream, format='png', bbox_inches='tight')
    img_stream.seek(0)
    img_base64 = base64.b64encode(img_stream.read()).decode('utf-8')
    plt.close(fig)
    return img_base64


# --- Gráfico de Status de Pagamento por Mês (Em Dia vs. Inadimplente) ---
def gerar_grafico_status_pagamento_por_mes(df_pagamentos):
    if df_pagamentos.empty or 'Status_Pagamento' not in df_pagamentos.columns or 'Mes' not in df_pagamentos.columns:
        fig, ax = plt.subplots(figsize=(12, 7))
        ax.text(0.5, 0.5, "Sem dados para o gráfico de status de pagamento por mês", horizontalalignment='center', verticalalignment='center', fontsize=12, color='gray')
        ax.axis('off')
        return gerar_grafico(fig, ax, title='Status de Pagamento por Mês')

    meses_nomes = {
        1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
        7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
    }

    contagem_mensal = df_pagamentos.groupby(['Mes', 'Status_Pagamento']).size().unstack(fill_value=0)
    
    for status in ['Em Dia', 'Inadimplente']:
        if status not in contagem_mensal.columns:
            contagem_mensal[status] = 0

    contagem_mensal['Total_Mensal'] = contagem_mensal[['Em Dia', 'Inadimplente']].sum(axis=1)
    contagem_mensal = contagem_mensal[contagem_mensal['Total_Mensal'] > 0].drop(columns=['Total_Mensal'])

    if contagem_mensal.empty:
        fig, ax = plt.subplots(figsize=(12, 7))
        ax.text(0.5, 0.5, "Não há dados de pagamento ou inadimplência registrados para o período.", horizontalalignment='center', verticalalignment='center', fontsize=12, color='gray')
        ax.axis('off')
        return gerar_grafico(fig, ax, title='Status de Pagamento por Mês')

    meses_com_dados_numericos = contagem_mensal.index.tolist()
    meses_ordenados_nomes = [meses_nomes[m] for m in sorted(meses_com_dados_numericos)]
    contagem_mensal.index = contagem_mensal.index.map(meses_nomes)

    fig, ax = plt.subplots(figsize=(14, 7))
    
    contagem_mensal.loc[:, ['Em Dia', 'Inadimplente']].plot(kind='bar', ax=ax, color={'Em Dia': 'lightgreen', 'Inadimplente': 'salmon'}, width=0.8)
    
    ax.set_title('Status de Pagamento Mensal de Mensalistas', fontsize=16)
    ax.set_xlabel('Mês', fontsize=12)
    ax.set_ylabel('Número de Mensalistas', fontsize=12)
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.set_xticklabels(meses_ordenados_nomes, rotation=45, ha='right')
    ax.legend(title='Status', fontsize=10, title_fontsize=12)

    for container in ax.containers:
        for bar in container:
            height = bar.get_height()
            if height > 0:
                ax.annotate(f'{int(height)}', 
                            xy=(bar.get_x() + bar.get_width() / 2, height), 
                            xytext=(0, 3), 
                            textcoords="offset points",
                            ha='center', va='bottom',
                            fontsize=9, color='black')

    img_stream = io.BytesIO()
    fig.savefig(img_stream, format='png', bbox_inches='tight')
    img_stream.seek(0)
    img_base64 = base64.b64encode(img_stream.read()).decode('utf-8')
    plt.close(fig)
    return img_base64

# --- Função para gerar gráfico de Agrupamento (K-Means) ---
def gerar_grafico_kmeans_estacionamento(df_estacionamento):
    # Selecionar as features para o agrupamento
    features = ['Duracao', 'Hora_Entrada']
    df_cluster = df_estacionamento[features].copy()
    df_cluster.dropna(inplace=True)

    if df_cluster.empty or len(df_cluster) < 2:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, "Dados insuficientes para o agrupamento K-Means", horizontalalignment='center', verticalalignment='center', fontsize=12, color='gray')
        ax.axis('off')
        return gerar_grafico(fig, ax, title='Padrões de Duração de Estacionamento (K-Means)')

    # Escalar os dados
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(df_cluster)
    
    # K=3 com o algoritmo K-Means
    n_clusters = 3 

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df_cluster['Cluster'] = kmeans.fit_predict(scaled_features)

    fig, ax = plt.subplots(figsize=(12, 7))
    sns.scatterplot(x='Hora_Entrada', y='Duracao', hue='Cluster', data=df_cluster, 
                    palette='viridis', s=100, alpha=0.7, ax=ax)
    
    # Adicionar os centroides dos clusters
    centroids = scaler.inverse_transform(kmeans.cluster_centers_)
    ax.scatter(centroids[:, 1], centroids[:, 0], marker='X', s=200, color='red', label='Centroides', edgecolor='black')


    ax.set_title(f'Padrões de Duração de Estacionamento (K-Means, K={n_clusters})', fontsize=16)
    ax.set_xlabel('Hora de Entrada', fontsize=12)
    ax.set_ylabel('Duração (horas)', fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend(title='Cluster', bbox_to_anchor=(1.05, 1), loc='upper left')

    img_stream = io.BytesIO()
    fig.savefig(img_stream, format='png', bbox_inches='tight')
    img_stream.seek(0)
    img_base64 = base64.b64encode(img_stream.read()).decode('utf-8')
    plt.close(fig)
    return img_base64

# Função principal para realizar toda a análise de dados
def realizar_analise_completa():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # --- Análise do csv_estacionamento.csv ---
    caminho_csv_estacionamento = os.path.join(script_dir, 'dataset', 'csv_estacionamento.csv')
    estacionamento_msg_erro = None
    df_estacionamento_tratado = pd.DataFrame()
    total_registros_estacionamento = 0
    
    grafico_dia_semana = None
    grafico_media_geral = None
    grafico_histograma_duracao = None
    grafico_boxplot_duracao_mes = None
    grafico_heatmap_duracao = None
    grafico_ocupacao_periodo = None
    grafico_kmeans_estacionamento = None

    try:
        df_estacionamento = pd.read_csv(caminho_csv_estacionamento, delimiter=';')
        df_estacionamento_tratado = tratar_dados_estacionamento(df_estacionamento.copy())
    except FileNotFoundError:
        estacionamento_msg_erro = f"Erro: Arquivo '{caminho_csv_estacionamento}' não encontrado."
    except Exception as e:
        estacionamento_msg_erro = f"Erro ao processar '{caminho_csv_estacionamento}': {e}"

    if estacionamento_msg_erro is None and not df_estacionamento_tratado.empty:
        total_registros_estacionamento = len(df_estacionamento_tratado)
        # Verificar se as colunas essenciais para calculo de ocupacao estão presentes
        if 'Duracao' not in df_estacionamento_tratado.columns or \
           'Mes' not in df_estacionamento_tratado.columns or \
           'Dia_Semana' not in df_estacionamento_tratado.columns or \
           'Hora_Entrada' not in df_estacionamento_tratado.columns or \
           'Entrada_Completa' not in df_estacionamento_tratado.columns or \
           'Saida_Completa' not in df_estacionamento_tratado.columns:
            estacionamento_msg_erro = "Erro: Colunas essenciais ausentes em 'csv_estacionamento.csv' após tratamento para calcular ocupação."
        else:
            dias_semana_portugues = {
                'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta',
                'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
            }
            dias_ordenados = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']

            # 1. Gráfico de Média de Duração por Dia da Semana
            if not df_estacionamento_tratado['Duracao'].dropna().empty and 'Dia_Semana' in df_estacionamento_tratado.columns:
                media_por_dia = df_estacionamento_tratado.groupby('Dia_Semana')['Duracao'].mean()
                media_por_dia.index = media_por_dia.index.map(dias_semana_portugues)
                media_por_dia = media_por_dia.reindex(dias_ordenados)
                if not media_por_dia.dropna().empty:
                    fig_dia_semana, ax_dia_semana = plt.subplots(figsize=(10, 6))
                    media_por_dia.dropna().plot(kind='bar', color='skyblue', ax=ax_dia_semana)
                    ax_dia_semana.set_xticklabels(media_por_dia.dropna().index, rotation=45, ha='right')
                    grafico_dia_semana = gerar_grafico(fig_dia_semana, ax_dia_semana,
                                                       title='Média de Duração por Dia da Semana', xlabel='Dia da Semana', ylabel='Média de Duração (horas)',
                                                       show_values_on_bars=True)
            # 2. Gráfico de Média de Duração Geral
            if not df_estacionamento_tratado['Duracao'].dropna().empty:
                media_geral_valor = df_estacionamento_tratado['Duracao'].mean()
                fig_media_geral, ax_media_geral = plt.subplots(figsize=(4, 6))
                ax_media_geral.bar(x=['Média Geral'], height=[media_geral_valor], color='lightgreen')
                ax_media_geral.set_ylim(0, media_geral_valor * 1.2 if media_geral_valor > 0 else 1)
                grafico_media_geral = gerar_grafico(fig_media_geral, ax_media_geral,
                                                     title='Média de Duração Geral', xlabel='', ylabel='Média de Duração (horas)',
                                                     show_values_on_bars=True)

            # 3. Histograma da Duração de Permanência
            if not df_estacionamento_tratado['Duracao'].dropna().empty:
                fig_hist, ax_hist = plt.subplots(figsize=(10, 6))
                sns.histplot(df_estacionamento_tratado['Duracao'], bins=20, kde=True, ax=ax_hist, color='purple')
                grafico_histograma_duracao = gerar_grafico(fig_hist, ax_hist,
                                                            title='Histograma da Duração de Permanência',
                                                            xlabel='Duração (horas)', ylabel='Frequência')

            # 4. Box Plot da Duração por Mês
            if not df_estacionamento_tratado['Duracao'].dropna().empty and 'Mes' in df_estacionamento_tratado.columns:
                fig_box_mes, ax_box_mes = plt.subplots(figsize=(12, 6))
                sns.boxplot(x='Mes', y='Duracao', data=df_estacionamento_tratado, ax=ax_box_mes, palette='Blues', hue='Mes', legend=False)
                ax_box_mes.set_xlabel('Mês')
                ax_box_mes.set_ylabel('Duração (horas)')
                grafico_boxplot_duracao_mes = gerar_grafico(fig_box_mes, ax_box_mes,
                                                            title='Box Plot da Duração por Mês',
                                                            xlabel='Mês', ylabel='Duração (horas)')

            # 5. Mapa de Calor da Duração Média por Hora de Entrada e Dia da Semana
            if not df_estacionamento_tratado.empty and 'Hora_Entrada' in df_estacionamento_tratado.columns and 'Dia_Semana' in df_estacionamento_tratado.columns:
                df_heatmap = df_estacionamento_tratado.pivot_table(index='Hora_Entrada', columns='Dia_Semana', values='Duracao', aggfunc='mean')
                df_heatmap.columns = df_heatmap.columns.map(dias_semana_portugues)
                existent_ordered_days = [day for day in dias_ordenados if day in df_heatmap.columns]
                df_heatmap = df_heatmap[existent_ordered_days]
                fig_heatmap, ax_heatmap = plt.subplots(figsize=(12, 8))
                sns.heatmap(df_heatmap, annot=True, fmt=".1f", cmap='YlGnBu', linewidths=.5, ax=ax_heatmap, cbar_kws={'label': 'Média de Duração (horas)'})
                ax_heatmap.set_title('Duração Média por Hora de Entrada e Dia da Semana')
                ax_heatmap.set_xlabel('Dia da Semana')
                ax_heatmap.set_ylabel('Hora de Entrada')
                grafico_heatmap_duracao = gerar_grafico(fig_heatmap, ax_heatmap, title='Duração Média por Hora de Entrada e Dia da Semana', xlabel='Dia da Semana', ylabel='Hora de Entrada')
            
            # 6. Agrupamento K-Means (Gráfico Machine Learning)
            if 'Duracao' in df_estacionamento_tratado.columns and 'Hora_Entrada' in df_estacionamento_tratado.columns:
                grafico_kmeans_estacionamento = gerar_grafico_kmeans_estacionamento(df_estacionamento_tratado)


        caminho_csv_estacionamento_tratado = os.path.join(script_dir, 'dataset', 'csv_estacionamento_tratado.csv')
        print(f"Salvando o arquivo CSV tratado em: {caminho_csv_estacionamento_tratado}")
        df_estacionamento_tratado.to_csv(caminho_csv_estacionamento_tratado, index=False, quoting=csv.QUOTE_MINIMAL)
    else:
        def get_empty_plot(title):
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.text(0.5, 0.5, "Sem dados para o gráfico", horizontalalignment='center', verticalalignment='center', fontsize=16, color='gray')
            ax.axis('off')
            return gerar_grafico(fig, ax, title=title)

        grafico_dia_semana = get_empty_plot('Média de Duração por Dia da Semana')
        grafico_media_geral = get_empty_plot('Média de Duração Geral')
        grafico_histograma_duracao = get_empty_plot('Histograma da Duração de Permanência')
        grafico_boxplot_duracao_mes = get_empty_plot('Box Plot da Duração por Mês')
        grafico_heatmap_duracao = get_empty_plot('Duração Média por Hora de Entrada e Dia da Semana')
        grafico_ocupacao_periodo = get_empty_plot('Ocupação Média por Período do Dia')
        grafico_kmeans_estacionamento = get_empty_plot('Padrões de Duração de Estacionamento (K-Means)')

    # --- Análise do pagamentos_placas.csv ---
    caminho_csv_pagamentos = os.path.join(script_dir, 'dataset', 'pagamentos_placas.csv')
    pagamentos_msg_erro = None
    df_pagamentos_tratado = pd.DataFrame()
    grafico_status_pagamento = None
    grafico_status_pagamento_por_mes = None
    total_registros_pagamentos = 0

    try:
        df_pagamentos = pd.read_csv(caminho_csv_pagamentos, delimiter=',')
        df_pagamentos_tratado = tratar_dados_pagamento(df_pagamentos.copy())
    except FileNotFoundError:
        pagamentos_msg_erro = f"Erro: Arquivo '{caminho_csv_pagamentos}' não encontrado."
    except Exception as e:
        pagamentos_msg_erro = f"Erro ao processar '{caminho_csv_pagamentos}': {e}"

    if pagamentos_msg_erro is None and not df_pagamentos_tratado.empty:
        total_registros_pagamentos = len(df_pagamentos_tratado)
        if 'Status_Pagamento' not in df_pagamentos_tratado.columns:
            pagamentos_msg_erro = "Erro: Coluna 'Status_Pagamento' ausente em 'pagamentos_placas.csv' após tratamento."
        else:
            grafico_status_pagamento = gerar_grafico_status_pagamento(df_pagamentos_tratado)
            grafico_status_pagamento_por_mes = gerar_grafico_status_pagamento_por_mes(df_pagamentos_tratado)

        caminho_csv_pagamentos_tratado = os.path.join(script_dir, 'dataset', 'pagamentos_placas_tratado.csv')
        print(f"Salvando o arquivo CSV tratado em: {caminho_csv_pagamentos_tratado}")
        df_pagamentos_tratado.to_csv(caminho_csv_pagamentos_tratado, index=False, quoting=csv.QUOTE_MINIMAL)
    else:
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.text(0.5, 0.5, "Sem dados para o gráfico de status de pagamento", horizontalalignment='center', verticalalignment='center', fontsize=12, color='gray')
        ax.axis('off')
        grafico_status_pagamento = gerar_grafico(fig, ax, title='Status de Pagamento dos Mensalistas')

        fig_inad_mes, ax_inad_mes = plt.subplots(figsize=(12, 7))
        ax_inad_mes.text(0.5, 0.5, "Sem dados para o gráfico de status de pagamento por mês", horizontalalignment='center', verticalalignment='center', fontsize=12, color='gray')
        ax_inad_mes.axis('off')
        grafico_status_pagamento_por_mes = gerar_grafico(fig_inad_mes, ax_inad_mes, title='Status de Pagamento por Mês')


    return {
        'total_registros_estacionamento': total_registros_estacionamento,
        'total_registros_pagamentos': total_registros_pagamentos,
        'estacionamento_msg_erro': estacionamento_msg_erro,
        'pagamentos_msg_erro': pagamentos_msg_erro
    }, grafico_dia_semana, grafico_media_geral, grafico_histograma_duracao, grafico_boxplot_duracao_mes, \
        grafico_heatmap_duracao, grafico_ocupacao_periodo, grafico_kmeans_estacionamento, grafico_status_pagamento, \
        grafico_status_pagamento_por_mes

@app.route('/')
def index():
    estatisticas, grafico_dia_semana, grafico_media_geral, grafico_histograma_duracao, grafico_boxplot_duracao_mes, \
    grafico_heatmap_duracao, grafico_ocupacao_periodo, grafico_kmeans_estacionamento, grafico_status_pagamento, \
    grafico_status_pagamento_por_mes = realizar_analise_completa()

    return render_template('index.html',
        estatisticas=estatisticas,
        grafico_dia_semana=grafico_dia_semana,
        grafico_media_geral=grafico_media_geral,
        grafico_histograma_duracao=grafico_histograma_duracao,
        grafico_boxplot_duracao_mes=grafico_boxplot_duracao_mes,
        grafico_heatmap_duracao=grafico_heatmap_duracao,
        grafico_ocupacao_periodo=grafico_ocupacao_periodo,
        grafico_kmeans_estacionamento=grafico_kmeans_estacionamento,
        grafico_status_pagamento=grafico_status_pagamento,
        grafico_status_pagamento_por_mes=grafico_status_pagamento_por_mes
    )

if __name__ == '__main__':
    app.run(debug=True)