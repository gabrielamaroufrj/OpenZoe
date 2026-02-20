# reports/charts_export.py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import datetime
import os

def gerar_png_evolucao(dados, modo_multiplo, diretorio, caminho_oculto=None):
    try:
        plt.figure(figsize=(12, 6))
        if not modo_multiplo:
            eixo_x = [d[0] for d in dados]
            eixo_y = [d[1] for d in dados]
            plt.plot(eixo_x, eixo_y, marker='o', linestyle='-', color='b')
        else:
            datas_unicas = sorted(list(set(d[0] for d in dados)))
            medicos_unicos = sorted(list(set(d[1] for d in dados)))
            mapa_dados = {med: {d: 0 for d in datas_unicas} for med in medicos_unicos}
            for r in dados: mapa_dados[r[1]][r[0]] = r[2]
            cores = plt.cm.tab10.colors
            for i, medico in enumerate(medicos_unicos):
                y_vals = [mapa_dados[medico][d] for d in datas_unicas]
                plt.plot(datas_unicas, y_vals, marker='o', linestyle='-', label=medico, color=cores[i % len(cores)])
            plt.legend(title="Médicos")

        plt.title("Evolução Temporal de Exames")
        plt.xlabel("Data"); plt.ylabel("Quantidade")
        plt.grid(True, linestyle='--', alpha=0.7); plt.xticks(rotation=45, fontsize=8)
        plt.tight_layout()

        if caminho_oculto:
            plt.savefig(caminho_oculto, dpi=150)
            plt.close()
            return True, caminho_oculto

        nome_arquivo = os.path.join(diretorio, f"evolucao_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        plt.savefig(nome_arquivo, dpi=300)
        plt.close()
        return True, os.path.basename(nome_arquivo)
    except Exception as e: return False, str(e)

def gerar_png_dose_medico(dados, diretorio, caminho_oculto=None):
    try:
        eixo_x = [d[0] for d in dados]
        eixo_y = [d[1] for d in dados]
        plt.figure(figsize=(10, 6))
        plt.axhline(y=1000, color='#8F00FF', linestyle='--', linewidth=2)
        plt.axhline(y=2000, color='blue', linestyle='--', linewidth=2)
        plt.axhline(y=3000, color='yellow', linestyle='--', linewidth=2)
        plt.axhline(y=4000, color='orange', linestyle='--', linewidth=2)
        plt.axhline(y=5000, color='red', linestyle='--', linewidth=2)
        plt.bar(eixo_x, eixo_y, color='b')
        plt.title("Média de Dose por Médico"); plt.xlabel("Médico"); plt.ylabel("Dose Média (mGy)")
        plt.grid(True, linestyle='--', alpha=0.7); plt.xticks(rotation=45)
        plt.tight_layout()

        if caminho_oculto:
            plt.savefig(caminho_oculto, dpi=150); plt.close(); return True, caminho_oculto

        nome_arquivo = os.path.join(diretorio, f"Dose_medico_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        plt.savefig(nome_arquivo, dpi=300); plt.close(); return True, os.path.basename(nome_arquivo)
    except Exception as e: return False, str(e)

def gerar_png_tempo_medico(dados, diretorio, caminho_oculto=None):
    try:
        eixo_x = [d[0] for d in dados]
        eixo_y = [d[1] for d in dados]
        plt.figure(figsize=(10, 6))
        plt.bar(eixo_x, eixo_y, color='b')
        plt.title("Média de Tempo por Médico"); plt.xlabel("Médico"); plt.ylabel("Tempo Médio (min)")
        plt.grid(True, linestyle='--', alpha=0.7); plt.xticks(rotation=45)
        plt.tight_layout()

        if caminho_oculto:
            plt.savefig(caminho_oculto, dpi=150); plt.close(); return True, caminho_oculto

        nome_arquivo = os.path.join(diretorio, f"Tempo_medico_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        plt.savefig(nome_arquivo, dpi=300); plt.close(); return True, os.path.basename(nome_arquivo)
    except Exception as e: return False, str(e)

def gerar_png_dose_exame(dados, modo_multiplo, diretorio, caminho_oculto=None):
    try:
        plt.figure(figsize=(12, 6))
        plt.axhline(y=1000, color='#8F00FF', linestyle='--', linewidth=2)
        plt.axhline(y=2000, color='blue', linestyle='--', linewidth=2)
        plt.axhline(y=3000, color='yellow', linestyle='--', linewidth=2)
        plt.axhline(y=4000, color='orange', linestyle='--', linewidth=2)
        plt.axhline(y=5000, color='red', linestyle='--', linewidth=2)

        if not modo_multiplo:
            eixo_x = [d[0] for d in dados]; eixo_y = [d[1] for d in dados]
            plt.bar(eixo_x, eixo_y, color='b'); plt.xlabel("Exame")
        else:
            exames = sorted(list(set(d[0] for d in dados)))
            medicos = sorted(list(set(d[1] for d in dados)))
            largura_barra = 0.8 / len(medicos); posicoes = list(range(len(exames)))
            
            dados_map = {ex: {} for ex in exames}
            for row in dados: dados_map[row[0]][row[1]] = row[2] 
            cores = plt.cm.tab10.colors 

            for i, medico in enumerate(medicos):
                valores = [dados_map[exame].get(medico, 0) for exame in exames]
                pos_deslocada = [p + (i * largura_barra) for p in posicoes]
                plt.bar(pos_deslocada, valores, width=largura_barra, label=medico, color=cores[i % len(cores)])

            centro_grupo = [p + largura_barra * (len(medicos) - 1) / 2 for p in posicoes]
            plt.xticks(centro_grupo, exames, rotation=45)
            plt.legend(title="Médicos"); plt.xlabel("Exame")

        plt.title("Média de Dose por Exame"); plt.ylabel("Dose média (mGy)")
        plt.grid(True, linestyle='--', alpha=0.7, axis='y'); plt.tight_layout() 

        if caminho_oculto:
            plt.savefig(caminho_oculto, dpi=150); plt.close(); return True, caminho_oculto

        nome_arquivo = os.path.join(diretorio, f"Dose_exame_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        plt.savefig(nome_arquivo, dpi=300); plt.close(); return True, os.path.basename(nome_arquivo)
    except Exception as e: return False, str(e)

def gerar_png_tempo_exame(dados, modo_multiplo, diretorio, caminho_oculto=None):
    try:
        plt.figure(figsize=(12, 6))
        if not modo_multiplo:
            eixo_x = [d[0] for d in dados]; eixo_y = [d[1] for d in dados]
            plt.bar(eixo_x, eixo_y, color='orange'); plt.xlabel("Exame")
        else:
            exames = sorted(list(set(d[0] for d in dados)))
            medicos = sorted(list(set(d[1] for d in dados)))
            largura_barra = 0.8 / len(medicos); posicoes = list(range(len(exames)))
            
            dados_map = {ex: {} for ex in exames}
            for row in dados: dados_map[row[0]][row[1]] = row[2] 
            cores = plt.cm.tab10.colors 

            for i, medico in enumerate(medicos):
                valores = [dados_map[exame].get(medico, 0) for exame in exames]
                pos_deslocada = [p + (i * largura_barra) for p in posicoes]
                plt.bar(pos_deslocada, valores, width=largura_barra, label=medico, color=cores[i % len(cores)])

            centro_grupo = [p + largura_barra * (len(medicos) - 1) / 2 for p in posicoes]
            plt.xticks(centro_grupo, exames, rotation=45)
            plt.legend(title="Médicos"); plt.xlabel("Exame")

        plt.title("Média de Tempo por Exame"); plt.ylabel("Tempo médio (min)")
        plt.grid(True, linestyle='--', alpha=0.7, axis='y'); plt.tight_layout() 

        if caminho_oculto:
            plt.savefig(caminho_oculto, dpi=150); plt.close(); return True, caminho_oculto

        nome_arquivo = os.path.join(diretorio, f"Tempo_exame_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        plt.savefig(nome_arquivo, dpi=300); plt.close(); return True, os.path.basename(nome_arquivo)
    except Exception as e: return False, str(e)