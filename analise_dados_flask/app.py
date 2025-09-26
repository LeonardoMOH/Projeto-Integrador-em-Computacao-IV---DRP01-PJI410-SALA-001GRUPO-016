# Importação de bibliotecas utilizadas no projeto
import pandas as pd
import numpy as np
import io
import base64
from datetime import datetime
from flask import Flask, render_template
import csv
import os
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import seaborn as sns 

# Configuração da aplicação Flask
app = Flask(__name__)

# Função para formatar a duração em um valor numérico (horas)
def formatar_duracao_numerica(td):
    if pd.isna(td):
        return np.nan
    return td.total_seconds() / 3600

# Função para o tratamento de dados (ajustada para extrair o mês e dia da semana)
def tratar_dados_estacionamento(df):
    df['Entrada_Completa'] = pd.to_datetime(df['Data'] + ' ' + df['Entrada'], format='%d/%m/%Y %H:%M', errors='coerce')
    df['Saida_Completa'] = pd.to_datetime(df['Data'] + ' ' + df['Saida'], format='%d/%m/%Y %H:%M', errors='coerce')
    df.dropna(subset=['Entrada_Completa', 'Saida_Completa'], inplace=True)
    df.loc[df['Saida_Completa'] < df['Entrada_Completa'], 'Saida_Completa'] += pd.Timedelta(days=1)
    df['Duracao_temp'] = df['Saida_Completa'] - df['Entrada_Completa']
    df['Marca'], df['Modelo'] = df['Marca/Modelo'].str.split('/', expand=True)
    df['Duracao'] = df['Duracao_temp'].apply(formatar_duracao_numerica)
    df['Mes'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce').dt.month
    
    # Extrair hora de entrada para o mapa de calor
    df['Hora_Entrada'] = df['Entrada_Completa'].dt.hour
    
    df['Dia_Semana'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce').dt.day_name() 
    
    df.dropna(subset=['Duracao', 'Mes', 'Dia_Semana', 'Hora_Entrada'], inplace=True) 
    
    print("\n--- Debug Tratamento de Dados ---")
    print("df['Data'] head após to_datetime:\n", pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce').head())
    print("df['Dia_Semana'] head:\n", df['Dia_Semana'].head())
    print("Contagem de NaNs em Dia_Semana após dropna:", df['Dia_Semana'].isna().sum())
    print(f"df_tratado após tratamento ({len(df)} linhas):\n", df.head())
    print("df_tratado info:\n")
    df.info()
    print("-------------------------------\n")
    
    return df

# Recebe a figura e o eixo
def gerar_grafico(fig, ax, title="", xlabel="", ylabel="", show_values_on_bars=False):
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(axis='y', linestyle='--')

    if show_values_on_bars:
        # Verifica se 'ax.patches' existe e tem itens antes de iterar
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

# Função principal para realizar toda a análise de dados
def realizar_analise_completa():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    caminho_csv_original = os.path.join(script_dir, 'dataset', 'csv_estacionamento.csv')
    print(f"Tentando abrir o arquivo CSV original em: {caminho_csv_original}")

    try:
        df = pd.read_csv(caminho_csv_original, delimiter=';')
    except FileNotFoundError:
        # Retorna erro de arquivo não encontrado
        return {
            'total_registros': 0
        }, "Erro: Arquivo '{caminho_csv_original}' não encontrado.", None, None, None, None, None

    df_tratado = tratar_dados_estacionamento(df.copy())
    
    if df_tratado.empty or 'Duracao' not in df_tratado.columns or 'Mes' not in df_tratado.columns or 'Dia_Semana' not in df_tratado.columns or 'Hora_Entrada' not in df_tratado.columns:
        # Retorna erro de DataFrame vazio ou colunas essenciais ausentes
        return {
            'total_registros': len(df_tratado)
        }, "Erro: O DataFrame tratado está vazio ou faltam colunas essenciais ('Duracao', 'Mes', 'Dia_Semana', 'Hora_Entrada') após o tratamento de dados. Verifique o CSV.", None, None, None, None, None

    # Dicionários para tradução e ordenação
    dias_semana_portugues = {
        'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta',
        'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
    }
    dias_ordenados = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']

    # Gráficos de Análise de Dados

    # 1. Gráfico de Média de Duração por Dia da Semana (Gráfico Média (horas) X Dia da Semana)
    grafico_dia_semana = None 
    if not df_tratado['Duracao'].dropna().empty and 'Dia_Semana' in df_tratado.columns:
        media_por_dia = df_tratado.groupby('Dia_Semana')['Duracao'].mean()
        media_por_dia.index = media_por_dia.index.map(dias_semana_portugues)
        media_por_dia = media_por_dia.reindex(dias_ordenados)

        if not media_por_dia.dropna().empty:
            fig_dia_semana, ax_dia_semana = plt.subplots(figsize=(10, 6))
            media_por_dia.dropna().plot(kind='bar', color='skyblue', ax=ax_dia_semana)
            ax_dia_semana.set_xticklabels(media_por_dia.dropna().index, rotation=45, ha='right')
            grafico_dia_semana = gerar_grafico(fig_dia_semana, ax_dia_semana, 
                                               title='Média de Duração por Dia da Semana', xlabel='Dia da Semana', ylabel='Média de Duração (horas)',
                                               show_values_on_bars=True)
        else:
            fig_empty_dia, ax_empty_dia = plt.subplots(figsize=(10, 6))
            ax_empty_dia.text(0.5, 0.5, "Sem dados para o gráfico", horizontalalignment='center', verticalalignment='center', fontsize=16, color='gray')
            ax_empty_dia.axis('off')
            grafico_dia_semana = gerar_grafico(fig_empty_dia, ax_empty_dia, title='Média de Duração por Dia da Semana')
    else:
        fig_empty_dia, ax_empty_dia = plt.subplots(figsize=(10, 6))
        ax_empty_dia.text(0.5, 0.5, "Sem dados para o gráfico", horizontalalignment='center', verticalalignment='center', fontsize=16, color='gray')
        ax_empty_dia.axis('off')
        grafico_dia_semana = gerar_grafico(fig_empty_dia, ax_empty_dia, title='Média de Duração por Dia da Semana')


    # 2. Gráfico de Média de Duração Geral (Gráfico Média (horas) X Geral)
    grafico_media_geral = None 
    if not df_tratado['Duracao'].dropna().empty:
        media_geral_valor = df_tratado['Duracao'].mean()
        
        fig_media_geral, ax_media_geral = plt.subplots(figsize=(4, 6))
        ax_media_geral.bar(x=['Média Geral'], height=[media_geral_valor], color='lightgreen')
        ax_media_geral.set_ylim(0, media_geral_valor * 1.2 if media_geral_valor > 0 else 1)
        grafico_media_geral = gerar_grafico(fig_media_geral, ax_media_geral, 
                                            title='Média de Duração Geral', xlabel='', ylabel='Média de Duração (horas)',
                                            show_values_on_bars=True)
    else:
        fig_empty_geral, ax_empty_geral = plt.subplots(figsize=(4, 6))
        ax_empty_geral.text(0.5, 0.5, "Sem dados para o gráfico", horizontalalignment='center', verticalalignment='center', fontsize=16, color='gray')
        ax_empty_geral.axis('off')
        grafico_media_geral = gerar_grafico(fig_empty_geral, ax_empty_geral, title='Média de Duração Geral')

    # 3. Histograma da Duração de Permanência
    grafico_histograma_duracao = None 
    if not df_tratado['Duracao'].dropna().empty:
        fig_hist, ax_hist = plt.subplots(figsize=(10, 6))
        sns.histplot(df_tratado['Duracao'], bins=20, kde=True, ax=ax_hist, color='purple')
        grafico_histograma_duracao = gerar_grafico(fig_hist, ax_hist, 
                                                   title='Histograma da Duração de Permanência', 
                                                   xlabel='Duração (horas)', ylabel='Frequência')
    else:
        fig_empty_hist, ax_empty_hist = plt.subplots(figsize=(10, 6))
        ax_empty_hist.text(0.5, 0.5, "Sem dados para o Histograma", horizontalalignment='center', verticalalignment='center', fontsize=16, color='gray')
        ax_empty_hist.axis('off')
        grafico_histograma_duracao = gerar_grafico(fig_empty_hist, ax_empty_hist, title='Histograma da Duração de Permanência')


    # 4. Box Plot da Duração por Mês
    grafico_boxplot_duracao_mes = None 
    if not df_tratado['Duracao'].dropna().empty and 'Mes' in df_tratado.columns:
        fig_box_mes, ax_box_mes = plt.subplots(figsize=(12, 6))
        sns.boxplot(x='Mes', y='Duracao', data=df_tratado, ax=ax_box_mes, palette='Blues', hue='Mes', legend=False)
        ax_box_mes.set_xlabel('Mês')
        ax_box_mes.set_ylabel('Duração (horas)')
        grafico_boxplot_duracao_mes = gerar_grafico(fig_box_mes, ax_box_mes, 
                                                   title='Box Plot da Duração por Mês', 
                                                   xlabel='Mês', ylabel='Duração (horas)')
    else:
        fig_empty_box_mes, ax_empty_box_mes = plt.subplots(figsize=(12, 6))
        ax_empty_box_mes.text(0.5, 0.5, "Sem dados para o Box Plot por Mês", horizontalalignment='center', verticalalignment='center', fontsize=16, color='gray')
        ax_empty_box_mes.axis('off')
        grafico_boxplot_duracao_mes = gerar_grafico(fig_empty_box_mes, ax_empty_box_mes, title='Box Plot da Duração por Mês')

    # 5. Mapa de Calor da Duração Média por Hora do Dia e Dia da Semana
    grafico_heatmap_duracao = None 
    if not df_tratado.empty and 'Hora_Entrada' in df_tratado.columns and 'Dia_Semana' in df_tratado.columns:
        df_heatmap = df_tratado.pivot_table(index='Hora_Entrada', columns='Dia_Semana', values='Duracao', aggfunc='mean')
        
        df_heatmap.columns = df_heatmap.columns.map(dias_semana_portugues)
        
        existent_ordered_days = [day for day in dias_ordenados if day in df_heatmap.columns]
        df_heatmap = df_heatmap[existent_ordered_days]
    
        fig_heatmap, ax_heatmap = plt.subplots(figsize=(12, 8))
        sns.heatmap(df_heatmap, annot=True, fmt=".1f", cmap='YlGnBu', linewidths=.5, ax=ax_heatmap, cbar_kws={'label': 'Média de Duração (horas)'})
        ax_heatmap.set_title('Duração Média por Hora de Entrada e Dia da Semana')
        ax_heatmap.set_xlabel('Dia da Semana')
        ax_heatmap.set_ylabel('Hora de Entrada')
        grafico_heatmap_duracao = gerar_grafico(fig_heatmap, ax_heatmap, title='Duração Média por Hora de Entrada e Dia da Semana', xlabel='Dia da Semana', ylabel='Hora de Entrada')
    else:
        fig_empty_heatmap, ax_empty_heatmap = plt.subplots(figsize=(12, 8))
        ax_empty_heatmap.text(0.5, 0.5, "Sem dados para o Mapa de Calor", horizontalalignment='center', verticalalignment='center', fontsize=16, color='gray')
        ax_empty_heatmap.axis('off')
        grafico_heatmap_duracao = gerar_grafico(fig_empty_heatmap, ax_empty_heatmap, title='Duração Média por Hora de Entrada e Dia da Semana')

    caminho_csv_tratado = os.path.join(script_dir, 'dataset', 'csv_estacionamento_tratado.csv')
    print(f"Salvando o arquivo CSV tratado em: {caminho_csv_tratado}")
    df_tratado.to_csv(caminho_csv_tratado, index=False, quoting=csv.QUOTE_MINIMAL)

    return {
        'total_registros': len(df_tratado)
    }, grafico_dia_semana, grafico_media_geral, grafico_histograma_duracao, grafico_boxplot_duracao_mes, grafico_heatmap_duracao

# Rota principal da aplicação Flask
@app.route('/')
def index():
    estatisticas, grafico_dia_semana, grafico_media_geral, grafico_histograma_duracao, grafico_boxplot_duracao_mes, grafico_heatmap_duracao = realizar_analise_completa()
    
    # Se houver erro de arquivo, exibe a mensagem de erro
    if isinstance(estatisticas, str) and estatisticas.startswith("Erro:"): 
        return render_template('erro.html', mensagem_erro=estatisticas)
    
       
    return render_template('index.html', 
        estatisticas=estatisticas, 
        grafico_dia_semana=grafico_dia_semana,
        grafico_media_geral=grafico_media_geral,
        grafico_histograma_duracao=grafico_histograma_duracao,
        grafico_boxplot_duracao_mes=grafico_boxplot_duracao_mes,
        grafico_heatmap_duracao=grafico_heatmap_duracao
    )

# Execução da aplicação Flask
if __name__ == '__main__':
    app.run(debug=True)