import streamlit as st
import pandas as pd
import numpy as np
import datetime
import time
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys
from pathlib import Path
from st_gsheets_connection import GSheetsConnection

# Configuração da página - DEVE ser o primeiro comando Streamlit
st.set_page_config(
    page_title="Dashboard de Avaliações - CEOP",
    page_icon="📊",
    layout="wide"
)

# Função para ler dados do Google Sheets
@st.cache_data(ttl=30)  # Cache por 30 segundos
def ler_dados_google_sheets(nome_conexao):
    try:
        # Conexão com o Google Sheets
        conn = st.connection(nome_conexao, type=GSheetsConnection)
        
        # Leitura da planilha
        df_original = conn.read()
        
        # Verificar se há dados na planilha
        if df_original.empty:
            st.error("A planilha não contém dados")
            return pd.DataFrame(columns=['recepcao', 'timestamp', 'atendimento', 'recomendacao', 'comentario'])
        
        # Mapear corretamente as colunas conforme a estrutura real da planilha
        # A: Recepção, B: Timestamp, C: E-mail, D: Atendimento, E: Recomendação, F: Comentário
        col_recepcao = 0    # Coluna A
        col_timestamp = 1   # Coluna B
        col_email = 2       # Coluna C
        col_atendimento = 3 # Coluna D
        col_recomendacao = 4 # Coluna E
        col_comentario = 5   # Coluna F
        
        # Criar novo DataFrame apenas com as colunas necessárias
        df = pd.DataFrame()
        
        if len(df_original.columns) > col_recepcao:
            df['recepcao'] = df_original.iloc[:, col_recepcao].fillna('Não informado')
        else:
            df['recepcao'] = 'Não informado'
        
        if len(df_original.columns) > col_timestamp:
            df['timestamp'] = df_original.iloc[:, col_timestamp]
        else:
            df['timestamp'] = pd.NaT
        
        # Ignoramos o email, mas podemos incluí-lo se necessário
        
        if len(df_original.columns) > col_atendimento:
            df['atendimento'] = df_original.iloc[:, col_atendimento]
        else:
            df['atendimento'] = np.nan
        
        if len(df_original.columns) > col_recomendacao:
            df['recomendacao'] = df_original.iloc[:, col_recomendacao]
        else:
            df['recomendacao'] = np.nan
        
        if len(df_original.columns) > col_comentario:
            df['comentario'] = df_original.iloc[:, col_comentario]
        else:
            df['comentario'] = ""
        
        # Converter timestamp para datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        # Converter notas para inteiro
        df['atendimento'] = pd.to_numeric(df['atendimento'], errors='coerce')
        df['recomendacao'] = pd.to_numeric(df['recomendacao'], errors='coerce')
        
        # Adicionar colunas de ano e mês para facilitar filtragem
        df['ano'] = df['timestamp'].dt.year
        df['mes'] = df['timestamp'].dt.month
        df['mes_nome'] = df['timestamp'].dt.strftime('%B')  # Nome do mês
        df['ano_mes'] = df['timestamp'].dt.strftime('%Y-%m')  # Formato YYYY-MM
        
        return df
        
    except Exception as e:
        st.error(f"Erro ao ler dados do Google Sheets: {e}")
        # Retornar DataFrame vazio em caso de erro
        return pd.DataFrame(columns=['recepcao', 'timestamp', 'atendimento', 'recomendacao', 'comentario'])


# Função para filtrar dados por período
def filtrar_por_periodo(df, periodo=None):
    """
    Filtra o DataFrame de acordo com o período selecionado.
    
    Args:
        df: DataFrame original
        periodo: Período para filtrar (formato 'YYYY-MM' ou None para todos)
    
    Returns:
        DataFrame filtrado
    """
    if not periodo or periodo == "Todos":
        return df
    
    # Se o período for "Atual", filtra para o mês atual
    if periodo == "Atual":
        mes_atual = datetime.datetime.now().month
        ano_atual = datetime.datetime.now().year
        return df[(df['mes'] == mes_atual) & (df['ano'] == ano_atual)]
    
    # Caso contrário, filtra pelo período específico (formato YYYY-MM)
    return df[df['ano_mes'] == periodo]

# Função para obter lista de períodos disponíveis
def obter_periodos_disponiveis(df):
    """
    Retorna a lista de períodos disponíveis no DataFrame.
    
    Args:
        df: DataFrame com dados
        
    Returns:
        Lista de períodos no formato YYYY-MM
    """
    if df.empty or 'ano_mes' not in df.columns:
        return ["Todos"]
    
    # Obter períodos únicos
    periodos = df['ano_mes'].unique().tolist()
    periodos.sort(reverse=True)  # Mais recentes primeiro
    
    # Transformar para formato mais amigável (Mês/Ano)
    periodos_formatados = []
    meses_pt = {
        '01': 'Janeiro', '02': 'Fevereiro', '03': 'Março', 
        '04': 'Abril', '05': 'Maio', '06': 'Junho',
        '07': 'Julho', '08': 'Agosto', '09': 'Setembro',
        '10': 'Outubro', '11': 'Novembro', '12': 'Dezembro'
    }
    
    for periodo in periodos:
        if pd.notna(periodo):
            ano, mes = periodo.split('-')
            nome_mes = meses_pt.get(mes, mes)
            periodos_formatados.append(f"{nome_mes}/{ano}")
    
    # Adicionar opções especiais
    mes_atual = datetime.datetime.now().month
    ano_atual = datetime.datetime.now().year
    mes_atual_str = f"{meses_pt[f'{mes_atual:02d}']}/{ano_atual}"
    
    # Garantir que não haja duplicação
    if mes_atual_str not in periodos_formatados:
        periodos_formatados.insert(0, mes_atual_str)
    
    # Adicionar opções "Atual" e "Todos" no início
    periodos_formatados = ["Atual", "Todos"] + periodos_formatados
    
    return periodos_formatados

# Converte período formatado (Mês/Ano) para formato YYYY-MM
def converter_periodo_para_formato(periodo):
    if periodo in ["Todos", "Atual"]:
        return periodo
    
    # Converter de "Mês/Ano" para "YYYY-MM"
    meses_pt_inverso = {
        'Janeiro': '01', 'Fevereiro': '02', 'Março': '03', 
        'Abril': '04', 'Maio': '05', 'Junho': '06',
        'Julho': '07', 'Agosto': '08', 'Setembro': '09',
        'Outubro': '10', 'Novembro': '11', 'Dezembro': '12'
    }
    
    try:
        mes, ano = periodo.split('/')
        mes_num = meses_pt_inverso.get(mes, mes)
        return f"{ano}-{mes_num}"
    except:
        return None

# Funções para cálculos
def calcular_nps(notas):
    # Remover valores NaN, se houver
    notas = [n for n in notas if not pd.isna(n)]
    
    if len(notas) == 0:
        return 0
    
    promotores = sum(nota >= 9 for nota in notas)
    detratores = sum(nota <= 6 for nota in notas)
    
    return ((promotores / len(notas)) - (detratores / len(notas))) * 100

def calcular_percentual_promotores(notas):
    # Converter para lista e filtrar valores NaN
    notas = [n for n in notas if not pd.isna(n)]
    
    if len(notas) == 0:
        return 0
    return (sum(nota >= 9 for nota in notas) / len(notas)) * 100

def calcular_percentual_neutros(notas):
    # Converter para lista e filtrar valores NaN
    notas = [n for n in notas if not pd.isna(n)]
    
    if len(notas) == 0:
        return 0
    return (sum(7 <= nota <= 8 for nota in notas) / len(notas)) * 100

def calcular_percentual_detratores(notas):
    # Converter para lista e filtrar valores NaN
    notas = [n for n in notas if not pd.isna(n)]
    
    if len(notas) == 0:
        return 0
    return (sum(nota <= 6 for nota in notas) / len(notas)) * 100

def calcular_distribuicao_notas(df):
    distribuicao = []
    
    for i in range(11):  # 0 a 10
        atendimento_count = len(df[df['atendimento'] == i])
        recomendacao_count = len(df[df['recomendacao'] == i])
        
        distribuicao.append({
            'nota': i,
            'atendimento': atendimento_count,
            'recomendacao': recomendacao_count
        })
    
    return pd.DataFrame(distribuicao)

def calcular_tendencia_diaria(df):
    if len(df) == 0:
        return pd.DataFrame()
    
    # Criar uma cópia do dataframe para não modificar o original
    df_temp = df.copy()
    
    # Verificar se há valores de timestamp válidos
    if df_temp['timestamp'].isna().all():
        return pd.DataFrame()
    
    # Extrair apenas a hora do timestamp
    df_temp['periodo'] = df_temp['timestamp'].dt.strftime('%H:00')
    
    # Agrupar por hora
    result = df_temp.groupby('periodo').agg({
        'atendimento': 'mean',
        'recomendacao': 'mean'
    }).reset_index()
    
    # Ordenar por hora
    result['hora_num'] = result['periodo'].str.split(':').str[0].astype(int)
    result = result.sort_values('hora_num').drop('hora_num', axis=1)
    
    return result

def categoria_de_nps(nps):
    if nps >= 75:
        return "Excelente", "#22c55e"
    if nps >= 50:
        return "Bom", "#3b82f6"
    if nps >= 0:
        return "Regular", "#eab308"
    return "Crítico", "#ef4444"

# Interface principal
def main():
    # Filtro de filial (antes de carregar os dados)
    st.sidebar.header("Filial")
    filiais = {
        "CEOP Belém": "gsheets_belem",
        "CEOP Castanhal": "gsheets_castanhal",
        "CEOP Barcarena": "gsheets_barcarena"
    }
    filial_selecionada = st.sidebar.selectbox(
        "Selecione a filial:",
        options=list(filiais.keys()),
        index=0  # Belém por padrão
    )

    # Cabeçalho
    try:
        # Caminho para o logo
        logo_path = "../logo Ceop.jpg"  # Caminho relativo padrão
        if getattr(sys, 'frozen', False):
            # Quando executado como executável
            logo_path = os.path.join(os.path.dirname(sys.executable), "logo Ceop.jpg")
        
        header_col1, header_col2 = st.columns([7, 3])
        
        with header_col1:
            st.title(f"Dashboard de Avaliações - {filial_selecionada}")
            st.markdown("Acompanhamento de avaliações de pacientes")
        
        with header_col2:
            # Tentar exibir o logo, se disponível
            try:
                st.image(logo_path, width=150)
            except:
                st.markdown("##")  # Espaço em branco caso não consiga carregar a imagem
                
            if st.button("🔄 Atualizar agora"):
                st.cache_data.clear()
                st.rerun()
    except Exception as e:
        # Fallback para cabeçalho simples em caso de erro
        st.title(f"Dashboard de Avaliações - {filial_selecionada}")
        st.markdown("Acompanhamento de avaliações de pacientes")
        if st.button("🔄 Atualizar agora"):
            st.cache_data.clear()
            st.rerun()

    # Carregar dados da filial selecionada
    df = ler_dados_google_sheets(filiais[filial_selecionada])
    
    if df.empty:
        st.warning("Nenhum dado encontrado ou erro na conexão com Google Sheets.")
        st.stop()
    
    # Filtro de período
    st.sidebar.header("Filtros")
    
    # Filtro de recepção
    recepcoes_disponiveis = ['Todas'] + sorted(df['recepcao'].dropna().unique().tolist())
    recepcao_selecionada = st.sidebar.selectbox(
        "Recepção:",
        options=recepcoes_disponiveis,
        index=0  # 'Todas' por padrão
    )
    
    # Filtro de período
    periodos_disponiveis = obter_periodos_disponiveis(df)
    periodo_selecionado = st.sidebar.selectbox(
        "Período de análise:",
        options=periodos_disponiveis,
        index=0  # "Atual" por padrão
    )
    
    # Converter para formato interno e filtrar dados
    periodo_formatado = converter_periodo_para_formato(periodo_selecionado)
    df_filtrado = filtrar_por_periodo(df, periodo_formatado)
    
    # Aplicar filtro de recepção
    if recepcao_selecionada != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['recepcao'] == recepcao_selecionada]
    
    # Exibir informação do período
    if periodo_selecionado == "Todos":
        st.sidebar.info("Visualizando dados de todo o período")
    elif periodo_selecionado == "Atual":
        mes_atual = datetime.datetime.now().strftime('%B/%Y')
        st.sidebar.info(f"Visualizando dados do mês atual ({mes_atual})")
    else:
        st.sidebar.info(f"Visualizando dados de {periodo_selecionado}")
    
    # Mostrar contagem de avaliações no período selecionado
    st.sidebar.metric("Avaliações no período", len(df_filtrado))
    
    # Métricas principais
    media_atendimento = df_filtrado['atendimento'].mean()
    media_recomendacao = df_filtrado['recomendacao'].mean()
    
    # Verificar se as médias são NaN e substituir por 0 se forem
    if pd.isna(media_atendimento):
        media_atendimento = 0
    if pd.isna(media_recomendacao):
        media_recomendacao = 0
        
    nps = calcular_nps(df_filtrado['recomendacao'].dropna().tolist())
    categoria, cor_nps = categoria_de_nps(nps)
    
    # Cards de métricas principais
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    
    with metric_col1:
        st.markdown(f"### Net Promoter Score")
        st.markdown(f"<span style='color:{cor_nps}; font-size:12px; padding:4px 8px; border-radius:10px; background-color:{cor_nps}20;'>{categoria}</span>", unsafe_allow_html=True)
        st.markdown(f"<span style='color:{cor_nps}; font-size:42px; font-weight:bold;'>{int(round(nps))}</span> <span style='color:#6B7280; font-size:14px;'>pontos</span>", unsafe_allow_html=True)
        
        # Gráfico de pizza NPS
        fig_nps = go.Figure(data=[go.Pie(
            labels=['Promotores', 'Neutros', 'Detratores'],
            values=[
                calcular_percentual_promotores(df_filtrado['recomendacao'].dropna()),
                calcular_percentual_neutros(df_filtrado['recomendacao'].dropna()),
                calcular_percentual_detratores(df_filtrado['recomendacao'].dropna())
            ],
            hole=.4,
            marker_colors=['#22c55e', '#eab308', '#ef4444']
        )])
        fig_nps.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=180)
        st.plotly_chart(fig_nps, use_container_width=True)
        
        # Legenda do gráfico de pizza
        legend_col_p, legend_col_n, legend_col_d = st.columns(3)
        with legend_col_p:
            st.markdown(f"<div style='text-align:center;'><span style='color:#22c55e; font-weight:500;'>Promotores</span><br>{calcular_percentual_promotores(df_filtrado['recomendacao'].dropna()):.1f}%</div>", unsafe_allow_html=True)
        with legend_col_n:
            st.markdown(f"<div style='text-align:center;'><span style='color:#eab308; font-weight:500;'>Neutros</span><br>{calcular_percentual_neutros(df_filtrado['recomendacao'].dropna()):.1f}%</div>", unsafe_allow_html=True)
        with legend_col_d:
            st.markdown(f"<div style='text-align:center;'><span style='color:#ef4444; font-weight:500;'>Detratores</span><br>{calcular_percentual_detratores(df_filtrado['recomendacao'].dropna()):.1f}%</div>", unsafe_allow_html=True)
    
    with metric_col2:
        st.markdown("### Média de Atendimento")
        st.markdown(f"<span style='color:#3b82f6; font-size:42px; font-weight:bold;'>{media_atendimento:.1f}</span> <span style='color:#6B7280; font-size:14px;'>/ 10</span>", unsafe_allow_html=True)
        
        # Barra de progresso
        st.progress(float(media_atendimento/10))
        st.markdown(f"Baseado em {len(df_filtrado['atendimento'].dropna())} avaliações")
    
    with metric_col3:
        st.markdown("### Taxa de Recomendação")
        st.markdown(f"<span style='color:#22c55e; font-size:42px; font-weight:bold;'>{media_recomendacao:.1f}</span> <span style='color:#6B7280; font-size:14px;'>/ 10</span>", unsafe_allow_html=True)
        
        # Barra de progresso
        st.progress(float(media_recomendacao/10))
        
        if media_recomendacao > 8:
            st.markdown("A maioria dos pacientes recomendaria o CEOP")
        else:
            st.markdown("Há oportunidades para melhorias")
    
    # Gráficos detalhados
    detail_col1, detail_col2 = st.columns(2)
    
    with detail_col1:
        st.markdown("### Distribuição de Notas")
        distribuicao_df = calcular_distribuicao_notas(df_filtrado)
        
        # Melt para facilitar o uso com plotly
        distribuicao_melted = pd.melt(
            distribuicao_df, 
            id_vars=['nota'], 
            value_vars=['atendimento', 'recomendacao'],
            var_name='tipo', 
            value_name='contagem'
        )
        
        # Gráfico de barras para distribuição
        fig_dist = px.bar(
            distribuicao_melted, 
            x='nota', 
            y='contagem', 
            color='tipo',
            barmode='group',
            color_discrete_map={'atendimento': '#3b82f6', 'recomendacao': '#22c55e'},
            labels={'contagem': 'Quantidade', 'nota': 'Nota', 'tipo': 'Tipo'}
        )
        fig_dist.update_layout(legend_title_text='')
        st.plotly_chart(fig_dist, use_container_width=True)
    
    with detail_col2:
        st.markdown("### Evolução por Período")
        
        # Agrupar por mês para mostrar evolução
        if len(df) > 0 and not df['timestamp'].isna().all():
            # Criar cópia para não modificar o original
            df_temp = df.copy()
            
            # Agrupar por ano-mês
            df_evolucao = df_temp.groupby('ano_mes').agg({
                'atendimento': 'mean',
                'recomendacao': 'mean'
            }).reset_index()
            
            # Ordenar por ano-mês
            df_evolucao = df_evolucao.sort_values('ano_mes')
            
            # Formatar período
            meses_pt = {
                '01': 'Jan', '02': 'Fev', '03': 'Mar', 
                '04': 'Abr', '05': 'Mai', '06': 'Jun',
                '07': 'Jul', '08': 'Ago', '09': 'Set',
                '10': 'Out', '11': 'Nov', '12': 'Dez'
            }
            
            df_evolucao['periodo_formatado'] = df_evolucao['ano_mes'].apply(
                lambda x: f"{meses_pt.get(x.split('-')[1], x.split('-')[1])}/{x.split('-')[0][2:4]}" if pd.notna(x) else ""
            )
            
            # Gráfico de linha para evolução
            fig_evol = go.Figure()
            
            fig_evol.add_trace(go.Scatter(
                x=df_evolucao['periodo_formatado'],
                y=df_evolucao['atendimento'],
                name='Atendimento',
                line=dict(color='#3b82f6', width=3),
                mode='lines+markers'
            ))
            
            fig_evol.add_trace(go.Scatter(
                x=df_evolucao['periodo_formatado'],
                y=df_evolucao['recomendacao'],
                name='Recomendação',
                line=dict(color='#22c55e', width=3),
                mode='lines+markers'
            ))
            
            fig_evol.update_layout(
                yaxis=dict(range=[0, 10]),
                xaxis_title="Período",
                yaxis_title="Média"
            )
            
            st.plotly_chart(fig_evol, use_container_width=True)
        else:
            st.info("Não há dados suficientes para exibir a evolução por período")
    
    # Tendência de avaliações (horário/dia)
    if periodo_selecionado == "Atual":
        st.markdown("### Tendência de Avaliações")
        tendencia_df = calcular_tendencia_diaria(df_filtrado)
        
        if not tendencia_df.empty:
            # Gráfico de linha para tendência
            fig_tend = go.Figure()
            
            fig_tend.add_trace(go.Scatter(
                x=tendencia_df['periodo'],
                y=tendencia_df['atendimento'],
                name='Atendimento',
                line=dict(color='#3b82f6', width=3),
                mode='lines+markers'
            ))
            
            fig_tend.add_trace(go.Scatter(
                x=tendencia_df['periodo'],
                y=tendencia_df['recomendacao'],
                name='Recomendação',
                line=dict(color='#22c55e', width=3),
                mode='lines+markers'
            ))
            
            fig_tend.update_layout(
                yaxis=dict(range=[0, 10]),
                xaxis_title="Período do dia",
                yaxis_title="Média"
            )
            
            st.plotly_chart(fig_tend, use_container_width=True)
        else:
            st.info("Não há dados suficientes para exibir a tendência por hora do dia")
    
    # Tabela de últimas avaliações
    st.markdown("### Últimas Avaliações")
    
    # Criar cópia do DataFrame e formatar
    df_display = df_filtrado.copy()
    df_display['timestamp'] = df_display['timestamp'].dt.strftime('%d/%m/%Y %H:%M')
    df_display.rename(columns={
        'timestamp': 'Data/Hora',
        'atendimento': 'Atendimento',
        'recomendacao': 'Recomendação',
        'comentario': 'Comentário'
    }, inplace=True)
    
    # Remover colunas de filtro
    df_display = df_display.drop(columns=['ano', 'mes', 'mes_nome', 'ano_mes'], errors='ignore')
    
    # Aplicar estilo à tabela
    def color_notas(val):
        if pd.isna(val) or not isinstance(val, (int, float)):
            return ''
        
        val = float(val)
        if val >= 9:
            return 'color: #22c55e; font-weight: bold'  # Verde mais claro
        elif val >= 7:
            return 'color: #3b82f6; font-weight: bold'  # Azul mais claro
        elif val >= 5:
            return 'color: #eab308; font-weight: bold'  # Amarelo mais claro
        else:
            return 'color: #ef4444; font-weight: bold'  # Vermelho mais claro
    
    # Exibir tabela estilizada
    st.dataframe(
        df_display.sort_values('Data/Hora', ascending=False).fillna("-").style.applymap(
            color_notas, subset=['Atendimento', 'Recomendação']
        ),
        hide_index=True,
        use_container_width=True
    )
    
    # Configurações
    with st.expander("⚙️ Configurações"):
        intervalo_atualizacao = st.selectbox(
            "Intervalo de atualização:",
            options=[10, 30, 60, 300],
            format_func=lambda x: f"{x} segundos" if x < 60 else f"{x // 60} minuto{'s' if x >= 120 else ''}",
            index=1  # Padrão é 30 segundos
        )
        
        atualizar_automaticamente = st.checkbox("Atualizar dados automaticamente", value=True)
        
        st.info("O dashboard será atualizado automaticamente com este intervalo se a opção estiver marcada.")
    
    # Para prevenir loops infinitos quando executado como aplicativo
    if getattr(sys, 'frozen', False):
        # Se estiver rodando como aplicativo compilado, use uma abordagem mais segura
        st.write(f"Próxima atualização automática em {intervalo_atualizacao} segundos")
        time.sleep(intervalo_atualizacao)
        st.experimental_rerun()
    else:
        # No ambiente de desenvolvimento, podemos usar o contador original
        if atualizar_automaticamente:
            contador = st.empty()
            for i in range(intervalo_atualizacao, 0, -1):
                contador.markdown(f"Próxima atualização em: **{i}s**")
                time.sleep(1)
            st.rerun()
        else:
            st.info("Atualização automática desativada. Clique em 'Atualizar agora' para atualizar os dados.")

if __name__ == "__main__":
    main()
