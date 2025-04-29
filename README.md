# Dashboard de Avaliações CEOP - Executável

Este repositório contém o código-fonte e os scripts necessários para compilar o Dashboard de Avaliações CEOP como um aplicativo desktop executável.

## Estrutura do Projeto

```
├── DASHBOARD/
│   └── ceop_dashboard.py         # Script principal do dashboard
├── AVALIAÇÃO PACIENTES/
│   └── avaliação.html            # Formulário de avaliação
├── .streamlit/
│   ├── config.toml               # Configurações do Streamlit
│   └── secrets.toml              # Credenciais (manter privado)
├── dashboard.spec                # Especificação do PyInstaller
├── run_dashboard.py              # Script wrapper para o executável
├── check_dependencies.py         # Verificador de dependências
├── compile_dashboard.bat         # Script de compilação (Windows)
├── compile_dashboard.sh          # Script de compilação (Linux/macOS)
├── installer.bat                 # Instalador simples (Windows)
├── uninstall.bat                 # Desinstalador (Windows)
├── requirements-build.txt        # Requisitos para compilação
└── README_COMPILE.md             # Instruções detalhadas de compilação
```

## Sobre o Projeto

Este projeto permite transformar o dashboard Streamlit de avaliações do CEOP em um aplicativo desktop independente, facilitando o uso para usuários sem conhecimento técnico.

## Características

- **Interface Web em Aplicativo Desktop**: Executa o Streamlit localmente e abre automaticamente no navegador
- **Visualização em Tempo Real**: Conecta-se ao Google Sheets para obter dados atualizados
- **Fácil Distribuição**: Pode ser distribuído como um executável sem necessidade de instalar Python
- **Compatível com Windows, Linux e macOS**: Scripts de compilação para cada plataforma

## Como Compilar o Executável

Para instruções detalhadas sobre como compilar o executável, consulte o arquivo [README_COMPILE.md](README_COMPILE.md).

### Resumo Rápido (Windows)

1. Certifique-se de ter Python 3.8+ instalado
2. Execute o script de compilação:
   ```
   compile_dashboard.bat
   ```
3. Após a compilação, instale o aplicativo (opcional):
   ```
   installer.bat
   ```

## Requisitos

- Python 3.8 ou superior
- PyInstaller 5.13.0 ou superior
- Streamlit 1.24.0 ou superior
- Pandas, NumPy, Plotly
- Conexão com internet (para acessar o Google Sheets)

## Uso do Dashboard Original

Para executar o dashboard em modo de desenvolvimento sem compilar:
```
streamlit run DASHBOARD/ceop_dashboard.py
```

## Estrutura dos Dados

O dashboard espera que a planilha do Google Sheets tenha as seguintes colunas:
1. Carimbo de data/hora (timestamp)
2. Email do usuário
3. Avaliação de atendimento (nota de 0 a 10)
4. Recomendação (nota de 0 a 10)
5. Comentário (opcional) 