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
import json
from typing import Optional, Dict, Any
import base64
import requests

# Verifica se as bibliotecas opcionais estão disponíveis
try:
    from google.oauth2.service_account import Credentials
    from google.oauth2 import service_account
    import gspread
    from gspread_pandas import Spread
    from gspread_dataframe import get_as_dataframe
    GOOGLE_LIBRARIES_AVAILABLE = True
except ImportError:
    GOOGLE_LIBRARIES_AVAILABLE = False

try:
    from streamlit_gsheets import GSheetsConnection
    STREAMLIT_GSHEETS_AVAILABLE = True
except ImportError:
    STREAMLIT_GSHEETS_AVAILABLE = False

# Configuração da página - DEVE ser o primeiro comando Streamlit
st.set_page_config(
    page_title="Dashboard de Avaliações - CEOP",
    page_icon="📊",
    layout="wide"
)

# Criar pasta para armazenar arquivos temporários e de configuração
def setup_app_directories():
    """Configura os diretórios necessários para a aplicação"""
    # Determina o diretório base
    if getattr(sys, 'frozen', False):
        # Se for executável
        base_dir = os.path.dirname(sys.executable)
    else:
        # Se for script
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Cria o diretório de configuração se não existir
    config_dir = os.path.join(base_dir, "config")
    os.makedirs(config_dir, exist_ok=True)
    
    # Cria o diretório de dados se não existir
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    return {
        "base_dir": base_dir,
        "config_dir": config_dir,
        "data_dir": data_dir
    }

# Configuração de caminho quando executado como executável
def resolve_resource_path(relative_path):
    """Resolve o caminho de recursos quando executado como executável"""
    if getattr(sys, 'frozen', False):
        # Se estiver rodando como executável (compilado)
        base_path = getattr(sys, '_MEIPASS', Path(sys.executable).parent)
        return os.path.join(base_path, relative_path)
    else:
        # Rodando normalmente como script Python
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

# Função para carregar a configuração das planilhas
def carregar_configuracao_planilhas():
    """Carrega as configurações das planilhas do arquivo de configuração"""
    dirs = setup_app_directories()
    config_file = os.path.join(dirs["config_dir"], "sheets_config.json")
    
    # Configuração padrão
    config_padrao = {
        "filiais": {
            "CEOP Belém": {
                "sheet_id": "",
                "sheet_name": "",
                "connection_name": "gsheets_belem"
            },
            "CEOP Castanhal": {
                "sheet_id": "",
                "sheet_name": "",
                "connection_name": "gsheets_castanhal"
            },
            "CEOP Barcarena": {
                "sheet_id": "",
                "sheet_name": "",
                "connection_name": "gsheets_barcarena"
            }
        },
        "modo_conexao": "file" # Opções: streamlit, gspread, file
    }
    
    # Verifica se o arquivo existe
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        except Exception as e:
            st.sidebar.error(f"Erro ao carregar configuração: {e}")
            # Usa a configuração padrão
            return config_padrao
    else:
        # Cria o arquivo de configuração padrão
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_padrao, f, indent=4, ensure_ascii=False)
            return config_padrao
        except Exception as e:
            st.sidebar.error(f"Erro ao criar arquivo de configuração: {e}")
            return config_padrao

# Função para carregar configuração do Google Service Account
def carregar_service_account():
    """Carrega as credenciais do Google Service Account"""
    dirs = setup_app_directories()
    creds_file = os.path.join(dirs["config_dir"], "credentials.json")
    
    if os.path.exists(creds_file):
        try:
            with open(creds_file, 'r') as f:
                info = json.load(f)
            return info
        except Exception as e:
            st.sidebar.error(f"Erro ao carregar credenciais: {e}")
            return None
    else:
        return None

# Função para ler dados do Google Sheets usando diferentes métodos
@st.cache_data(ttl=30)  # Cache por 30 segundos
def ler_dados_google_sheets(filial_config: Dict[str, Any]) -> pd.DataFrame:
    """
    Lê dados do Google Sheets usando diferentes métodos.
    
    Args:
        filial_config: Configurações da filial selecionada
    
    Returns:
        DataFrame com os dados da planilha
    """
    config = carregar_configuracao_planilhas()
    modo_conexao = config.get("modo_conexao", "file")
    
    # Tenta ler usando o método configurado
    if modo_conexao == "streamlit" and STREAMLIT_GSHEETS_AVAILABLE:
        return ler_com_streamlit_gsheets(filial_config.get("connection_name", ""))
    elif modo_conexao == "gspread" and GOOGLE_LIBRARIES_AVAILABLE:
        return ler_com_gspread(filial_config.get("sheet_id", ""), filial_config.get("sheet_name", ""))
    elif modo_conexao == "file":
        return ler_de_arquivo_local(filial_config.get("connection_name", ""))
    else:
        st.error("Método de conexão não disponível ou não configurado corretamente")
        return pd.DataFrame(columns=['recepcao', 'timestamp', 'atendimento', 'recomendacao', 'comentario'])

# Método 1: Usando streamlit_gsheets
def ler_com_streamlit_gsheets(nome_conexao):
    try:
        # Conexão com o Google Sheets
        conn = st.connection(nome_conexao, type=GSheetsConnection)
        
        # Leitura da planilha
        df_original = conn.read()
        
        return processar_dataframe(df_original)
        
    except Exception as e:
        st.error(f"Erro ao ler dados do Google Sheets (Streamlit): {e}")
        return pd.DataFrame(columns=['recepcao', 'timestamp', 'atendimento', 'recomendacao', 'comentario'])

# Método 2: Usando gspread diretamente
def ler_com_gspread(sheet_id, sheet_name):
    try:
        # Verifica se as credenciais foram carregadas
        info_credencial = carregar_service_account()
        if not info_credencial:
            st.error("Credenciais do Google não encontradas")
            return pd.DataFrame(columns=['recepcao', 'timestamp', 'atendimento', 'recomendacao', 'comentario'])
        
        # Configura as credenciais
        credentials = service_account.Credentials.from_service_account_info(
            info_credencial,
            scopes=['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        )
        client = gspread.authorize(credentials)
        
        # Abre a planilha
        sh = client.open_by_key(sheet_id)
        worksheet = sh.worksheet(sheet_name) if sheet_name else sh.sheet1
        
        # Obter todos os valores
        df_original = pd.DataFrame(worksheet.get_all_records())
        
        return processar_dataframe(df_original)
    
    except Exception as e:
        st.error(f"Erro ao ler dados do Google Sheets (gspread): {e}")
        return pd.DataFrame(columns=['recepcao', 'timestamp', 'atendimento', 'recomendacao', 'comentario'])

# Método 3: Leitura de arquivo local CSV ou Excel
def ler_de_arquivo_local(nome_filial):
    try:
        dirs = setup_app_directories()
        data_dir = dirs["data_dir"]
        
        # Tenta encontrar arquivos CSV ou Excel na pasta de dados
        csv_path = os.path.join(data_dir, f"{nome_filial}.csv")
        excel_path = os.path.join(data_dir, f"{nome_filial}.xlsx")
        
        if os.path.exists(csv_path):
            df_original = pd.read_csv(csv_path)
        elif os.path.exists(excel_path):
            df_original = pd.read_excel(excel_path)
        else:
            st.warning(f"Arquivo de dados para {nome_filial} não encontrado.")
            return pd.DataFrame(columns=['recepcao', 'timestamp', 'atendimento', 'recomendacao', 'comentario'])
        
        return processar_dataframe(df_original)
    
    except Exception as e:
        st.error(f"Erro ao ler dados do arquivo local: {e}")
        return pd.DataFrame(columns=['recepcao', 'timestamp', 'atendimento', 'recomendacao', 'comentario'])

# Função para processar o DataFrame independentemente da origem
def processar_dataframe(df_original):
    try:
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
        
        # Se os dados já vieram com nomes de colunas corretos
        if isinstance(df_original.columns[0], str):
            colunas_possiveis = {
                'recepcao': ['recepcao', 'recepção', 'recepçao', 'recepção'],
                'timestamp': ['timestamp', 'data', 'data/hora', 'data e hora'],
                'email': ['email', 'e-mail', 'email', 'e-mail'],
                'atendimento': ['atendimento', 'nota do atendimento', 'avaliação do atendimento'],
                'recomendacao': ['recomendacao', 'recomendação', 'nota de recomendação'],
                'comentario': ['comentario', 'comentário', 'observações', 'observacoes']
            }
            
            # Tentar mapear as colunas por nome
            cols_mapeadas = {}
            for col_destino, nomes_possiveis in colunas_possiveis.items():
                for col_nome in df_original.columns:
                    if col_nome.lower() in nomes_possiveis:
                        cols_mapeadas[col_destino] = col_nome
                        break
            
            # Se encontrou todas as colunas principais
            if 'recepcao' in cols_mapeadas and 'timestamp' in cols_mapeadas and 'atendimento' in cols_mapeadas and 'recomendacao' in cols_mapeadas:
                df = pd.DataFrame()
                df['recepcao'] = df_original[cols_mapeadas.get('recepcao')].fillna('Não informado')
                df['timestamp'] = df_original[cols_mapeadas.get('timestamp')]
                df['atendimento'] = df_original[cols_mapeadas.get('atendimento')]
                df['recomendacao'] = df_original[cols_mapeadas.get('recomendacao')]
                
                if 'comentario' in cols_mapeadas:
                    df['comentario'] = df_original[cols_mapeadas.get('comentario')]
                else:
                    df['comentario'] = ""
            else:
                # Usar o método baseado em posição se não encontrou as colunas por nome
                df = pd.DataFrame()
                
                if len(df_original.columns) > col_recepcao:
                    df['recepcao'] = df_original.iloc[:, col_recepcao].fillna('Não informado')
                else:
                    df['recepcao'] = 'Não informado'
                
                if len(df_original.columns) > col_timestamp:
                    df['timestamp'] = df_original.iloc[:, col_timestamp]
                else:
                    df['timestamp'] = pd.NaT
                
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
        else:
            # Usar o método original baseado em posição
            df = pd.DataFrame()
            
            if len(df_original.columns) > col_recepcao:
                df['recepcao'] = df_original.iloc[:, col_recepcao].fillna('Não informado')
            else:
                df['recepcao'] = 'Não informado'
            
            if len(df_original.columns) > col_timestamp:
                df['timestamp'] = df_original.iloc[:, col_timestamp]
            else:
                df['timestamp'] = pd.NaT
            
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
        st.error(f"Erro ao processar dados: {e}")
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
    # Inicializa diretorios
    dirs = setup_app_directories()
    
    # Carrega a configuração das planilhas
    config = carregar_configuracao_planilhas()
    
    # Adicionar botão para configuração no sidebar
    st.sidebar.title("CEOP Dashboard")
    
    # Verifica o modo de conexão atual e exibe informação
    modo_conexao = config.get("modo_conexao", "file")
    if modo_conexao == "streamlit":
        modo_texto = "Streamlit Sheets (Online)"
    elif modo_conexao == "gspread":
        modo_texto = "GSpread API (Online)"
    else:
        modo_texto = "Arquivos Locais (Offline)"
    
    st.sidebar.info(f"Modo de conexão: {modo_texto}")
    
    # Filtro de filial (antes de carregar os dados)
    st.sidebar.header("Filial")
    filiais = config.get("filiais", {})
    
    if not filiais:
        st.error("Nenhuma filial configurada. Verifique o arquivo de configuração.")
        st.stop()
    
    filial_selecionada = st.sidebar.selectbox(
        "Selecione a filial:",
        options=list(filiais.keys()),
        index=0  # Primeira filial por padrão
    )

    # Carrega ou baixa logo
    mostrar_logo = True
    try:
        # Caminho para o logo
        logo_path = os.path.join(dirs["base_dir"], "logo Ceop.jpg")
        
        # Verifica se o logo existe
        if not os.path.exists(logo_path):
            # Tenta encontrar em caminhos alternativos
            alt_path = "../logo Ceop.jpg"
            if os.path.exists(alt_path):
                logo_path = alt_path
            else:
                mostrar_logo = False
    except Exception:
        mostrar_logo = False
    
    # Cabeçalho
    header_col1, header_col2 = st.columns([7, 3])
    
    with header_col1:
        st.title(f"Dashboard de Avaliações - {filial_selecionada}")
        st.markdown("Acompanhamento de avaliações de pacientes")
    
    with header_col2:
        # Tentar exibir o logo, se disponível
        if mostrar_logo:
            try:
                st.image(logo_path, width=150)
            except:
                st.markdown("##")  # Espaço em branco caso não consiga carregar a imagem
        else:
            st.markdown("##")  # Espaço em branco caso não tenha logo
            
        if st.button("🔄 Atualizar agora"):
            st.cache_data.clear()
            st.rerun()

    # Configuração da interface
    with st.sidebar.expander("⚙️ Configurações do Dashboard"):
        intervalo_atualizacao = st.selectbox(
            "Intervalo de atualização:",
            options=[10, 30, 60, 300, 600],
            format_func=lambda x: f"{x} segundos" if x < 60 else f"{x // 60} minuto{'s' if x >= 120 else ''}",
            index=1  # Padrão é 30 segundos
        )
        
        atualizar_automaticamente = st.checkbox("Atualizar dados automaticamente", value=True)
        
        st.info("O dashboard será atualizado automaticamente com este intervalo se a opção estiver marcada.")
        
        # Botão para salvar dados offline (útil para uso sem conexão)
        if (modo_conexao == "streamlit" or modo_conexao == "gspread") and st.button("💾 Salvar dados para uso offline"):
            try:
                # Obter dados atuais
                filial_config = filiais.get(filial_selecionada, {})
                df = ler_dados_google_sheets(filial_config)
                
                # Salvar como CSV
                csv_path = os.path.join(dirs["data_dir"], f"{filial_config.get('connection_name', 'dados')}.csv")
                df.to_csv(csv_path, index=False)
                
                st.success(f"Dados salvos com sucesso em {csv_path}")
            except Exception as e:
                st.error(f"Erro ao salvar dados: {e}")

    # Carregar dados da filial selecionada
    filial_config = filiais.get(filial_selecionada, {})
    df = ler_dados_google_sheets(filial_config)
    
    if df.empty:
        st.warning("Nenhum dado encontrado ou erro na conexão com a fonte de dados.")
        
        # Mostrar dicas de solução
        if modo_conexao == "streamlit":
            st.info("Verifique se a conexão do Streamlit com o Google Sheets está configurada corretamente.")
        elif modo_conexao == "gspread":
            st.info("Verifique se o arquivo de credenciais e os IDs das planilhas estão configurados corretamente.")
        else:
            st.info(f"Verifique se existem arquivos CSV ou Excel para esta filial na pasta {dirs['data_dir']}.")
        
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
    
    # Sistema de atualização automática mais seguro
    if atualizar_automaticamente:
        # Usar um método mais compatível com diferentes ambientes
        st.markdown("---")
        atualizacao_info = st.empty()
        
        # Exibir informação sobre a próxima atualização
        tempo_atual = int(time.time())
        proxima_atualizacao = tempo_atual + intervalo_atualizacao
        
        atualizacao_info.info(f"Próxima atualização automática às {time.strftime('%H:%M:%S', time.localtime(proxima_atualizacao))}")
        
        # Adicionar script JavaScript para recarregar a página após o intervalo
        # Isso é mais confiável que usar sleep() que pode bloquear a thread
        js_code = f"""
        <script>
            // Programar recarregamento da página
            setTimeout(function() {{
                window.location.reload();
            }}, {intervalo_atualizacao * 1000});
        </script>
        """
        st.markdown(js_code, unsafe_allow_html=True)
    else:
        st.info("Atualização automática desativada. Clique em 'Atualizar agora' para atualizar os dados.")

# Página de configuração para quando o usuário clica em "Configurações" no sidebar
def pagina_configuracao():
    st.title("Configurações do Dashboard")
    
    # Inicializa diretorios
    dirs = setup_app_directories()
    
    # Carrega a configuração atual
    config = carregar_configuracao_planilhas()
    
    st.markdown("### Modo de Conexão")
    
    # Opções de modo de conexão
    modos_disponiveis = []
    
    # Sempre disponível
    modos_disponiveis.append("file")
    
    # Verificar disponibilidade do Streamlit Sheets
    if STREAMLIT_GSHEETS_AVAILABLE:
        modos_disponiveis.append("streamlit")
    
    # Verificar disponibilidade do GSpread
    if GOOGLE_LIBRARIES_AVAILABLE:
        modos_disponiveis.append("gspread")
    
    # Mapear para nomes amigáveis
    modos_nomes = {
        "file": "Arquivos Locais (offline)",
        "streamlit": "Streamlit Google Sheets (online)",
        "gspread": "Google Sheets API (online)"
    }
    
    modo_atual = config.get("modo_conexao", "file")
    
    modo_selecionado = st.radio(
        "Selecione o modo de conexão para os dados:",
        modos_disponiveis,
        format_func=lambda x: modos_nomes.get(x, x),
        index=modos_disponiveis.index(modo_atual) if modo_atual in modos_disponiveis else 0
    )
    
    # Se modo selecionado é diferente do atual, atualizar
    if modo_selecionado != modo_atual:
        config["modo_conexao"] = modo_selecionado
        
        # Salvar configuração
        try:
            config_file = os.path.join(dirs["config_dir"], "sheets_config.json")
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            st.success(f"Modo de conexão alterado para {modos_nomes[modo_selecionado]}")
        except Exception as e:
            st.error(f"Erro ao salvar configuração: {e}")
    
    # Configuração específica para cada modo
    if modo_selecionado == "gspread":
        st.markdown("### Configuração do Google Sheets API")
        
        # Verificar se já existe arquivo de credenciais
        creds_file = os.path.join(dirs["config_dir"], "credentials.json")
        creds_existe = os.path.exists(creds_file)
        
        if creds_existe:
            st.success("Arquivo de credenciais encontrado!")
            st.info("Para atualizar as credenciais, envie um novo arquivo JSON.")
        
        uploaded_file = st.file_uploader("Envie o arquivo de credenciais do Google Service Account (JSON):", type=['json'])
        
        if uploaded_file is not None:
            try:
                # Salvar o arquivo de credenciais
                with open(creds_file, 'wb') as f:
                    f.write(uploaded_file.getbuffer())
                st.success("Arquivo de credenciais salvo com sucesso!")
            except Exception as e:
                st.error(f"Erro ao salvar arquivo de credenciais: {e}")
        
        # Configuração de planilhas
        st.markdown("### Configuração das Planilhas")
        
        # Mostrar configuração atual
        filiais = config.get("filiais", {})
        
        for filial, filial_config in filiais.items():
            st.markdown(f"#### {filial}")
            
            # ID da planilha
            novo_sheet_id = st.text_input(
                f"ID da planilha do Google Sheets para {filial}:",
                value=filial_config.get("sheet_id", ""),
                key=f"sheet_id_{filial}"
            )
            
            # Nome da aba
            novo_sheet_name = st.text_input(
                f"Nome da aba na planilha para {filial} (deixe em branco para usar a primeira aba):",
                value=filial_config.get("sheet_name", ""),
                key=f"sheet_name_{filial}"
            )
            
            # Atualizar configuração se valores foram alterados
            if (novo_sheet_id != filial_config.get("sheet_id", "") or 
                novo_sheet_name != filial_config.get("sheet_name", "")):
                
                filial_config["sheet_id"] = novo_sheet_id
                filial_config["sheet_name"] = novo_sheet_name
                
                # Salvar a configuração atualizada
                try:
                    config_file = os.path.join(dirs["config_dir"], "sheets_config.json")
                    with open(config_file, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=4, ensure_ascii=False)
                    st.success(f"Configuração para {filial} atualizada!")
                except Exception as e:
                    st.error(f"Erro ao salvar configuração: {e}")
            
            st.markdown("---")
    
    elif modo_selecionado == "streamlit":
        st.markdown("### Configuração do Streamlit Google Sheets")
        st.info("""
        Para usar o Streamlit Google Sheets, você precisa configurar conexões no Streamlit Cloud.
        Se estiver executando localmente, consulte a documentação do Streamlit sobre como configurar conexões.
        
        [Documentação do Streamlit sobre conexões](https://docs.streamlit.io/library/api-reference/connections)
        """)
        
        # Mostrar configuração atual
        filiais = config.get("filiais", {})
        
        for filial, filial_config in filiais.items():
            st.markdown(f"#### {filial}")
            
            # Nome da conexão
            novo_conn_name = st.text_input(
                f"Nome da conexão para {filial}:",
                value=filial_config.get("connection_name", ""),
                key=f"conn_name_{filial}"
            )
            
            # Atualizar configuração se valores foram alterados
            if novo_conn_name != filial_config.get("connection_name", ""):
                
                filial_config["connection_name"] = novo_conn_name
                
                # Salvar a configuração atualizada
                try:
                    config_file = os.path.join(dirs["config_dir"], "sheets_config.json")
                    with open(config_file, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=4, ensure_ascii=False)
                    st.success(f"Configuração para {filial} atualizada!")
                except Exception as e:
                    st.error(f"Erro ao salvar configuração: {e}")
            
            st.markdown("---")
    
    elif modo_selecionado == "file":
        st.markdown("### Configuração de Arquivos Locais")
        st.info(f"""
        Os arquivos devem estar no diretório de dados: 
        {dirs['data_dir']}
        
        Os arquivos devem ter o mesmo nome das conexões configuradas, com extensão .csv ou .xlsx
        """)
        
        # Mostrar configuração atual
        filiais = config.get("filiais", {})
        
        for filial, filial_config in filiais.items():
            st.markdown(f"#### {filial}")
            
            # Nome do arquivo
            nome_arquivo = filial_config.get("connection_name", "")
            if not nome_arquivo:
                nome_arquivo = filial.lower().replace(" ", "_")
            
            novo_nome_arquivo = st.text_input(
                f"Nome do arquivo para {filial} (sem extensão):",
                value=nome_arquivo,
                key=f"file_name_{filial}"
            )
            
            # Atualizar configuração se valores foram alterados
            if novo_nome_arquivo != filial_config.get("connection_name", ""):
                
                filial_config["connection_name"] = novo_nome_arquivo
                
                # Salvar a configuração atualizada
                try:
                    config_file = os.path.join(dirs["config_dir"], "sheets_config.json")
                    with open(config_file, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=4, ensure_ascii=False)
                    st.success(f"Configuração para {filial} atualizada!")
                except Exception as e:
                    st.error(f"Erro ao salvar configuração: {e}")
            
            # Verificar se o arquivo existe
            csv_path = os.path.join(dirs["data_dir"], f"{novo_nome_arquivo}.csv")
            excel_path = os.path.join(dirs["data_dir"], f"{novo_nome_arquivo}.xlsx")
            
            if os.path.exists(csv_path):
                st.success(f"Arquivo CSV encontrado: {csv_path}")
            elif os.path.exists(excel_path):
                st.success(f"Arquivo Excel encontrado: {excel_path}")
            else:
                st.warning(f"Nenhum arquivo encontrado para {filial}. Crie um arquivo CSV ou Excel.")
                
                # Opção para enviar arquivo
                uploaded_file = st.file_uploader(
                    f"Envie um arquivo CSV ou Excel para {filial}:",
                    type=['csv', 'xlsx'],
                    key=f"upload_{filial}"
                )
                
                if uploaded_file is not None:
                    try:
                        # Determinar extensão
                        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
                        if file_ext == '.csv':
                            save_path = csv_path
                        else:
                            save_path = excel_path
                        
                        # Salvar o arquivo
                        with open(save_path, 'wb') as f:
                            f.write(uploaded_file.getbuffer())
                        st.success(f"Arquivo salvo com sucesso em {save_path}")
                    except Exception as e:
                        st.error(f"Erro ao salvar arquivo: {e}")
            
            st.markdown("---")
    
    st.markdown("### Gerenciamento de Filiais")
    
    # Adicionar nova filial
    st.markdown("#### Adicionar Nova Filial")
    nova_filial = st.text_input("Nome da nova filial:")
    if nova_filial and st.button("Adicionar Filial"):
        if nova_filial in config.get("filiais", {}):
            st.error("Esta filial já existe!")
        else:
            # Adicionar nova filial à configuração
            if "filiais" not in config:
                config["filiais"] = {}
            
            # Criar configuração padrão para a nova filial
            config["filiais"][nova_filial] = {
                "sheet_id": "",
                "sheet_name": "",
                "connection_name": nova_filial.lower().replace(" ", "_")
            }
            
            # Salvar configuração
            try:
                config_file = os.path.join(dirs["config_dir"], "sheets_config.json")
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                st.success(f"Filial {nova_filial} adicionada com sucesso!")
            except Exception as e:
                st.error(f"Erro ao salvar configuração: {e}")
    
    # Remover filial
    st.markdown("#### Remover Filial")
    filiais_lista = list(config.get("filiais", {}).keys())
    if filiais_lista:
        filial_para_remover = st.selectbox("Selecione a filial para remover:", filiais_lista)
        if st.button("Remover Filial"):
            # Remover filial da configuração
            if filial_para_remover in config.get("filiais", {}):
                del config["filiais"][filial_para_remover]
                
                # Salvar configuração
                try:
                    config_file = os.path.join(dirs["config_dir"], "sheets_config.json")
                    with open(config_file, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=4, ensure_ascii=False)
                    st.success(f"Filial {filial_para_remover} removida com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao salvar configuração: {e}")
    else:
        st.info("Nenhuma filial disponível para remover.")
    
    # Botão para voltar ao dashboard
    if st.button("Voltar ao Dashboard"):
        st.session_state.pagina = "dashboard"
        st.rerun()

# Ponto de entrada do aplicativo
if __name__ == "__main__":
    # Verifica se há uma página selecionada na sessão
    if "pagina" not in st.session_state:
        st.session_state.pagina = "dashboard"
    
    # Botão para alternar para página de configurações
    if st.sidebar.button("⚙️ Configurar Fontes de Dados"):
        st.session_state.pagina = "config"
    
    # Exibe a página apropriada
    if st.session_state.pagina == "dashboard":
        main()
    elif st.session_state.pagina == "config":
        pagina_configuracao()
