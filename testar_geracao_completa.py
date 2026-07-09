import os
import sys
import time
import logging

# Configurar logging para exibir no console em tempo real
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

from acs_runner import executar_acs_e_gerar_sped, matar_acs
from file_manager import organizar_sped_posto
from ini_manager import atualizar_ini

def main():
    print("============================================================")
    print("   TESTE DE PRODUÇÃO DE RPA: LOGIN + SPED FISCAL A/B + CONTRIB")
    print("============================================================")
    
    # Modo a ser testado: 'Perfil A' para rodar a geração completa Fiscal A + B + Contrib
    # (Fiscal B -> Contribuições -> Trocar para Perfil A -> Fiscal A -> Voltar para Perfil B)
    info_sped = "Perfil A"
    posto_nome = "POSTO ADEMIR"
    banco_base = "Ademir"
    
    print(f"[RPA Test] Iniciando geração completa para '{posto_nome}'...")
    print(f"[RPA Test] Modo: '{info_sped}' (Fiscal A e B + Contribuições)")
    
    start_time = time.time()
    
    try:
        # Garante que o acsgerente.ini está apontando para o banco correto
        print("[RPA Test] Atualizando acsgerente.ini para apontar para o banco correto...")
        atualizar_ini(banco_base, posto_nome)

        # Aplica os fixes no banco de dados local antes do teste
        print("[RPA Test] Aplicando correções do banco de dados (aliases, inventário, aberturas)...")
        nome_db_local = f"{banco_base.lower()}_local"
        from postgres_manager import fix_prestacao_update_alias, fix_saldo_mes_inventario, fix_aberturas_medicao
        fix_saldo_mes_inventario(nome_db_local)
        fix_prestacao_update_alias(nome_db_local)
        fix_aberturas_medicao(nome_db_local)

        # Executa a geração usando a função do pipeline de produção
        arquivos_gerados = executar_acs_e_gerar_sped(
            nome_posto=posto_nome,
            nome_base=banco_base,
            informacoes_sped=info_sped
        )
        
        elapsed = time.time() - start_time
        
        print("\n============================================================")
        print("                 RESULTADO DA AUTOMACÃO")
        print("============================================================")
        print(f"Tempo total de execução: {elapsed:.1f} segundos ({elapsed/60:.1f} minutos)")
        
        if arquivos_gerados:
            # Organiza e move os arquivos válidos para a pasta da empresa
            print("\n[RPA Test] Organizando e movendo arquivos para a pasta da empresa...")
            arquivos_finais = organizar_sped_posto(posto_nome, arquivos_gerados)
            
            print(f"\n[SUCESSO] Foram gerados {len(arquivos_finais)} arquivo(s) organizados na pasta da empresa:")
            for arq in arquivos_finais:
                print(f"  - {arq} (Tamanho: {os.path.getsize(arq)} bytes)")
            
            # Verificar se todos os 3 arquivos esperados para Perfil A foram gerados
            if len(arquivos_finais) >= 3:
                print("\n[OK] Todos os 3 arquivos (Fiscal B, Contribuições, Fiscal A) foram gerados, validados e guardados na pasta!")
                sys.exit(0)
            else:
                print(f"\n[ATENÇÃO] Sucesso parcial. Gerados {len(arquivos_finais)} de 3 arquivos esperados.")
                sys.exit(2)
        else:
            print("\n[ERRO] Nenhum arquivo foi gerado ou todos falharam na validação.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n[FALHA CATASTRÓFICA] Erro durante a automação: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        matar_acs()

if __name__ == "__main__":
    main()
