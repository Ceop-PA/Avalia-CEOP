# Dashboard de Avaliações CEOP

Este dashboard foi desenvolvido para visualizar dados de avaliações de pacientes das unidades CEOP. Ele é flexível e pode ser executado em diferentes ambientes:

1. Localmente como aplicativo Streamlit
2. Na web via Streamlit Cloud
3. Como aplicativo independente

## Requisitos

### Dependências básicas

```
streamlit>=1.25.0
pandas>=1.3.0
numpy>=1.20.0
plotly>=5.5.0
```

### Dependências opcionais (para conexão online com Google Sheets)

```
google-auth>=2.0.0
gspread>=5.0.0
gspread-pandas>=3.0.0
gspread-dataframe>=3.0.0
streamlit-gsheets>=0.0.1
```

## Instalação

### 1. Instalação como aplicativo Python local

1. Clone ou baixe este repositório
2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Execute o dashboard:

```bash
streamlit run ceop_dashboard.py
```

### 2. Configuração no Streamlit Cloud

1. Faça upload do código para um repositório GitHub
2. Conecte o repositório ao Streamlit Cloud
3. Configure as conexões com Google Sheets no Streamlit Cloud
4. Implante o aplicativo

### 3. Criação de aplicativo independente

Você pode criar um executável independente usando PyInstaller:

```bash
pip install pyinstaller
pyinstaller --name "CEOP Dashboard" --onefile --windowed --add-data "logo Ceop.jpg;." ceop_dashboard.py
```

## Configuração

O dashboard oferece três modos de acesso aos dados:

### 1. Arquivos Locais (Offline)

Coloque arquivos CSV ou Excel na pasta `data`. Os arquivos devem ter o mesmo nome configurado para cada filial.

### 2. Google Sheets API (Online)

Requer um arquivo de credenciais do Google Service Account e configuração dos IDs de planilha.

1. Crie um projeto no Google Cloud Console
2. Ative a API do Google Sheets
3. Crie uma conta de serviço e baixe o arquivo JSON de credenciais
4. Compartilhe suas planilhas com o e-mail da conta de serviço
5. Configure os IDs das planilhas no dashboard

### 3. Streamlit Google Sheets (Online)

Método mais simples para uso com Streamlit Cloud.

1. Configure conexões com Google Sheets no painel do Streamlit Cloud
2. Selecione este modo no dashboard

## Uso

1. Na primeira execução, clique em "⚙️ Configurar Fontes de Dados" para definir o modo de acesso aos dados
2. Configure as planilhas para cada filial
3. Retorne ao dashboard para visualizar os dados

## Estrutura de Planilhas

O dashboard espera dados nas seguintes colunas:

- **Recepção**: Nome da recepção
- **Timestamp**: Data e hora da avaliação
- **E-mail**: E-mail do paciente (opcional)
- **Atendimento**: Nota do atendimento (0-10)
- **Recomendação**: Nota de recomendação (0-10)
- **Comentário**: Comentários do paciente

## Suporte

Em caso de dúvidas ou problemas, entre em contato conosco. 