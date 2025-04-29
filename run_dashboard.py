import os
import webbrowser
import threading
import sys

DASHBOARD_PATH = os.path.join('DASHBOARD', 'ceop_dashboard.py')


def start_streamlit():
    # Garante que o comando funcione mesmo se for executado como .exe
    os.system(f'streamlit run "{DASHBOARD_PATH}"')

if __name__ == "__main__":
    # Abre o navegador após 2 segundos
    threading.Timer(2, lambda: webbrowser.open("http://localhost:8501")).start()
    start_streamlit() 