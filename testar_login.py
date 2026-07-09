import os
import sys
import time
import logging
import subprocess

# Configurar logging para exibir no console em tempo real
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

from acs_runner import matar_acs
from acs_automation import iniciar_sessao_acs, finalizar_sessao_acs

EXE_PATH = r"C:\ACSSoft\Sintese\Gerente SPED\gerente.exe"

def main():
    print("============================================================")
    print("             TESTE DE EXECUÇÃO E LOGIN DO SISTEMA           ")
    print("============================================================")
    
    # 1. Matar qualquer instância anterior do ACS Gerente para evitar conflito
    print("[RPA] Fechando instâncias anteriores do ACS Gerente...")
    matar_acs()
    time.sleep(1.0)
    
    # 2. Iniciar o processo
    print(f"[RPA] Lançando o executável: {EXE_PATH}")
    if not os.path.exists(EXE_PATH):
        print(f"[ERRO] Executável não encontrado em: {EXE_PATH}")
        sys.exit(1)
        
    try:
        subprocess.Popen([EXE_PATH])
        print("[RPA] Processo iniciado com sucesso!")
    except Exception as e:
        print(f"[ERRO] Falha ao executar o processo: {e}")
        sys.exit(1)
        
    # 3. Iniciar a sessão (esperar abrir, fechar avisos e realizar login)
    print("[RPA] Iniciando sessão (fechando avisos de startup e executando login)...")
    app_win, handler = iniciar_sessao_acs("") # empresa_nome vazia usa o padrão do combo
    
    if app_win:
        print("\n============================================================")
        print("           SESSÃO E LOGIN CONCLUÍDOS COM SUCESSO!           ")
        print("============================================================")
        
        # Mantém a janela aberta por 5 segundos para que o usuário possa ver
        print("[RPA] Mantendo o sistema aberto por 5 segundos para verificação...")
        time.sleep(5.0)
        
        # Fechar graciosamente no final
        print("[RPA] Fechando o sistema...")
        matar_acs()
    else:
        print("\n============================================================")
        print("                 FALHA AO REALIZAR O LOGIN                  ")
        print("============================================================")
        
    # Limpar handlers de background
    finalizar_sessao_acs(handler)

if __name__ == "__main__":
    main()
