"""
OpenZoe v1.0.2
------------------
Sistema de gerenciamento e análise de doses radiológicas baseado em arquivos DICOM SR.
Desenvolvido com Python, Flet, SQLite, Pydicom e Matplotlib.

Autor: Gabriel Amaro
Licença: MIT
"""

import flet as ft
import flet_charts as fch
import sqlite3
import datetime
import math 
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import pydicom
from pydicom import config
import os
import csv
import io
from fpdf import FPDF
import tempfile


# --- VARIÁVEIS GLOBAIS ---
data_inicio = ""
data_final = ""
pagina_atual = 1
itens_por_pagina = 15
FILE_PATH = ""
directory_path = ""
upload_path = ""
texto_csv_para_salvar = None

# Mapeamento de Códigos DICOM para Nomes Legíveis
codigos_dose = {
    "113722": ("Dose Area Product Total", "Gy·m²"),
    "113725": ("Dose (RP) Total", "Gy"),
    "113730": ("Total Fluoro Time", "s"),
    "113855": ("Total Acquisition Time", "s"),
    "122130": ("Dose Area Product (Individual)", "Gy·m²"),
    "113738": ("Dose (RP) (Individual)", "Gy")}

# Lista padrão para fallback (caso o banco esteja vazio)
lista_exames = []
lista_equipamentos = []
# --- CONFIGURAÇÕES GLOBAIS ---
config.convert_wrong_length_to_UN = True
config.enforce_valid_values = False



# --- FUNÇÃO EXTRA DE CONVERSÃO DE TEMPO ---
def tempo_para_minutos(tempo_str):
    if not tempo_str or str(tempo_str) == "None":
        return 0.0
    try:
        t = str(tempo_str).split(' ')[-1]
        h, m, s = t.split(':')
        total = int(h) * 60 + int(m) + float(s) / 60
        return total
    except:
        return 0.0
    
def formatar_data(valor):
    """Formata data para exibição (apenas YYYY-MM-DD)."""
    return str(valor).split()[0] if valor else ""

def formatar_tempo(valor):
    """Remove milissegundos da string de tempo."""
    return str(valor).split()[0].replace('.000000', '') if valor else ""

# --- CLASSE DO RELATÓRIO PDF ---

# --- CLASSE DO RELATÓRIO PDF ---
class RelatorioPDF(FPDF):
    def header(self):
        # 1. Pega o caminho absoluto (à prova de falhas)
        diretorio_atual = os.path.dirname(os.path.abspath(__file__))
        caminho_logo = os.path.join(diretorio_atual, "assets", "icon.png")
        
        # 2. Adiciona a Logo (se existir)
        if os.path.exists(caminho_logo):
            self.image(caminho_logo, x=10, y=8, w=12) 
        else:
            # Apenas para você saber se o caminho ainda está errado durante os testes
            print(f"ATENÇÃO: Logo não encontrada no caminho: {caminho_logo}")

        # 3. Título principal
        self.set_font("helvetica", "B", 16)
        self.set_text_color(0, 51, 102) 
        self.cell(0, 10, "OpenZoe - Relatório de Dosimetria e Qualidade", align="C", new_x="LMARGIN", new_y="NEXT")
        
        # 4. Linha horizontal separadora
        self.line(10, 24, 200, 24) 
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Página {self.page_no()}", align="C")

# ==============================================================================
#                           CAMADA DE BANCO DE DADOS
# ==============================================================================

# --- 1. FUNÇÕES DE BANCO DE DADOS ---

def conectar():
    if not FILE_PATH: return None
    return sqlite3.connect(FILE_PATH)

def montar_query_filtros(data_inicio, data_fim, min_d, max_d, n_medico, exm, min_tempo, max_tempo, min_dap, max_dap, sala, sexo, id_pac):
    sql_base = " FROM exames WHERE 1=1"
    params = []

    if data_inicio and data_fim:
        sql_base += " AND date(data) BETWEEN ? AND ?"
        params.extend([data_inicio, data_fim])
    elif data_inicio:
        sql_base += " AND date(data) >= ?"
        params.append(data_inicio)

    if min_d and str(min_d).strip():
        sql_base += " AND CAST(REPLACE(dose_mgy, ',', '.') AS REAL) >= ?"
        params.append(min_d)
    
    if max_d and str(max_d).strip():
        sql_base += " AND CAST(REPLACE(dose_mgy, ',', '.') AS REAL) <= ?"
        params.append(max_d)
    
    if n_medico and str(n_medico).strip():
        entrada_medico = str(n_medico).strip()
        if ";" in entrada_medico:
            lista_medicos = [m.strip() for m in entrada_medico.split(";") if m.strip()]
            if lista_medicos:
                placeholders = ",".join(["?"] * len(lista_medicos))
                sql_base += f" AND medico IN ({placeholders})"
                params.extend(lista_medicos)
        else:
            sql_base += " AND medico = ?" 
            params.append(entrada_medico)
    
    if exm and str(exm).strip():
        sql_base += " AND exam = ?" 
        params.append(str(exm).strip())

    if min_tempo and str(min_tempo).strip():
        sql_base += " AND tempo >= ?"
        params.append(min_tempo)

    if max_tempo and str(max_tempo).strip():
        sql_base += " AND tempo <= ?"
        params.append(max_tempo)

    if min_dap and str(min_dap).strip():
        sql_base += " AND CAST(dap AS REAL) >= ?"
        params.append(min_dap)

    if max_dap and str(max_dap).strip():
        sql_base += " AND CAST(dap AS REAL) <= ?"
        params.append(max_dap)

    if sala and str(sala).strip():
        sql_base += " AND sala == ?"
        params.append(sala)

    if sexo and str(sexo).strip():
        sql_base += " AND sexo = ?"
        params.append(sexo)

    if id_pac and str(id_pac).strip():
        sql_base += " AND paciente_id = ?" 
        params.append(id_pac)
    
    return sql_base, params

def carregar_dados_banco(data_inicio, data_fim, min_d, max_d, n_medico, exm, min_tempo, max_tempo, min_dap, max_dap, sala,sexo, id_pac, limit=15, offset=0):
    dados = []
    total_registros = 0
    try:
        conn = conectar()
        cursor = conn.cursor()
        
        sql_where, params = montar_query_filtros(data_inicio, data_fim, min_d, max_d, n_medico, exm, min_tempo, max_tempo, min_dap, max_dap, sala, sexo, id_pac)
        
        cursor.execute(f"SELECT COUNT(*) {sql_where}", params)
        total_registros = cursor.fetchone()[0]

        sql_dados = f"SELECT rowid, data, medico, exam, dose_mgy, tempo, dap, paciente_id, sexo, sala {sql_where} ORDER BY data DESC LIMIT ? OFFSET ?"
        
        params_dados = params.copy()
        params_dados.extend([limit, offset])

        cursor.execute(sql_dados, params_dados)
        dados = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"Erro SQL Dados: {e}")
    
    return dados, total_registros

def criar_indices():
    try:
        conn = conectar()
        if not conn: return
        cursor = conn.cursor()
        # Cria "atalhos" para busca rápida
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_data ON exames(data)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_medico ON exames(medico)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_exam ON exames(exam)")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erro ao criar índices: {e}")

# --- CSV ---

def gerar_csv_string(apenas_filtrados=False, inputs_filtros=None):
    """
    Gera o conteúdo CSV garantindo o alinhamento correto das colunas.
    """
    try:
        conn = conectar()
        if not conn: return ""
        cursor = conn.cursor()
        
        # 1. Definição da Ordem Exata (Cabeçalho)
        colunas_header = [
            "ID",           # 0
            "Data",         # 1
            "Médico",       # 2
            "Exame",        # 3
            "Dose (mGy)",   # 4
            "Tempo",        # 5
            "DAP",          # 6
            "ID Paciente",  # 7
            "Sexo",         # 8
            "Sala"          # 9
        ]
        
        # 2. Definição da Ordem Exata (SQL) - TEM QUE BATER COM O HEADER ACIMA
        campos_sql = "rowid, data, medico, exam, dose_mgy, tempo, dap, paciente_id, sexo, sala"

        if apenas_filtrados and inputs_filtros:
            sql_where, params = montar_query_filtros(
                data_inicio, data_final, 
                inputs_filtros['min_d'], inputs_filtros['max_d'], 
                inputs_filtros['med'], inputs_filtros['exm'], 
                inputs_filtros['min_t'], inputs_filtros['max_t'], 
                inputs_filtros['min_dap'], inputs_filtros['max_dap'], 
                inputs_filtros['sala'], inputs_filtros['sexo'], 
                inputs_filtros['id_pac']
            )
            sql = f"SELECT {campos_sql} {sql_where} ORDER BY data DESC"
            cursor.execute(sql, params)
        else:
            sql = f"SELECT {campos_sql} FROM exames ORDER BY data DESC"
            cursor.execute(sql)
            
        dados = cursor.fetchall()
        conn.close()

        # 3. Criação do CSV
        output = io.StringIO()
        
        # QUOTE_ALL: Coloca aspas em TUDO (ex: "Médico A; Médico B") para o Excel não dividir errado
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_ALL)
        
        # Escreve o Cabeçalho
        writer.writerow(colunas_header)
        
        # Escreve os Dados linha a linha
        for row in dados:
            # row[0]=id, row[1]=data, row[2]=medico, row[3]=exame, row[4]=dose, 
            # row[5]=tempo, row[6]=dap, row[7]=paciente, row[8]=sexo, row[9]=sala
            
            linha = list(row)
            
            # Formatações Específicas
            linha[1] = formatar_data(linha[1])  # Formata Data (índice 1)
            linha[5] = formatar_tempo(linha[5]) # Formata Tempo (índice 5)
            
            # Tratamento de números para Excel BR (Ponto vira Vírgula)
            # Dose (índice 4)
            if linha[4]: linha[4] = str(linha[4]).replace('.', ',')
            # DAP (índice 6)
            if linha[6]: linha[6] = str(linha[6]).replace('.', ',')
            
            writer.writerow(linha)
            
        return output.getvalue()

    except Exception as e:
        print(f"Erro CSV: {e}")
        return ""


# ==============================================================================
#                           ANÁLISE DE DADOS (KPIS)
# ==============================================================================

# --- FUNÇÕES DE CÁLCULO ---

def calcular_evolucao_temporal(data_inicio, data_fim, min_d, max_d, n_medico, exm, min_tempo, max_tempo, min_dap, max_dap, sala, sexo, id_pac):
    modo_multiplo = False
    if n_medico and ";" in str(n_medico):
        modo_multiplo = True

    try:
        conn = conectar()
        if conn is None: return [], modo_multiplo
        cursor = conn.cursor()
        sql_where, params = montar_query_filtros(data_inicio, data_fim, min_d, max_d, n_medico, exm, min_tempo, max_tempo, min_dap, max_dap, sala, sexo, id_pac)
        
        if modo_multiplo:
            sql = f"SELECT date(data), medico, COUNT(*) {sql_where} GROUP BY date(data), medico ORDER BY date(data)"
        else:
            sql = f"SELECT date(data), COUNT(*) {sql_where} GROUP BY date(data) ORDER BY date(data)"
            
        cursor.execute(sql, params)
        res = cursor.fetchall()
        conn.close()

        # --- A MÁGICA DOS DIAS ZERADOS COMEÇA AQUI ---
        if not res: 
            return [], modo_multiplo

        # 1. Descobre o primeiro e o último dia do resultado
        datas = [r[0] for r in res]
        str_inicio = min(datas)
        str_fim = max(datas)

        d_inicio = datetime.datetime.strptime(str_inicio, "%Y-%m-%d").date()
        d_fim = datetime.datetime.strptime(str_fim, "%Y-%m-%d").date()

        # 2. Cria uma lista contínua com TODOS os dias entre o início e o fim
        todas_datas = []
        delta = d_fim - d_inicio
        for i in range(delta.days + 1):
            dia = d_inicio + datetime.timedelta(days=i)
            todas_datas.append(dia.strftime("%Y-%m-%d"))

        res_preenchido = []
        
        if not modo_multiplo:
            # Transforma o resultado do banco num dicionário de fácil acesso { '2026-02-10': 5 }
            mapa_dados = {r[0]: r[1] for r in res}
            
            for d in todas_datas:
                # Se o dia existir no dicionário, pega o valor, senão é 0
                res_preenchido.append((d, mapa_dados.get(d, 0)))
        else:
            # Dicionário para cada médico { 'Dr. A': {'2026-02-10': 5} }
            medicos = list(set([r[1] for r in res]))
            mapa_dados = {m: {} for m in medicos}
            
            for r in res:
                mapa_dados[r[1]][r[0]] = r[2] # r[1]=medico, r[0]=data, r[2]=qtd
                
            for d in todas_datas:
                for m in medicos:
                    # Distribui as datas e garante os zeros onde os médicos não trabalharam
                    res_preenchido.append((d, m, mapa_dados[m].get(d, 0)))

        return res_preenchido, modo_multiplo
        
    except Exception as e:
        print(f"Erro Evolução: {e}")
        return [], False

def calcular_media_medico(data_inicio, data_fim, min_d, max_d, n_medico, exm, min_tempo, max_tempo, min_dap, max_dap, sala, sexo, id_pac):
    resultados = []
    try:
        conn = conectar()
        cursor = conn.cursor()
        sql_where, params = montar_query_filtros(data_inicio, data_fim, min_d, max_d, n_medico, exm, min_tempo, max_tempo, min_dap, max_dap, sala, sexo, id_pac)
        
        sql_media = f"""
            SELECT 
                medico, 
                AVG(CAST(REPLACE(dose_mgy, ',', '.') AS REAL)) as media_dose,
                MIN(CAST(REPLACE(dose_mgy, ',', '.') AS REAL)) as min_dose,
                MAX(CAST(REPLACE(dose_mgy, ',', '.') AS REAL)) as max_dose,
                COUNT(*) as qtd
            {sql_where} 
            GROUP BY medico 
            ORDER BY media_dose DESC
        """
        cursor.execute(sql_media, params)
        resultados = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"Erro SQL Media: {e}")
    return resultados

def calcular_media_tempo_medico(data_inicio, data_fim, min_d, max_d, n_medico, exm, min_tempo, max_tempo, min_dap, max_dap, sala, sexo, id_pac):
    try:
        conn = conectar()
        if not conn: return []
        cursor = conn.cursor()
        
        sql_where, params = montar_query_filtros(data_inicio, data_fim, min_d, max_d, n_medico, exm, min_tempo, max_tempo, min_dap, max_dap, sala, sexo, id_pac)
        
        # Fórmula SQL para converter "HH:MM:SS" em Minutos (float)
        # substr(tempo, 1, 2) = Horas
        # substr(tempo, 4, 2) = Minutos
        # substr(tempo, 7, 2) = Segundos
        calc_minutos = "(CAST(substr(tempo, 1, 2) AS INTEGER) * 60 + CAST(substr(tempo, 4, 2) AS INTEGER) + CAST(substr(tempo, 7, 2) AS REAL)/60)"

        sql = f"""
            SELECT 
                medico, 
                AVG({calc_minutos}) as media,
                MIN({calc_minutos}) as minimo,
                MAX({calc_minutos}) as maximo,
                COUNT(*) as qtd
            {sql_where}
            GROUP BY medico
            ORDER BY media DESC
        """
        
        cursor.execute(sql, params)
        resultados = cursor.fetchall()
        conn.close()
        
        # Retorna lista no formato: [(Medico, Media, Min, Max, Qtd), ...]
        return resultados

    except Exception as e:
        print(f"Erro Media Tempo SQL: {e}")
        return []
def calcular_media_exame(data_inicio, data_fim, min_d, max_d, n_medico, exm, min_tempo, max_tempo, min_dap, max_dap, sala, sexo, id_pac):
    resultados = []
    modo_multiplo = False
    
    if n_medico and ";" in str(n_medico):
        modo_multiplo = True

    try:
        conn = conectar()
        cursor = conn.cursor()
        sql_where, params = montar_query_filtros(data_inicio, data_fim, min_d, max_d, n_medico, exm, min_tempo, max_tempo, min_dap, max_dap, sala, sexo, id_pac)
        
        if modo_multiplo:
            sql_media = f"""
                SELECT 
                    exam, medico, 
                    AVG(CAST(REPLACE(dose_mgy, ',', '.') AS REAL)) as media_dose,
                    MIN(CAST(REPLACE(dose_mgy, ',', '.') AS REAL)) as min_dose,
                    MAX(CAST(REPLACE(dose_mgy, ',', '.') AS REAL)) as max_dose,
                    COUNT(*) as qtd
                {sql_where}
                GROUP BY exam, medico
                ORDER BY exam
            """
        else:
            sql_media = f"""
                SELECT 
                    exam, 
                    AVG(CAST(REPLACE(dose_mgy, ',', '.') AS REAL)) as media_dose,
                    MIN(CAST(REPLACE(dose_mgy, ',', '.') AS REAL)) as min_dose,
                    MAX(CAST(REPLACE(dose_mgy, ',', '.') AS REAL)) as max_dose,
                    COUNT(*) as qtd
                {sql_where}
                GROUP BY exam
                ORDER BY media_dose DESC
            """ #LIMIT 6 (adicione isso se quiser  limitar o grafico a um TOP 6)
            
        cursor.execute(sql_media, params)
        resultados = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"Erro SQL Media Exame: {e}")
        
    return resultados, modo_multiplo

def calcular_media_tempo_exame(data_inicio, data_fim, min_d, max_d, n_medico, exm, min_tempo, max_tempo, min_dap, max_dap, sala, sexo, id_pac):
    modo_multiplo = False
    if n_medico and ";" in str(n_medico):
        modo_multiplo = True

    try:
        conn = conectar()
        if not conn: return [], modo_multiplo
        cursor = conn.cursor()
        
        sql_where, params = montar_query_filtros(data_inicio, data_fim, min_d, max_d, n_medico, exm, min_tempo, max_tempo, min_dap, max_dap, sala, sexo, id_pac)
        
        # A mesma fórmula mágica de antes
        calc_minutos = "(CAST(substr(tempo, 1, 2) AS INTEGER) * 60 + CAST(substr(tempo, 4, 2) AS INTEGER) + CAST(substr(tempo, 7, 2) AS REAL)/60)"

        if modo_multiplo:
            # Agrupa por Exame E Médico
            sql = f"""
                SELECT 
                    exam, 
                    medico, 
                    AVG({calc_minutos}) as media,
                    MIN({calc_minutos}) as minimo,
                    MAX({calc_minutos}) as maximo,
                    COUNT(*) as qtd
                {sql_where}
                GROUP BY exam, medico
                ORDER BY exam
            """
        else:
            # Agrupa apenas por Exame
            sql = f"""
                SELECT 
                    exam, 
                    AVG({calc_minutos}) as media,
                    MIN({calc_minutos}) as minimo,
                    MAX({calc_minutos}) as maximo,
                    COUNT(*) as qtd
                {sql_where}
                GROUP BY exam
                ORDER BY media DESC
            """ # Adicione LIMIT 6 aqui se quiser pegar apenas os top 6 exames mais demorados
            
        cursor.execute(sql, params)
        resultados = cursor.fetchall()
        conn.close()

        return resultados, modo_multiplo

    except Exception as e:
        print(f"Erro Media Tempo Exame SQL: {e}")
        return [], False

# --- CRUD FUNCTIONS ---
def inserir_exame(dados):
    try:
        conn = conectar()
        cursor = conn.cursor()
        sql_create = """CREATE TABLE IF NOT EXISTS exames (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            medico TEXT,
            exam TEXT,
            dose_mgy TEXT,
            tempo TEXT,
            dap TEXT,
            paciente_id TEXT,
            sexo TEXT,
            sala TEXT
        )"""
        cursor.execute(sql_create)
        sql = """INSERT INTO exames (data, medico, exam, dose_mgy, tempo, dap, paciente_id, sexo, sala) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        cursor.execute(sql, dados)
        conn.commit()
        conn.close()
        return True
    except Exception as e: print(f"Erro Insert: {e}"); return False

def deletar_exame(id_row):
    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM exames WHERE rowid = ?", (id_row,))
        if cursor.rowcount == 0: conn.close(); return False 
        conn.commit(); conn.close(); return True
    except Exception as e: print(f"Erro Delete: {e}"); return False

def buscar_exame_por_id(id_row):
    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT data, medico, exam, dose_mgy, tempo, dap, paciente_id, sexo, sala FROM exames WHERE rowid = ?", (id_row,))
        dados = cursor.fetchone(); conn.close(); return dados
    except Exception as e: print(f"Erro Busca ID: {e}"); return None

def atualizar_exame(id_row, dados):
    try:
        conn = conectar()
        cursor = conn.cursor()
        sql = """UPDATE exames SET data=?, medico=?, exam=?, dose_mgy=?, tempo=?, dap=?, paciente_id=?, sexo=?, sala=? WHERE rowid=?"""
        params = list(dados); params.append(id_row)
        cursor.execute(sql, params); conn.commit(); conn.close(); return True
    except Exception as e: print(f"Erro Update: {e}"); return False

# --- GERENCIAMENTO DE TIPOS DE EXAMES ---

def inicializar_tipos_exames():
    """Cria a tabela e popula com os padrões se estiver vazia"""
    padroes = []
    try:
        conn = conectar()
        if not conn: return padroes    
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS tipos_exames (nome TEXT PRIMARY KEY)")
        
        # Verifica se está vazia
        cursor.execute("SELECT COUNT(*) FROM tipos_exames")
        if cursor.fetchone()[0] == 0:
            for item in padroes:
                cursor.execute("INSERT INTO tipos_exames (nome) VALUES (?)", (item,))
            conn.commit()
        
        # Retorna a lista atualizada
        cursor.execute("SELECT nome FROM tipos_exames ORDER BY nome")
        lista = [r[0] for r in cursor.fetchall()]
        conn.close()
        return lista
    except Exception as e:
        print(f"Erro init exames: {e}")
        return padroes

def adicionar_tipo_exame_db(novo_nome):
    try:
        conn = conectar()
        if not conn: return False 
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tipos_exames (nome) VALUES (?)", (novo_nome.upper(),))
        conn.commit()
        conn.close()
        return True
    except Exception as e: return False

def remover_tipo_exame_db(nome):
    try:
        conn = conectar()
        if not conn: return False 
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tipos_exames WHERE nome = ?", (nome,))
        conn.commit()
        conn.close()
        return True
    except Exception as e: return False


# --- GERENCIAMENTO DE TIPOS DE EQUIPAMENTO S/N ---

def inicializar_equipamento():
    """Cria a tabela e popula com os padrões se estiver vazia"""
    padroes = []
    try:
        conn = conectar()
        if not conn: return padroes    
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS tipos_equipamento (nome TEXT PRIMARY KEY)")
        
        # Verifica se está vazia
        cursor.execute("SELECT COUNT(*) FROM tipos_equipamento")
        if cursor.fetchone()[0] == 0:
            for item in padroes:
                cursor.execute("INSERT INTO tipos_equipamento (nome) VALUES (?)", (item,))
            conn.commit()
        
        # Retorna a lista atualizada
        cursor.execute("SELECT nome FROM tipos_equipamento ORDER BY nome")
        lista = [r[0] for r in cursor.fetchall()]
        conn.close()
        return lista
    except Exception as e:
        print(f"Erro init equipamento: {e}")
        return padroes

def adicionar_tipo_equipamento_db(novo_nome):
    try:
        conn = conectar()
        if not conn: return False 
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tipos_equipamento (nome) VALUES (?)", (novo_nome,))
        conn.commit()
        conn.close()
        return True
    except Exception as e: return False

def remover_tipo_equipamento_db(nome):
    try:
        conn = conectar()
        if not conn: return False 
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tipos_equipamento WHERE nome = ?", (nome,))
        conn.commit()
        conn.close()
        return True
    except Exception as e: return False

# ==============================================================================
#                           INTERFACE GRÁFICA (FLET)
# ==============================================================================

def main(page: ft.Page):
    page.title = "OpenZoe - Gerenciador de Radiologia"

    # Função para alterar entre modo claro e escuro
    def toggle_tema(e):
        page.theme_mode = ft.ThemeMode.LIGHT if page.theme_mode == ft.ThemeMode.DARK else ft.ThemeMode.DARK
        btn_tema.icon = ft.Icons.DARK_MODE if page.theme_mode == ft.ThemeMode.LIGHT else ft.Icons.LIGHT_MODE
        page.update()

    # --- HANDLERS (SELEÇÃO DE ARQUIVOS) ---

    async def handle_pick_files(e: ft.Event[ft.Button]):
        global FILE_PATH
        files = await ft.FilePicker().pick_files(allow_multiple=True)
        if files:
            FILE_PATH = files[0].path
            conn = conectar()
            cursor = conn.cursor()
            sql_create = """CREATE TABLE IF NOT EXISTS exames (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT,
                medico TEXT,
                exam TEXT,
                dose_mgy TEXT,
                tempo TEXT,
                dap TEXT,
                paciente_id TEXT,
                sexo TEXT,
                sala TEXT
            )"""
            inicializar_tipos_exames() 
            inicializar_equipamento()
            atualizar_dropdowns_globais()
            cursor.execute(sql_create)
            conn.commit()
            conn.close()
            criar_indices()
            atualizar_tudo()
            page.show_dialog(ft.SnackBar(ft.Text(f"Arquivo Selecionado: {FILE_PATH}"), bgcolor="green"))
        else:
            page.update()

    async def handle_get_directory_path_evolucao(e: ft.Event[ft.Button]):
        global directory_path
        directory_path = await ft.FilePicker().get_directory_path()
        if directory_path:
            salvar_grafico_evolucao()
        else:
            page.update()

    async def handle_get_directory_path_dose_medico(e: ft.Event[ft.Button]):
        global directory_path
        directory_path = await ft.FilePicker().get_directory_path()
        if directory_path:
            salvar_grafico_dose_medico()
        else:
            page.update()

    async def handle_get_directory_path_tempo_medico(e: ft.Event[ft.Button]):
        global directory_path
        directory_path = await ft.FilePicker().get_directory_path()
        if directory_path:
            salvar_grafico_tempo_medico()
        else:
            page.update()

    async def handle_get_directory_path_dose_exame(e: ft.Event[ft.Button]):
        global directory_path
        directory_path = await ft.FilePicker().get_directory_path()
        if directory_path:
            salvar_grafico_dose_exame()
        else:
            page.update()

    async def handle_get_directory_path_tempo_exame(e: ft.Event[ft.Button]):
        global directory_path
        directory_path = await ft.FilePicker().get_directory_path()
        if directory_path:
            salvar_grafico_tempo_exame()
        else:
            page.update()
 
    async def handle_get_directory_path_upload(e: ft.Event[ft.Button]):
        global upload_path
        upload_path = await ft.FilePicker().get_directory_path()
        if upload_path:
            upload_exames()
        else:
            page.update()

    # --- handle CSV ---

    async def exportar_csv_completo(e: ft.Event[ft.Button]):
        texto_csv = gerar_csv_string(apenas_filtrados=False)
        nome_arquivo = f"Relatorio_Completo_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
        resultado = await ft.FilePicker().save_file(file_name=nome_arquivo, allowed_extensions=["csv"])
        
        if resultado:
            try:
                with open(resultado, 'w', newline='', encoding='utf-8-sig') as f:
                    f.write(texto_csv)
                page.show_dialog(ft.SnackBar(ft.Text("Relatório completo salvo!"), bgcolor="green"))
            except Exception as ex:
                page.show_dialog(ft.SnackBar(ft.Text(f"Erro: {ex}"), bgcolor="red"))

    async def exportar_csv_filtrado(e: ft.Event[ft.Button]):
        filtros_atuais = {
            'min_d': min_dose.value, 'max_d': max_dose.value,
            'med': medico_entry.value, 'exm': exame_entry.value,
            'min_t': min_tempo_entry.value, 'max_t': max_tempo_entry.value,
            'min_dap': min_dap_entry.value, 'max_dap': max_dap_entry.value,
            'sala': sala_entry.value, 'sexo': sexo_entry.value,
            'id_pac': id_paciente_entry.value
        }
        
        texto_csv = gerar_csv_string(apenas_filtrados=True, inputs_filtros=filtros_atuais)
        
        if not texto_csv:
             page.show_dialog(ft.SnackBar(ft.Text("Sem dados com esses filtros."), bgcolor="orange")); return

        nome_arquivo = f"Relatorio_Filtrado_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
        
        # LÓGICA ASYNC
        resultado = await ft.FilePicker().save_file(file_name=nome_arquivo, allowed_extensions=["csv"])   
        if resultado:
            try:
                with open(resultado, 'w', newline='', encoding='utf-8-sig') as f:
                    f.write(texto_csv)
                page.show_dialog(ft.SnackBar(ft.Text("Relatório filtrado salvo!"), bgcolor="green"))
            except Exception as ex:
                page.show_dialog(ft.SnackBar(ft.Text(f"Erro: {ex}"), bgcolor="red"))

    # --- Hendler Para montar Relatório (PDF) ---

    async def exportar_pdf_filtrado(e: ft.Event[ft.Button]):
        v_min, v_max = min_dose.value, max_dose.value
        v_min_t, v_max_t = min_tempo_entry.value, max_tempo_entry.value
        v_min_dap, v_max_dap = min_dap_entry.value, max_dap_entry.value
        v_med, v_exm, v_sala = medico_entry.value, exame_entry.value, sala_entry.value
        v_sexo, v_id_pac = sexo_entry.value, id_paciente_entry.value

        nome_sugerido = f"Relatorio_Dosimetria_{datetime.datetime.now().strftime('%Y%m%d')}.pdf"
        filepath = await ft.FilePicker().save_file(file_name=nome_sugerido, allowed_extensions=["pdf"])
        if not filepath: return

        try:
            conn = conectar()
            cursor = conn.cursor()
            sql_where, params = montar_query_filtros(data_inicio, data_final, v_min, v_max, v_med, v_exm, v_min_t, v_max_t, v_min_dap, v_max_dap, v_sala, v_sexo, v_id_pac)

            # Busca os Top 10 e Total de Exames
            cursor.execute(f"SELECT data, medico, exam, dose_mgy, tempo {sql_where} ORDER BY CAST(REPLACE(dose_mgy, ',', '.') AS REAL) DESC LIMIT 10", params)
            top10_dados = cursor.fetchall()
            
            cursor.execute(f"SELECT COUNT(*) {sql_where}", params)
            total_exames = cursor.fetchone()[0]
            conn.close()

            # --- INICIALIZA O PDF E CABEÇALHOS ---
            pdf = RelatorioPDF()
            pdf.add_page()
            
            pdf.set_font("helvetica", "B", 12)
            pdf.cell(0, 8, "Filtros Aplicados:", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("helvetica", "", 10)
            pdf.cell(0, 6, f"Período: {data_inicio if data_inicio else 'Início'} a {data_final if data_final else 'Hoje'}", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 6, f"Médico(s): {v_med if v_med else 'Todos'}", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 6, f"Exame: {v_exm if v_exm else 'Todos'}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(5)

            # --- O AJUDANTE QUE REAPROVEITA SUAS FUNÇÕES ---
            def colocar_grafico_no_pdf(funcao_grafico):
                # Cria um arquivo temporário vazio
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
                
                # Chama SUA função passando o caminho oculto
                gerou_com_sucesso = funcao_grafico(caminho_oculto=temp_file) 
                
                if gerou_com_sucesso:
                    if pdf.get_y() > 200: pdf.add_page() # Evita cortar o gráfico
                    pdf.image(temp_file, w=180)
                    pdf.ln(5)
                
                if os.path.exists(temp_file): os.unlink(temp_file) # Limpa o lixo

            # --- REGRAS INTELIGENTES ---
            unico_dia = bool(data_inicio and data_final and data_inicio == data_final)
            unico_medico = bool(v_med and ";" not in v_med)

            if unico_dia:
                pdf.set_font("helvetica", "B", 14)
                pdf.set_text_color(0, 100, 0)
                dfmt = data_inicio[8:10] + "/" + data_inicio[5:7] + "/" + data_inicio[0:4]
                pdf.cell(0, 10, f"Total de Exames no dia {dfmt}: {total_exames}", new_x="LMARGIN", new_y="NEXT", align="C")
                pdf.set_text_color(0, 0, 0); pdf.ln(5)
            else:
                colocar_grafico_no_pdf(salvar_grafico_evolucao)

            if not unico_medico:
                colocar_grafico_no_pdf(salvar_grafico_dose_medico)
                colocar_grafico_no_pdf(salvar_grafico_tempo_medico)

            colocar_grafico_no_pdf(salvar_grafico_dose_exame)
            colocar_grafico_no_pdf(salvar_grafico_tempo_exame)

            # --- TABELA DE TOP 10 ---
            if pdf.get_y() > 200: pdf.add_page()
            pdf.set_font("helvetica", "B", 12)
            pdf.cell(0, 10, "Atenção: Top 10 Maiores Doses no Período", new_x="LMARGIN", new_y="NEXT")
            
            pdf.set_font("helvetica", "B", 10); pdf.set_fill_color(200, 200, 200)
            pdf.cell(30, 8, "Data", border=1, fill=True); pdf.cell(50, 8, "Médico", border=1, fill=True)
            pdf.cell(60, 8, "Exame", border=1, fill=True); pdf.cell(25, 8, "Dose", border=1, fill=True)
            pdf.cell(25, 8, "Tempo", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

            pdf.set_font("helvetica", "", 9)
            for row in top10_dados:
                ds = str(row[3]) if row[3] else "0.0"
                pdf.cell(30, 8, str(row[0]).split()[0] if row[0] else "N/A", border=1)
                pdf.cell(50, 8, str(row[1])[:20] if row[1] else "N/A", border=1)
                pdf.cell(60, 8, str(row[2])[:25] if row[2] else "N/A", border=1)
                
                try:
                    if float(ds.replace(',', '.')) > 3000:
                        pdf.set_text_color(200, 0, 0); pdf.set_font("helvetica", "B", 9)
                except: pass
                
                pdf.cell(25, 8, ds, border=1)
                pdf.set_text_color(0, 0, 0); pdf.set_font("helvetica", "", 9)
                pdf.cell(25, 8, str(row[4])[:8] if row[4] else "N/A", border=1, new_x="LMARGIN", new_y="NEXT")

            pdf.output(filepath)
            page.show_dialog(ft.SnackBar(ft.Text("Relatório PDF gerado com sucesso!"), bgcolor="green"))

        except Exception as err:
            page.show_dialog(ft.SnackBar(ft.Text(f"Erro ao gerar PDF: {err}"), bgcolor="red"))

    # --- FUNÇÕES PARA SALVAR GRÁFICOS (MATPLOTLIB) ---
    def salvar_grafico_evolucao(caminho_oculto=None):
        global directory_path
        try:
            # 1. Busca os dados e o modo
            resultado = calcular_evolucao_temporal(data_inicio, data_final, min_dose.value, max_dose.value, 
                                                   medico_entry.value, exame_entry.value, min_tempo_entry.value, 
                                                   max_tempo_entry.value, min_dap_entry.value, max_dap_entry.value, sala_entry.value, sexo_entry.value, id_paciente_entry.value)
            
            dados = resultado[0]
            modo_multiplo = resultado[1]

            if not dados:
                if not caminho_oculto: # 2. Só mostra o erro vermelho se NÃO for o PDF chamando
                    page.show_dialog(ft.SnackBar(ft.Text("Sem dados para salvar!"), bgcolor="red"))        
                    page.update()
                return False

            plt.figure(figsize=(12, 6)) # Aumentei um pouco a largura

            if not modo_multiplo:
                # --- MODO SIMPLES ---
                eixo_x = [d[0] for d in dados] 
                eixo_y = [d[1] for d in dados]
                plt.plot(eixo_x, eixo_y, marker='o', linestyle='-', color='b')
            else:
                # --- MODO MÚLTIPLO ---
                datas_unicas = sorted(list(set(d[0] for d in dados)))
                medicos_unicos = sorted(list(set(d[1] for d in dados)))

                mapa_dados = {med: {d: 0 for d in datas_unicas} for med in medicos_unicos}
                for r in dados:
                    mapa_dados[r[1]][r[0]] = r[2]

                cores = plt.cm.tab10.colors 
                for i, medico in enumerate(medicos_unicos):
                    y_vals = [mapa_dados[medico][d] for d in datas_unicas]
                    plt.plot(datas_unicas, y_vals, marker='o', linestyle='-', label=medico, color=cores[i % len(cores)])

                plt.legend(title="Médicos") # Mostra a legenda de cores

            plt.title("Evolução Temporal de Exames")
            plt.xlabel("Data")
            plt.ylabel("Quantidade")
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.xticks(rotation=45, fontsize=8) 
            plt.tight_layout() 

            if caminho_oculto:
                plt.savefig(caminho_oculto, dpi=150) # Salva qualidade média pro PDF
                plt.close()
                return True

            agora = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") 
            nome_arquivo = fr"{directory_path}/evolucao_{agora}.png"
            plt.savefig(nome_arquivo, dpi=300) 
            plt.close()

            page.show_dialog(ft.SnackBar(ft.Text(f"Salvo como: {os.path.basename(nome_arquivo)}"), bgcolor="green"))
            page.update()

        except Exception as err:
            print(err)
            page.show_dialog(ft.SnackBar(ft.Text(f"Erro ao salvar: {err}"), bgcolor="red"))
            page.update()

    def salvar_grafico_dose_medico(caminho_oculto=None):
        global directory_path
        try:
            # 1. Busca os mesmos dados que o gráfico usa
            dados = calcular_media_medico(data_inicio, data_final, min_dose.value, max_dose.value, 
                                             medico_entry.value, exame_entry.value, min_tempo_entry.value, 
                                             max_tempo_entry.value, min_dap_entry.value, max_dap_entry.value, sala_entry.value, sexo_entry.value, id_paciente_entry.value)
            
            if not dados:
                if not caminho_oculto: # 2. Só mostra o erro vermelho se NÃO for o PDF chamando
                    page.show_dialog(ft.SnackBar(ft.Text("Sem dados para salvar!"), bgcolor="red"))        
                    page.update()
                return False

            # 2. Separa X e Y
            # Datas vêm como "YYYY-MM-DD", vamos formatar para "DD/MM"
            #eixo_x = [d[0][5:].replace("-", "/") for d in dados] 
            eixo_x = [d[0] for d in dados] 
            eixo_y = [d[1] for d in dados]

            # 3. Cria a figura com Matplotlib (Back-end)
            plt.figure(figsize=(10, 6)) # Tamanho da imagem

            plt.axhline(y=1000, color='#8F00FF', linestyle='--', linewidth=2)
            plt.axhline(y=2000, color='blue', linestyle='--', linewidth=2)
            plt.axhline(y=3000, color='yellow', linestyle='--', linewidth=2)
            plt.axhline(y=4000, color='orange', linestyle='--', linewidth=2)
            plt.axhline(y=5000, color='red', linestyle='--', linewidth=2)
            plt.bar(eixo_x, eixo_y, color='b')
            
            plt.title("Média de Dose por médico ")
            plt.xlabel("Médico")
            plt.ylabel("Dose média")
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.xticks(rotation=45) # Gira as datas para caber
            plt.tight_layout() # Ajusta margens

            if caminho_oculto:
                plt.savefig(caminho_oculto, dpi=150) # Salva qualidade média pro PDF
                plt.close()
                return True

            # 4. Salva o arquivo
            agora = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f"{directory_path}/Dose_medico_{agora}.png"
            plt.savefig(nome_arquivo, dpi=300) 
            plt.close() # 

            # 5. Feedback
            page.show_dialog(ft.SnackBar(ft.Text(f"Salvo como: {nome_arquivo}"), bgcolor="green"))
            page.update()

        except Exception as err:
            print(err)
            page.show_dialog(ft.SnackBar(ft.Text(f"Erro ao salvar: {err}"), bgcolor="red"))
            page.update()

    def salvar_grafico_tempo_medico(caminho_oculto=None):
        global directory_path
        try:
            # 1. Busca os mesmos dados que o gráfico usa
            dados = calcular_media_tempo_medico(data_inicio, data_final, min_dose.value, max_dose.value, 
                                             medico_entry.value, exame_entry.value, min_tempo_entry.value, 
                                             max_tempo_entry.value, min_dap_entry.value, max_dap_entry.value, sala_entry.value, sexo_entry.value, id_paciente_entry.value)
            
            if not dados:
                if not caminho_oculto: # 2. Só mostra o erro vermelho se NÃO for o PDF chamando
                    page.show_dialog(ft.SnackBar(ft.Text("Sem dados para salvar!"), bgcolor="red"))        
                    page.update()
                return False

            # 2. Separa X e Y
            # Datas vêm como "YYYY-MM-DD", vamos formatar para "DD/MM"
            #eixo_x = [d[0][5:].replace("-", "/") for d in dados] 
            eixo_x = [d[0] for d in dados] 
            eixo_y = [d[1] for d in dados]

            # 3. Cria a figura com Matplotlib (Back-end)
            plt.figure(figsize=(10, 6)) # Tamanho da imagem
            plt.bar(eixo_x, eixo_y, color='b')
            
            plt.title("Média de Tempo por médico ")
            plt.xlabel("Médico")
            plt.ylabel("Tempo médio")
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.xticks(rotation=45) # Gira as datas para caber
            plt.tight_layout() # Ajusta margens

            if caminho_oculto:
                plt.savefig(caminho_oculto, dpi=150) # Salva qualidade média pro PDF
                plt.close()
                return True

            # 4. Salva o arquivo
            agora = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f"{directory_path}/Tempo_medico_{agora}.png"
            plt.savefig(nome_arquivo, dpi=300) 
            plt.close() 

            # 5. Feedback
            page.show_dialog(ft.SnackBar(ft.Text(f"Salvo como: {nome_arquivo}"), bgcolor="green"))
            page.update()

        except Exception as err:
            print(err)
            page.show_dialog(ft.SnackBar(ft.Text(f"Erro ao salvar: {err}"), bgcolor="red"))
            page.update()

    def salvar_grafico_dose_exame(caminho_oculto=None):
        global directory_path
        try:
            # 1. Busca os dados e o modo
            resultado = calcular_media_exame(data_inicio, data_final, min_dose.value, max_dose.value, 
                                         medico_entry.value, exame_entry.value, min_tempo_entry.value, 
                                         max_tempo_entry.value, min_dap_entry.value, max_dap_entry.value, sala_entry.value, sexo_entry.value, id_paciente_entry.value)
            
            dados = resultado[0]
            modo_multiplo = resultado[1]
            
            if not dados:
                if not caminho_oculto: # 2. Só mostra o erro vermelho se NÃO for o PDF chamando
                    page.show_dialog(ft.SnackBar(ft.Text("Sem dados para salvar!"), bgcolor="red"))        
                    page.update()
                return False

            plt.figure(figsize=(12, 6))

            plt.axhline(y=1000, color='#8F00FF', linestyle='--', linewidth=2)
            plt.axhline(y=2000, color='blue', linestyle='--', linewidth=2)
            plt.axhline(y=3000, color='yellow', linestyle='--', linewidth=2)
            plt.axhline(y=4000, color='orange', linestyle='--', linewidth=2)
            plt.axhline(y=5000, color='red', linestyle='--', linewidth=2)
            #plt.legend()

            if not modo_multiplo:
                # --- MODO SIMPLES ---
                eixo_x = [d[0] for d in dados] 
                eixo_y = [d[1] for d in dados]
                plt.bar(eixo_x, eixo_y, color='b')
                plt.xlabel("Exame")
            
            else:
                # --- MODO MÚLTIPLO (BARRAS AGRUPADAS) ---
                # 1. Identificar Exames e Médicos únicos
                exames = sorted(list(set(d[0] for d in dados)))
                medicos = sorted(list(set(d[1] for d in dados)))
                
                # 2. Criar posições no eixo X
                n_exames = len(exames)
                n_medicos = len(medicos)
                largura_barra = 0.8 / n_medicos # Largura dinâmica
                posicoes = list(range(n_exames))
                
                # 3. Mapear dados para acesso rápido: dados_map[exame][medico] = valor
                dados_map = {ex: {} for ex in exames}
                for row in dados:
                    dados_map[row[0]][row[1]] = row[2] 

                # 4. Plotar uma série de barras para cada médico
                # Cores para diferenciar (ciclando cores padrão do matplotlib)
                cores = plt.cm.tab10.colors 

                for i, medico in enumerate(medicos):
                    valores = []
                    for exame in exames:
                        valores.append(dados_map[exame].get(medico, 0))
                    pos_deslocada = [p + (i * largura_barra) for p in posicoes]
                    
                    plt.bar(pos_deslocada, valores, width=largura_barra, label=medico, color=cores[i % len(cores)])

                # 5. Ajustar rótulos do eixo X para ficarem no centro do grupo
                centro_grupo = [p + largura_barra * (n_medicos - 1) / 2 for p in posicoes]
                plt.xticks(centro_grupo, exames, rotation=45)
                plt.legend(title="Médicos") # Adiciona legenda
                plt.xlabel("Exame")

            # Configurações Comuns
            plt.title("Média de Dose por Exame")
            plt.ylabel("Dose média (mGy)")
            plt.grid(True, linestyle='--', alpha=0.7, axis='y')
            plt.tight_layout() 

            if caminho_oculto:
                plt.savefig(caminho_oculto, dpi=150) # Salva qualidade média pro PDF
                plt.close()
                return True

            # Salvar
            nome_arquivo = f"{directory_path}/Dose_exame_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(nome_arquivo, dpi=300)
            plt.close() 

            page.show_dialog(ft.SnackBar(ft.Text(f"Salvo como: {os.path.basename(nome_arquivo)}"), bgcolor="green"))
            page.update()

        except Exception as err:
            print(err)
            page.show_dialog(ft.SnackBar(ft.Text(f"Erro ao salvar: {err}"), bgcolor="red"))
            page.update()

    def salvar_grafico_tempo_exame(caminho_oculto=None):
        global directory_path
        try:
            # 1. Busca os dados e o modo
            resultado = calcular_media_tempo_exame(data_inicio, data_final, min_dose.value, max_dose.value, 
                                         medico_entry.value, exame_entry.value, min_tempo_entry.value, 
                                         max_tempo_entry.value, min_dap_entry.value, max_dap_entry.value, sala_entry.value, sexo_entry.value, id_paciente_entry.value)
            
            dados = resultado[0]
            modo_multiplo = resultado[1]
            
            if not dados:
                if not caminho_oculto: # 2. Só mostra o erro vermelho se NÃO for o PDF chamando
                    page.show_dialog(ft.SnackBar(ft.Text("Sem dados para salvar!"), bgcolor="red"))        
                    page.update()
                return False

            plt.figure(figsize=(12, 6))

            if not modo_multiplo:
                # Modo Simples: 
                eixo_x = [d[0] for d in dados] 
                eixo_y = [d[1] for d in dados]
                plt.bar(eixo_x, eixo_y, color='orange')
                plt.xlabel("Exame")
            
            else:
                # Modo Múltiplo:
                exames = sorted(list(set(d[0] for d in dados)))
                medicos = sorted(list(set(d[1] for d in dados)))
                
                n_exames = len(exames); n_medicos = len(medicos)
                largura_barra = 0.8 / n_medicos
                posicoes = list(range(n_exames))
                
                dados_map = {ex: {} for ex in exames}
                for row in dados:
                    dados_map[row[0]][row[1]] = row[2] # row[2] é o tempo médio

                cores = plt.cm.tab10.colors 

                for i, medico in enumerate(medicos):
                    valores = [dados_map[exame].get(medico, 0) for exame in exames]
                    pos_deslocada = [p + (i * largura_barra) for p in posicoes]
                    plt.bar(pos_deslocada, valores, width=largura_barra, label=medico, color=cores[i % len(cores)])

                centro_grupo = [p + largura_barra * (n_medicos - 1) / 2 for p in posicoes]
                plt.xticks(centro_grupo, exames, rotation=45)
                plt.legend(title="Médicos")
                plt.xlabel("Exame")

            plt.title("Média de Tempo por Exame")
            plt.ylabel("Tempo médio (min)")
            plt.grid(True, linestyle='--', alpha=0.7, axis='y')
            plt.tight_layout() 

            if caminho_oculto:
                plt.savefig(caminho_oculto, dpi=150) # Salva qualidade média pro PDF
                plt.close()
                return True

            nome_arquivo = f"{directory_path}/Tempo_exame_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(nome_arquivo, dpi=300)
            plt.close() 

            page.show_dialog(ft.SnackBar(ft.Text(f"Salvo como: {os.path.basename(nome_arquivo)}"), bgcolor="green"))
            page.update()

        except Exception as err:
            print(err)
            page.show_dialog(ft.SnackBar(ft.Text(f"Erro ao salvar: {err}"), bgcolor="red"))
            page.update()

# ==============================================================================
#                       PROCESSAMENTO DICOM (IMPORTAÇÃO)
# ==============================================================================

    def extrair_valores(sequence, info):
        for item in sequence:
            if hasattr(item, "ConceptNameCodeSequence"):
                codigo = item.ConceptNameCodeSequence[0].CodeValue
                if codigo in codigos_dose:
                    nome, unidade = codigos_dose[codigo]
                    if hasattr(item, "MeasuredValueSequence"):
                        valor = item.MeasuredValueSequence[0].NumericValue
                        info[f"{nome} ({unidade})"] = valor
            
            if hasattr(item, "ContentSequence"):
                extrair_valores(item.ContentSequence, info)

    def identificar_medico(nome_dicom_raw):
        # 1. Validação básica
        if not nome_dicom_raw or str(nome_dicom_raw) == "N/A":
            return "N/A"

        try:
            # 2. Limpeza
            # Remove os ^ e garante espaços corretos
            texto_limpo = str(nome_dicom_raw).replace('^', ' ').strip()

            # 3. Divide o texto em uma lista de palavras
            partes = texto_limpo.split()

            # 4. VARREDURA: Olha palavra por palavra
            for item in partes:   
                if item.isdigit():
                    return item 
                
        except Exception:
            pass 
        return f"{nome_dicom_raw}"
        
    def upload_exames():
        global upload_path
        for raiz, pastas, arquivos in os.walk(upload_path):
            for arquivo in arquivos:
                caminho_completo = os.path.join(raiz, arquivo)

                try:
                    ds = pydicom.dcmread(caminho_completo, stop_before_pixels=True, force=True)

                    if ds.get("Modality") == "SR":
                        # 1. Identificação do Médico
                        nome_medico_bruto = ds.get("PerformingPhysicianName", "N/A")
                        medico_id = identificar_medico(nome_medico_bruto)

                        # 2. Data
                        data_dicom = str(ds.get("StudyDate", ""))
                        if len(data_dicom) == 8:
                            data_formatada = f"{data_dicom[0:4]}-{data_dicom[4:6]}-{data_dicom[6:8]}"
                        else:
                            data_formatada = datetime.date.today().strftime("%Y-%m-%d")
                            
                        # 3. Extração de Valores
                        metrics = {
                            "Dose": 0.0, 
                            "DAP": 0.0, 
                            "TempoFluoro": 0.0, 
                            "TempoAcq": 0.0
                        }

                        if hasattr(ds, "ContentSequence"):
                            def extrair_simples(seq, dest):
                                for it in seq:
                                    if hasattr(it, "ConceptNameCodeSequence"):
                                        c = it.ConceptNameCodeSequence[0].CodeValue
                                        if hasattr(it, "MeasuredValueSequence"):
                                            valor = float(it.MeasuredValueSequence[0].NumericValue)

                                            if c == "113725": # Dose Total
                                                dest["Dose"] = valor
                                            elif c == "113722": # DAP Total
                                                dest["DAP"] = valor
                                            elif c == "113730": # Total Fluoro Time
                                                dest["TempoFluoro"] += valor #
                                            #elif c == "113855": # Total Acquisition Time
                                            #    dest["TempoAcq"] += valor    
                                    if hasattr(it, "ContentSequence"): 
                                        extrair_simples(it.ContentSequence, dest)
                            
                            extrair_simples(ds.ContentSequence, metrics)

                        # 4. Tratamento e Conversão
                        
                        # Dose: Multiplica por 1000 para mGy
                        dose = metrics["Dose"] * 1000 
                        
                        # DAP: Multiplica por 1000 para mGy.m2 
                        dap = metrics["DAP"] * 1e6    

                        # Tempo: SOMA os dois tempos encontrados
                        tempo_s = metrics["TempoFluoro"] + metrics["TempoAcq"]
                        
                        # Formata HH:MM:SS
                        m, s = divmod(tempo_s, 60)
                        h, m = divmod(m, 60)
                        tempo_fmt = "{:02d}:{:02d}:{:02d}".format(int(h), int(m), int(s))
                        
                        # 5. Novos Campos
                        paciente_id = str(ds.get("PatientID", "0"))
                        sexo_raw = str(ds.get("PatientSex", "NI")).upper()
                        sexo = sexo_raw if sexo_raw in ["F", "M"] else "NI"
                        exame_nome = str(ds.get("AdmittingDiagnosesDescription", ds.get("StudyDescription", "NI")))
                        fabricante = ds.get("Manufacturer", "Desconhecido")
                        numero_serie = str(ds.get("DeviceSerialNumber", ""))
                        inserir_exame((data_formatada, medico_id, exame_nome, round(dose, 2), tempo_fmt, round(dap, 2), paciente_id, sexo, f"{fabricante}-{numero_serie}"))
                        atualizar_tudo()
                        page.show_dialog(ft.SnackBar(ft.Text(f"Importação Finalizada!"), bgcolor="green"))
                except Exception as e:
                    print(f"Erro ao ler {arquivo}: {e}")
                    continue
            
            

    # --- UTILS ---
    def formatar_data(valor): return str(valor).split()[0] if valor else ""
    def formatar_tempo(valor): return str(valor).split()[0].replace('.000000','') if valor else ""

    # --- TABELA ---
    colunas_tabela = [
        ft.DataColumn(ft.Text("ID"), numeric=True), 
        ft.DataColumn(ft.Text("Data")), 
        ft.DataColumn(ft.Text("Médico")),
        ft.DataColumn(ft.Text("Exame")),  
        ft.DataColumn(ft.Text("Tempo"), numeric=True),
        ft.DataColumn(ft.Text("ID Paciente"), numeric=True), 
        ft.DataColumn(ft.Text("Sexo")), 
        ft.DataColumn(ft.Text("Sala")),
        ft.DataColumn(ft.Text(fr"DAP (μGym²)"), numeric=True),
        ft.DataColumn(ft.Text("Dose (mGy)"), numeric=True),
    ]
    tabela = ft.DataTable(columns=colunas_tabela, rows=[], border=ft.Border.all(1, "grey"), border_radius=ft.BorderRadius.all(10), vertical_lines=ft.border.BorderSide(1, "grey"), data_row_max_height=60)

    # --- CONFIG GRÁFICOS ---
    def criar_grafico_base(titulo):
        return fch.BarChart(
            expand=True, interactive=True, max_y=100,
            border=ft.Border.all(1, ft.Colors.GREY_400),
            horizontal_grid_lines=fch.ChartGridLines(color=ft.Colors.GREY_300, width=1, dash_pattern=[3, 3]),
            tooltip=fch.BarChartTooltip(bgcolor=ft.Colors.with_opacity(0.95, ft.Colors.WHITE)),
            left_axis=fch.ChartAxis(label_size=40, title=ft.Text(titulo, weight="bold"), title_size=20, labels=[]),
            bottom_axis=fch.ChartAxis(label_size=40, labels=[]), groups=[]
        )

    grafico_barras = criar_grafico_base("Dose Média")
    container_grafico = ft.Container(content=grafico_barras, padding=ft.Padding.all(20), height=600, border_radius=ft.BorderRadius.all(10), border=ft.Border.all(1, ft.Colors.GREY_300))

    grafico_tempo = criar_grafico_base("Minutos Médios")
    container_grafico_tempo = ft.Container(content=grafico_tempo, padding=ft.Padding.all(20), height=600, border_radius=ft.BorderRadius.all(10), border=ft.Border.all(1, ft.Colors.GREY_300))

    grafico_exame = criar_grafico_base("Dose / Exame")
    container_grafico_exame = ft.Container(content=grafico_exame, padding=ft.Padding.all(20), height=600, border_radius=ft.BorderRadius.all(10), border=ft.Border.all(1, ft.Colors.GREY_300))

    grafico_tempo_exame = criar_grafico_base("Tempo / Exame")
    container_grafico_tempo_exame = ft.Container(content=grafico_tempo_exame, padding=ft.Padding.all(20), height=600, border_radius=ft.BorderRadius.all(10), border=ft.Border.all(1, ft.Colors.GREY_300))

    # --- GRÁFICO EVOLUÇÃO TEMPORAL ---
    grafico_linha = fch.LineChart(
        expand=True,
        min_y=0,
        min_x=0,
        border=ft.Border.all(1, ft.Colors.GREY_400),
        horizontal_grid_lines=fch.ChartGridLines(interval=1, color=ft.Colors.GREY_300, width=1),
        tooltip=fch.LineChartTooltip(
            bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.WHITE)
        ),
        left_axis=fch.ChartAxis(
            label_size=40, 
            title=ft.Text("Qtd Exames", weight="bold"), 
            title_size=20
        ),
        bottom_axis=fch.ChartAxis(
            label_size=40,
        ),
        data_series=[] 
    )   

    # --- INPUTS ---
    min_dose = ft.TextField(label="Dose min", keyboard_type="number", width=150)
    max_dose = ft.TextField(label="Dose max", keyboard_type="number", width=150)
    medico_entry = ft.TextField(label="Medico (Use ; para vários)", width=150)
    exame_entry = ft.Dropdown(label="Exame", width=150, options=[ft.dropdown.Option(x) for x in lista_exames])
    min_tempo_entry = ft.TextField(label="Tempo min", width=150)
    max_tempo_entry = ft.TextField(label="Tempo max", width=150)
    min_dap_entry = ft.TextField(label="DAP min", keyboard_type="number", width=150)
    max_dap_entry = ft.TextField(label="DAP max", keyboard_type="number", width=150)
    sala_entry = ft.Dropdown(label="Sala", width=150, options=[ft.dropdown.Option(x) for x in lista_equipamentos])
    sexo_entry = ft.Dropdown(label="Sexo", width=105, options=[
        ft.dropdown.Option("F"), 
        ft.dropdown.Option("M"), 
        ft.dropdown.Option("NI")
    ])
    id_paciente_entry = ft.TextField(label="ID Paciente", width=150)
    txt_datas = ft.Text("Nenhuma data selecionada")

    def handle_change(e):
        global data_inicio, data_final
        if e.control.start_value: data_inicio = e.control.start_value.strftime('%Y-%m-%d')
        if e.control.end_value: data_final = e.control.end_value.strftime('%Y-%m-%d')
        txt_datas.value = f"De: {formatar_data(data_inicio)} Até: {formatar_data(data_final)}"
        page.update()

    today = datetime.datetime.now()
    drp = ft.DateRangePicker(start_value=datetime.datetime(year=today.year, month=today.month, day=1), end_value=datetime.datetime(year=today.year, month=today.month, day=15), on_change=handle_change)
    page.overlay.append(drp)

    # --- FUNÇÕES AUXILIARES DE GRÁFICOS ---

    def popular_grafico_simples(dados_tupla, grafico, cores, unit_suffix=""):
        grp = []; lbl_x = []; max_val = 0
        if not dados_tupla: dados_tupla = [] 
        
        for i, row in enumerate(dados_tupla):
            nome = row[0]
            val = row[1] if row[1] else 0
            mn = row[2] if row[2] else 0
            mx = row[3] if row[3] else 0
            qt = row[4] if row[4] else 0

            if val > max_val: max_val = val
            nome_display = nome[:8] + ".." if nome and len(nome) > 10 else (nome if nome else "N/A")
            
            tooltip_txt = f"{nome}\nMédia: {val:.2f}{unit_suffix}\nMin: {mn:.2f} | Max: {mx:.2f}\nQtd: {qt}"
            
            grp.append(fch.BarChartGroup(x=i, rods=[fch.BarChartRod(from_y=0, to_y=val, width=40 , color=cores[i % len(cores)], tooltip=tooltip_txt, border_radius=0)]))
            lbl_x.append(fch.ChartAxisLabel(value=i, label=ft.Container(ft.Text(nome_display, size=10, weight="bold"), padding=ft.Padding.all(10))))
        
        teto = max_val * 1.4 if max_val > 0 else 10
        grafico.groups = grp; grafico.max_y = teto; grafico.bottom_axis.labels = lbl_x

    def popular_grafico_agrupado(res_dados, grafico, modo_multiplo, cores_base, unit_suffix=""):
        if not modo_multiplo:
            popular_grafico_simples(res_dados, grafico, cores_base, unit_suffix)
        else:
            if not res_dados: res_dados = []
            medicos_unicos = sorted(list(set(row[1] for row in res_dados)))
            exames_unicos = sorted(list(set(row[0] for row in res_dados)))
            
            dados_map = {ex: {} for ex in exames_unicos}
            max_val = 0
            for ex, med, val, mn, mx, qt in res_dados:
                if val > max_val: max_val = val
                dados_map[ex][med] = (val, mn, mx, qt)
            
            mapa_cores = {med: cores_base[i % len(cores_base)] for i, med in enumerate(medicos_unicos)}
            grupos = []
            eixo_x = []
            
            for i, exame in enumerate(exames_unicos):
                barras = []
                for medico in medicos_unicos:
                    dados_med = dados_map[exame].get(medico, (0, 0, 0, 0))
                    valor, mn, mx, qt = dados_med
                    tooltip_txt = f"{medico}\nMédia: {valor:.2f}{unit_suffix}\nMin: {mn:.2f} | Max: {mx:.2f}\nQtd: {qt}"
                    barras.append(fch.BarChartRod(from_y=0, to_y=valor, width=15, color=mapa_cores[medico], tooltip=tooltip_txt, border_radius=0))
                
                grupos.append(fch.BarChartGroup(x=i, rods=barras))
                eixo_x.append(fch.ChartAxisLabel(value=i, label=ft.Container(ft.Text(exame, size=10, weight="bold"), padding=ft.Padding.all(10))))

            teto = max_val * 1.4 if max_val > 0 else 10
            grafico.groups = grupos
            grafico.bottom_axis.labels = eixo_x
            grafico.max_y = teto
            legenda = " | ".join(medicos_unicos)
            grafico.left_axis.title.value = f"Valores ({legenda})"

    

    # --- FUNÇÃO PRINCIPAL DE ATUALIZAÇÃO DA TELA ---

    # 1. ATUALIZA SÓ A TABELA (Leve e Rápida)
    def atualizar_apenas_tabela():
        global data_inicio, data_final, pagina_atual
        # Pega valores dos inputs
        v_min, v_max = min_dose.value, max_dose.value
        v_min_t, v_max_t = min_tempo_entry.value, max_tempo_entry.value
        v_min_dap, v_max_dap = min_dap_entry.value, max_dap_entry.value
        v_med, v_exm, v_sala = medico_entry.value, exame_entry.value, sala_entry.value
        v_sexo, v_id_pac = sexo_entry.value, id_paciente_entry.value
        
        offset = (pagina_atual - 1) * itens_por_pagina
        
        # Busca SQL Limitada 
        dados, total_registros = carregar_dados_banco(data_inicio, data_final, v_min, v_max, v_med, v_exm, v_min_t, v_max_t, v_min_dap, v_max_dap, v_sala, v_sexo, v_id_pac, itens_por_pagina, offset)
        
        tabela.rows.clear()
        
        # Reconstrói as linhas 
        for row in dados:
            try:
                valor_dose = float(str(row[4]).replace(',', '.'))
            except (ValueError, TypeError):
                valor_dose = 0.0

            if valor_dose >= 1000 and valor_dose < 2000:
                color_icon, color_text = "#8F00FF", "#8F00FF" # Roxo
            elif valor_dose >= 2000 and valor_dose < 3000:
                color_icon, color_text = ft.Colors.BLUE, ft.Colors.BLUE
            elif valor_dose >= 3000 and valor_dose < 4000:
                color_icon, color_text = ft.Colors.YELLOW, ft.Colors.YELLOW
            elif valor_dose >= 4000 and valor_dose < 5000:
                color_icon, color_text = ft.Colors.ORANGE, ft.Colors.ORANGE
            elif valor_dose >= 5000:
                color_icon, color_text = ft.Colors.RED, ft.Colors.RED
            else:
                color_icon, color_text = None, None

            if color_icon:
                celula_dose = ft.Row([ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=color_icon, size=16), ft.Text(str(row[4]), color=color_text, weight="bold", selectable=True)], spacing=5)
            else:
                celula_dose = ft.Text(str(row[4]) if row[4] else "", selectable=True)

            tabela.rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(row[0]), weight="bold", selectable=True)),
                ft.DataCell(ft.Text(formatar_data(row[1]), selectable=True)),
                ft.DataCell(ft.Text(str(row[2])[:20] if row[2] else "", selectable=True)),
                ft.DataCell(ft.Text(str(row[3]) if row[3] else "", selectable=True)),
                ft.DataCell(ft.Text(str(formatar_tempo(row[5])) if row[5] else "", selectable=True)),
                ft.DataCell(ft.Text(str(row[7]) if row[7] else "", selectable=True)),
                ft.DataCell(ft.Text(str(row[8]) if row[8] else "", selectable=True)),
                ft.DataCell(ft.Text(str(row[9]) if row[9] else "", selectable=True)),
                ft.DataCell(ft.Text(str(float(row[6])) if row[6] else "", selectable=True)),
                ft.DataCell(celula_dose),
            ]))
        
        total_paginas = math.ceil(total_registros / itens_por_pagina) if total_registros > 0 else 1
        txt_paginacao.value = f"Página {pagina_atual} de {total_paginas} (Total: {total_registros})"
        btn_anterior.disabled = (pagina_atual == 1)
        btn_proximo.disabled = (pagina_atual >= total_paginas)
        tabela.update()
        controles_paginacao.update()


    # 2. ATUALIZA SÓ O GRÁFICO SELECIONADO (Otimizado)
    def atualizar_apenas_graficos(e=None):
        # Descobre o que o usuário quer ver
        tipo = selecao_grafico.value
        
        # Pega os filtros
        v_min, v_max = min_dose.value, max_dose.value
        v_min_t, v_max_t = min_tempo_entry.value, max_tempo_entry.value
        v_min_dap, v_max_dap = min_dap_entry.value, max_dap_entry.value
        v_med, v_exm, v_sala = medico_entry.value, exame_entry.value, sala_entry.value
        v_sexo, v_id_pac = sexo_entry.value, id_paciente_entry.value

        # Variáveis para montar a tela
        grafico_obj = None
        titulo_grafico = ""
        funcao_salvar = None

        # --- LÓGICA DE SELEÇÃO ---
        
        if tipo == "Evolução Temporal (Linha)":
            titulo_grafico = "Evolução Temporal (Exames/Dia)"
            funcao_salvar = handle_get_directory_path_evolucao
            
            # Agora a função retorna os dados E a flag de modo_multiplo
            dados_evo, modo_mult_evo = calcular_evolucao_temporal(data_inicio, data_final, v_min, v_max, v_med, v_exm, v_min_t, v_max_t, v_min_dap, v_max_dap, v_sala, v_sexo, v_id_pac)
            
            if dados_evo:
                if not modo_mult_evo:
                    # --- MODO SIMPLES (1 Linha) ---
                    pontos = []
                    for i, r in enumerate(dados_evo):
                        data_fmt = r[0]
                        pontos.append(fch.LineChartDataPoint(x=i, y=r[1], tooltip=f"Data: {data_fmt}\nQtd: {r[1]}"))
                    
                    step = max(1, int(len(dados_evo) / 6))
                    lbl_x = [fch.ChartAxisLabel(value=i, label=ft.Container(ft.Text(r[0][5:].replace("-","/"), size=10, weight="bold"), padding=ft.Padding.only(top=10))) for i, r in enumerate(dados_evo) if i % step == 0]

                    grafico_linha.data_series = [fch.LineChartData(points=pontos, stroke_width=3, color=ft.Colors.CYAN, curved=True, below_line_bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.CYAN))]
                    grafico_linha.bottom_axis.labels = lbl_x
                    grafico_linha.max_x = len(dados_evo) - 1
                    grafico_linha.max_y = (max([r[1] for r in dados_evo]) * 1.2) if dados_evo else 10
                
                else:
                    # --- MODO MÚLTIPLO (Várias Linhas / Médicos) ---
                    datas_unicas = sorted(list(set(r[0] for r in dados_evo)))
                    medicos_unicos = sorted(list(set(r[1] for r in dados_evo)))

                    # Cria um "mapa" zerado para garantir que todos os médicos tenham ponto em todas as datas
                    mapa_dados = {med: {d: 0 for d in datas_unicas} for med in medicos_unicos}
                    for r in dados_evo:
                        mapa_dados[r[1]][r[0]] = r[2] # r[1]=medico, r[0]=data, r[2]=qtd

                    cores = [ft.Colors.CYAN, ft.Colors.PINK, ft.Colors.LIME, ft.Colors.ORANGE, ft.Colors.PURPLE, ft.Colors.RED]
                    series = []
                    max_y_val = 0

                    # Cria uma linha para cada médico
                    for idx_med, medico in enumerate(medicos_unicos):
                        pontos = []
                        cor = cores[idx_med % len(cores)]
                        for i, data_exm in enumerate(datas_unicas):
                            qtd = mapa_dados[medico][data_exm]
                            if qtd > max_y_val: max_y_val = qtd
                            pontos.append(fch.LineChartDataPoint(x=i, y=qtd, tooltip=f"{medico}\nData: {data_exm}\nQtd: {qtd}"))
                        
                        # Adiciona a linha na lista de séries
                        series.append(fch.LineChartData(points=pontos, stroke_width=3, color=cor, curved=True))

                    # Labels do Eixo X
                    step = max(1, int(len(datas_unicas) / 6))
                    lbl_x = [fch.ChartAxisLabel(value=i, label=ft.Container(ft.Text(d[5:].replace("-","/"), size=10, weight="bold"), padding=ft.Padding.only(top=10))) for i, d in enumerate(datas_unicas) if i % step == 0]

                    grafico_linha.data_series = series
                    grafico_linha.bottom_axis.labels = lbl_x
                    grafico_linha.max_x = len(datas_unicas) - 1
                    grafico_linha.max_y = max_y_val * 1.2 if max_y_val > 0 else 10

            else:
                grafico_linha.data_series = []
            
            grafico_obj = grafico_linha

        elif tipo == "Média de Dose por Médico":
            titulo_grafico = "Média Dose/Médico"
            funcao_salvar = handle_get_directory_path_dose_medico
            res = calcular_media_medico(data_inicio, data_final, v_min, v_max, v_med, v_exm, v_min_t, v_max_t, v_min_dap, v_max_dap, v_sala, v_sexo, v_id_pac)
            popular_grafico_simples(res, grafico_barras, [ft.Colors.GREEN, ft.Colors.BLUE, ft.Colors.RED, ft.Colors.ORANGE, ft.Colors.PURPLE])
            grafico_obj = grafico_barras

        elif tipo == "Média de Tempo por Médico":
            titulo_grafico = "Média Tempo/Médico"
            funcao_salvar = handle_get_directory_path_tempo_medico
            res = calcular_media_tempo_medico(data_inicio, data_final, v_min, v_max, v_med, v_exm, v_min_t, v_max_t, v_min_dap, v_max_dap, v_sala, v_sexo, v_id_pac)
            popular_grafico_simples(res, grafico_tempo, [ft.Colors.DEEP_ORANGE, ft.Colors.INDIGO, ft.Colors.AMBER], " min")
            grafico_obj = grafico_tempo

        elif tipo == "Média de Dose por Exame":
            titulo_grafico = "Média Dose/Exame"
            funcao_salvar = handle_get_directory_path_dose_exame
            res, modo_mult = calcular_media_exame(data_inicio, data_final, v_min, v_max, v_med, v_exm, v_min_t, v_max_t, v_min_dap, v_max_dap, v_sala, v_sexo, v_id_pac)
            popular_grafico_agrupado(res, grafico_exame, modo_mult, [ft.Colors.BLUE, ft.Colors.RED, ft.Colors.GREEN])
            grafico_obj = grafico_exame

        elif tipo == "Média de Tempo por Exame":
            titulo_grafico = "Média Tempo/Exame"
            funcao_salvar = handle_get_directory_path_tempo_exame
            res, modo_mult = calcular_media_tempo_exame(data_inicio, data_final, v_min, v_max, v_med, v_exm, v_min_t, v_max_t, v_min_dap, v_max_dap, v_sala, v_sexo, v_id_pac)
            popular_grafico_agrupado(res, grafico_tempo_exame, modo_mult, [ft.Colors.BROWN, ft.Colors.CYAN, ft.Colors.LIME], " min")
            grafico_obj = grafico_tempo_exame

        # --- MONTAGEM FINAL DA TELA ---
        
        # Cria um cabeçalho com o Título e o Botão de Salvar específico
        cabecalho = ft.Row([
            ft.Text(titulo_grafico, size=20, weight="bold"),
            ft.IconButton(
                icon=ft.Icons.SAVE_ALT, 
                tooltip="Salvar Gráfico como PNG", 
                on_click=funcao_salvar
            )
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        # Atualiza o conteúdo do container principal
        container_grafico_ativo.content = ft.Column([
            cabecalho,
            ft.Container(height=20), # Espaçamento
            ft.Container(content=grafico_obj, height=600) # O gráfico em si
        ])
        
        container_grafico_ativo.update()

    # 3. O MAESTRO (Atualiza o que for necessário)
    def atualizar_tudo(e=None):
        atualizar_apenas_tabela()
        atualizar_apenas_graficos()

    # --- DIÁLOGOS DE EDIÇÃO (MODAIS) ---

    f_data = ft.TextField(label="Data", value=datetime.date.today().strftime("%Y-%m-%d"))
    f_medico = ft.TextField(label="Médico"); f_exame = ft.Dropdown(label="Exame", options=[ft.dropdown.Option(x) for x in lista_exames])
    f_dose = ft.TextField(label="Dose", keyboard_type="number"); f_tempo = ft.TextField(label="Tempo", keyboard_type="number")
    f_dap = ft.TextField(label="DAP", keyboard_type="number"); f_sala = ft.Dropdown(label="Sala", options=[ft.dropdown.Option(x) for x in lista_equipamentos])
    f_id_target = ft.TextField(label="Informe o ID", keyboard_type="number", width=150)
    f_paciente_id = ft.TextField(label="ID Paciente", keyboard_type="number")
    f_sexo = ft.Dropdown(label="Sexo", options=[ft.dropdown.Option("F"), ft.dropdown.Option("M"), ft.dropdown.Option("NI")])

    def open_add_dialog(e):
        f_medico.value = ""; f_exame.value = None; f_dose.value = ""; f_tempo.value = ""
        f_dap.value = ""; f_paciente_id.value = ""; f_sexo.value = ""; f_sala.value = ""
        page.show_dialog(dlg_add)

    def salvar_adicao(e):
        if inserir_exame((f_data.value, f_medico.value, f_exame.value, f_dose.value, f_tempo.value, f_dap.value, f_paciente_id.value, f_sexo.value, f_sala.value)):
            page.pop_dialog(); atualizar_tudo(); page.show_dialog(ft.SnackBar(ft.Text("Adição Confirmada"), bgcolor="green"))
        else: page.show_dialog(ft.SnackBar(ft.Text("Erro!"), bgcolor="red"))

    dlg_add = ft.AlertDialog(title=ft.Text("Novo"), content=ft.Column([f_data, f_medico, f_exame, f_dose, f_tempo, f_dap, f_paciente_id, f_sexo, f_sala
    ], height=600, scroll=ft.ScrollMode.ADAPTIVE), actions=[ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()), ft.FilledButton("Salvar", on_click=salvar_adicao)])

    def open_del_dialog(e): f_id_target.value = ""; page.show_dialog(dlg_del)

    def confirmar_remocao(e):
        entrada = f_id_target.value
        
        if not entrada:
            return

        # 1. Normaliza: Troca vírgulas por espaço e separa os itens
        tokens = entrada.replace(',', ' ').split()
        
        ids_para_processar = []

        # 2. Processa cada item (pode ser número único ou intervalo)
        for token in tokens:
            token = token.strip()
            if '-' in token:
                try:
                    partes = token.split('-')
                    if len(partes) == 2:
                        inicio = int(partes[0])
                        fim = int(partes[1])
                        if inicio > fim: 
                            inicio, fim = fim, inicio
                        for i in range(inicio, fim + 1):
                            ids_para_processar.append(str(i))
                except ValueError:
                    page.show_dialog(ft.SnackBar(ft.Text("Intervalo ou ID inválidos"), bgcolor="red"))

            elif token.isdigit():
                ids_para_processar.append(token)

        # 3. Executa a deleção
        removidos_qtd = 0
        ids_unicos = set(ids_para_processar) 

        for id_limpo in ids_unicos:
            if deletar_exame(id_limpo):
                removidos_qtd += 1

        # 4. Feedback
        if removidos_qtd > 0:
            page.pop_dialog()
            atualizar_tudo()
            page.show_dialog(ft.SnackBar(ft.Text(f"Sucesso: {removidos_qtd} itens removidos!"), bgcolor="green"))
        else:
            page.show_dialog(ft.SnackBar(ft.Text("Nenhum ID válido encontrado ou erro ao deletar."), bgcolor="red"))
    dlg_del = ft.AlertDialog(title=ft.Text("Remover"), content=ft.Column([ft.Text("ID para excluir:"), f_id_target], height=100), actions=[ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()), ft.FilledButton("Remover", style=ft.ButtonStyle(bgcolor=ft.Colors.RED, color=ft.Colors.WHITE), on_click=confirmar_remocao)])

    def open_edit_ask_id(e): f_id_target.value = ""; page.show_dialog(dlg_ask_edit)
    def carregar_para_editar(e):
        d = buscar_exame_por_id(f_id_target.value) if f_id_target.value else None
        if d:
            f_data.value = str(d[0])
            f_medico.value = str(d[1] or "")
            exame_db = str(d[2] or "")
            opcoes_exame_atuais = [opt.key for opt in f_exame.options] if f_exame.options else []
            if exame_db and exame_db not in opcoes_exame_atuais:
                f_exame.options.append(ft.dropdown.Option(exame_db))

            f_exame.value = exame_db
            f_dose.value = str(d[3] or "")
            f_tempo.value = str(d[4] or "")
            f_dap.value = str(d[5] or "")
            f_paciente_id.value = str(d[6] or "")
            f_sexo.value = str(d[7] or "")
            sala_db = str(d[8] or "")
            opcoes_sala_atuais = [opt.key for opt in f_sala.options] if f_sala.options else []

            if sala_db and sala_db not in opcoes_sala_atuais:
                f_sala.options.append(ft.dropdown.Option(sala_db))
            f_sala.value = sala_db

            page.pop_dialog()
            page.show_dialog(dlg_form_edit)
            page.update() 
        else:
            page.show_dialog(ft.SnackBar(ft.Text("Não encontrado"), bgcolor="red"))

    def salvar_edicao(e):
        if atualizar_exame(f_id_target.value, (f_data.value, f_medico.value, f_exame.value, f_dose.value, f_tempo.value, f_dap.value, f_paciente_id.value, f_sexo.value, f_sala.value)):
            page.pop_dialog(); atualizar_tudo(); page.show_dialog(ft.SnackBar(ft.Text("Editado!"), bgcolor="green"))
        else: page.show_dialog(ft.SnackBar(ft.Text("Erro!"), bgcolor="red"))

    dlg_ask_edit = ft.AlertDialog(title=ft.Text("Editar"), content=ft.Column([ft.Text("ID para editar:"), f_id_target], height=100), actions=[ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()), ft.FilledButton("Buscar", on_click=carregar_para_editar)])
    dlg_form_edit = ft.AlertDialog(title=ft.Text("Editando"), content=ft.Column([f_data, f_medico, f_exame, f_dose, f_tempo, f_dap, f_paciente_id, f_sexo, f_sala
    ], height=600, scroll=ft.ScrollMode.AUTO), actions=[ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()), ft.FilledButton("Salvar", on_click=salvar_edicao)])

    # --- LOGICA DE GERENCIAR EXAMES ---
    
    txt_novo_exame = ft.TextField(label="Novo Tipo", expand=True, on_submit=lambda e: add_exame_click(e))
    lista_view_exames = ft.Column(scroll=ft.ScrollMode.AUTO, height=300)

    def carregar_lista_no_modal():
        lista_view_exames.controls.clear()
        
        conn = conectar()
        if not conn: 
            lista_view_exames.controls.append(ft.Text("Nenhum banco de dados selecionado."))
            page.update()
            return 

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT nome FROM tipos_exames ORDER BY nome")
            itens = cursor.fetchall()
            conn.close()

            for item in itens:
                nome = item[0]
                lista_view_exames.controls.append(
                    ft.Row([
                        ft.Text(nome, expand=True),
                        ft.IconButton(
                            icon=ft.Icons.DELETE, 
                            icon_color="red", 
                            tooltip="Remover da lista",
                            on_click=lambda e, n=nome: remove_exame_click(n)
                        )
                    ], alignment="spaceBetween")
                )
        except Exception as e:
            print(f"Erro ao carregar lista: {e}")
            
        page.update()

    def add_exame_click(e):
        if not txt_novo_exame.value: return
        if adicionar_tipo_exame_db(txt_novo_exame.value):
            txt_novo_exame.value = ""
            carregar_lista_no_modal()
            atualizar_dropdowns_globais() 
            page.update()

    def remove_exame_click(nome_alvo):
        if remover_tipo_exame_db(nome_alvo):
            carregar_lista_no_modal()
            atualizar_dropdowns_globais()
            page.update()

    # Janela Modal
    dlg_gerenciar_exames = ft.AlertDialog(
        title=ft.Text("Gerenciar Lista de Exames"),
        content=ft.Container(
            width=400,
            height=400,
            content=ft.Column([
                ft.Row([txt_novo_exame, ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_color="green", on_click=add_exame_click)]),
                ft.Divider(),
                ft.Text("Exames Cadastrados:", weight="bold"),
                lista_view_exames,
            ])
        ),
        actions=[ft.TextButton("Fechar", on_click=lambda e: page.pop_dialog())]
    )

    def abrir_gerenciador_exames(e):
        carregar_lista_no_modal()
        page.show_dialog(dlg_gerenciar_exames)

    # --- LOGICA DE GERENCIAR EXAMES ---
    
    txt_novo_exame = ft.TextField(label="Novo Tipo", expand=True, on_submit=lambda e: add_exame_click(e))
    lista_view_exames = ft.Column(scroll=ft.ScrollMode.AUTO, height=300)

    def carregar_lista_exames():
        lista_view_exames.controls.clear()
        
        conn = conectar()
        if not conn: 
            lista_view_exames.controls.append(ft.Text("Nenhum banco de dados selecionado."))
            page.update()
            return 
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT nome FROM tipos_exames ORDER BY nome")
            itens = cursor.fetchall()
            conn.close()
            for item in itens:
                nome = item[0]
                lista_view_exames.controls.append(
                    ft.Row([
                        ft.Text(nome, expand=True),
                        ft.IconButton(
                            icon=ft.Icons.DELETE, 
                            icon_color="red", 
                            tooltip="Remover da lista",
                            on_click=lambda e, n=nome: remove_exame_click(n)
                        )
                    ], alignment="spaceBetween")
                )
        except Exception as e:
            print(f"Erro ao carregar lista: {e}")
            
        page.update()

    def add_exame_click(e):
        if not txt_novo_exame.value: return
        if adicionar_tipo_exame_db(txt_novo_exame.value):
            txt_novo_exame.value = ""
            carregar_lista_exames()
            atualizar_dropdowns_globais() 
            page.update()

    def remove_exame_click(nome_alvo):
        if remover_tipo_exame_db(nome_alvo):
            carregar_lista_exames() 
            atualizar_dropdowns_globais()
            page.update()

    dlg_gerenciar_exames = ft.AlertDialog(
        title=ft.Text("Gerenciar Lista de Exames"),
        content=ft.Container(
            width=400,
            height=400,
            content=ft.Column([
                ft.Row([txt_novo_exame, ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_color="green", on_click=add_exame_click)]),
                ft.Divider(),
                ft.Text("Exames Cadastrados:", weight="bold"),
                lista_view_exames,
            ])
        ),
        actions=[ft.TextButton("Fechar", on_click=lambda e: page.pop_dialog())]
    )

    def abrir_gerenciador_exames(e):
        carregar_lista_exames() 
        page.show_dialog(dlg_gerenciar_exames)

    # --- LOGICA DE GERENCIAR EQUIPAMENTOS S/N ---
    
    txt_novo_equipamento = ft.TextField(label="Novo Tipo", expand=True, on_submit=lambda e: add_equipamento_click(e))
    lista_view_equipamento = ft.Column(scroll=ft.ScrollMode.AUTO, height=300)

    def carregar_lista_equipamentos():
        lista_view_equipamento.controls.clear()
        
        conn = conectar()
        if not conn: 
            lista_view_equipamento.controls.append(ft.Text("Nenhum banco de dados selecionado."))
            page.update()
            return 
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT nome FROM tipos_equipamento ORDER BY nome")
            itens = cursor.fetchall()
            conn.close()
            for item in itens:
                nome = item[0]
                lista_view_equipamento.controls.append(
                    ft.Row([
                        ft.Text(nome, expand=True),
                        ft.IconButton(
                            icon=ft.Icons.DELETE, 
                            icon_color="red", 
                            tooltip="Remover da lista",
                            on_click=lambda e, n=nome: remove_equipamento_click(n)
                        )
                    ], alignment="spaceBetween")
                )
        except Exception as e:
            print(f"Erro ao carregar lista: {e}")
            
        page.update()

    def add_equipamento_click(e):
        if not txt_novo_equipamento.value: return
        if adicionar_tipo_equipamento_db(txt_novo_equipamento.value):
            txt_novo_equipamento.value = ""
            carregar_lista_equipamentos() 
            atualizar_dropdowns_globais() 
            page.update()

    def remove_equipamento_click(nome_alvo):
        if remover_tipo_equipamento_db(nome_alvo):
            carregar_lista_equipamentos() 
            atualizar_dropdowns_globais()
            page.update()

    dlg_gerenciar_equipamento = ft.AlertDialog(
        title=ft.Text("Gerenciar Lista de Equipamentos"),
        content=ft.Container(
            width=400,
            height=400,
            content=ft.Column([
                ft.Row([txt_novo_equipamento, ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_color="green", on_click=add_equipamento_click)]),
                ft.Divider(),
                ft.Text("Equipamentos Cadastrados:", weight="bold"),
                lista_view_equipamento,
            ])
        ),
        actions=[ft.TextButton("Fechar", on_click=lambda e: page.pop_dialog())]
    )

    def abrir_gerenciador_equipamento(e):
        carregar_lista_equipamentos() 
        page.show_dialog(dlg_gerenciar_equipamento)


    def atualizar_dropdowns_globais():
        lista_atualizada_exm = inicializar_tipos_exames()
        lista_atualizada_eqp = inicializar_equipamento()
        novas_opcoes_exm = [ft.dropdown.Option(x) for x in lista_atualizada_exm]
        novas_opcoes_eqp = [ft.dropdown.Option(x) for x in lista_atualizada_eqp]
        exame_entry.options = novas_opcoes_exm
        f_exame.options = novas_opcoes_exm
        sala_entry.options = novas_opcoes_eqp
        f_sala.options = novas_opcoes_eqp
        page.update()


    # --- BOTÕES AÇÃO ---
    def acao_filtrar(e): global pagina_atual; pagina_atual = 1; atualizar_tudo()
    def limpar_filtros(e):
        global data_inicio, data_final, pagina_atual; data_inicio = ""; data_final = ""; pagina_atual = 1
        min_dose.value = ""; max_dose.value = ""; min_tempo_entry.value = ""; max_tempo_entry.value = ""; min_dap_entry.value = ""; max_dap_entry.value = ""; medico_entry.value = ""; exame_entry.value = None
        sala_entry.value = ""; txt_datas.value = "Nenhuma data selecionada"
        sexo_entry.value = None
        id_paciente_entry.value = ""
        atualizar_tudo()
    def mudar_pagina(d):
        global pagina_atual
        pagina_atual += d
        pagina_atual = max(1, pagina_atual) 
        atualizar_apenas_tabela()


    # --- APOIO / PIX ---
    
    chave_pix_copia_cola = "00020101021126580014br.gov.bcb.pix01364a063b34-f773-4f81-a183-b0c08e9ae4105204000053039865802BR5920GABRIEL A A DA SILVA6013RIO DE JANEIR62070503***6304A3B1"
    
    def fechar_pix(e):
        page.pop_dialog()
        page.update()

    async def copiar_pix(e):
        await ft.Clipboard().set(chave_pix_copia_cola)
        page.show_dialog(ft.SnackBar(ft.Text("Chave Pix copiada!"), bgcolor="green"))
        page.update()

    dlg_pix = ft.AlertDialog(
        title=ft.Text("Apoie o Projeto"),
        content=ft.Column([
            ft.Text("Este software é gratuito e de código aberto (Open Source). Ele foi desenvolvido para auxiliar profissionais de radiologia e continuará sendo livre para sempre. Se este programa economizou seu tempo ou ajudou no seu trabalho, considere fazer uma doação voluntária para manter o desenvolvimento ativo e pagar os cafés das madrugadas de programação."),
            ft.Text("Escaneie o QR Code ou copie a chave abaixo:", text_align="center"),
            ft.Container(
                content=ft.Image(
                    src="pix.jpg",
                    width=500, 
                    height=500,
                    fit="contain"
                ),
                alignment=ft.Alignment.CENTER
                
            ),
            ft.TextField(
                value=chave_pix_copia_cola, 
                read_only=True, 
                text_size=12, 
                height=40,
                border_radius=10,
            )
        ], tight=True, width=600, height=650, alignment="center", scroll=ft.ScrollMode.ADAPTIVE),
        actions=[
            ft.TextButton("Fechar", on_click=fechar_pix),
            ft.FilledButton("Copiar Chave", icon=ft.Icons.COPY, on_click=copiar_pix),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def abrir_modal_pix(e):
        page.show_dialog(dlg_pix)
        page.update()

    btn_apoio = ft.FilledButton(
        "Apoiar", 
        icon=ft.Icons.VOLUNTEER_ACTIVISM, 
        style=ft.ButtonStyle(bgcolor=ft.Colors.PINK_400, color=ft.Colors.WHITE),
        on_click=abrir_modal_pix 
    )
    
    # --- INTERFACE DE CONTROLE ---

    # Função para alternar visibilidade
    def toggle_filtros(e):
        # Inverte o estado atual (Se True vira False, se False vira True)
        estado_atual = linha_1.visible
        linha_1.visible = not estado_atual
        linha_2.visible = not estado_atual
        if linha_1.visible:
            btn_toggle_filtros.icon = ft.Icons.VISIBILITY_OFF
            btn_toggle_filtros.tooltip = "Ocultar Filtros"
        else:
            btn_toggle_filtros.icon = ft.Icons.FILTER_LIST
            btn_toggle_filtros.tooltip = "Mostrar Filtros"
            
        page.update()

    # Botões Principais

    btn_anterior = ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda _: mudar_pagina(-1))
    btn_proximo = ft.IconButton(icon=ft.Icons.ARROW_FORWARD, on_click=lambda _: mudar_pagina(1))
    txt_paginacao = ft.Text(f"Página {pagina_atual}")
    controles_paginacao = ft.Row(controls=[btn_anterior, txt_paginacao, btn_proximo], alignment=ft.MainAxisAlignment.CENTER)

    btn_filtrar = ft.Button("Filtrar", icon=ft.Icons.SEARCH, on_click=acao_filtrar)
    btn_limpar = ft.FilledButton("Limpar", on_click=limpar_filtros, style=ft.ButtonStyle(bgcolor=ft.Colors.GREY))
    def abrir_cal(e): drp.open=True; page.update()
    btn_calendar = ft.Button("Data", icon=ft.Icons.EDIT_CALENDAR, on_click=abrir_cal)
    btn_upload = ft.Button("Upload", icon=ft.Icons.UPLOAD, on_click=handle_get_directory_path_upload)
    btn_config_exames = ft.IconButton(
        icon=ft.Icons.SETTINGS, 
        tooltip="Adicionar/Remover Tipos de Exames", 
        icon_size=20,
        on_click=abrir_gerenciador_exames)
    btn_config_equipamento = ft.IconButton(
        icon=ft.Icons.SETTINGS, 
        tooltip="Adicionar/Remover Equipamentos", 
        icon_size=20,
        on_click=abrir_gerenciador_equipamento)
    btn_toggle_filtros = ft.IconButton(
        icon=ft.Icons.VISIBILITY_OFF, 
        tooltip="Ocultar Filtros",
        on_click=toggle_filtros
    )
    btn_csv_full = ft.IconButton(
        icon=ft.Icons.DOWNLOAD, 
        tooltip="Baixar TUDO (CSV)", 
        icon_color=ft.Colors.GREEN, 
        on_click=exportar_csv_completo
    )
    
    btn_csv_filter = ft.IconButton(
        icon=ft.Icons.FILTER_ALT_OFF, 
        tooltip="Baixar Visualização Atual (CSV)", 
        icon_color=ft.Colors.BLUE, 
        on_click=exportar_csv_filtrado
    )

    btn_pdf = ft.IconButton(
        icon=ft.Icons.PICTURE_AS_PDF, 
        tooltip="Gerar Relatório em PDF (Filtrado)", 
        icon_color=ft.Colors.RED_700, 
        on_click=exportar_pdf_filtrado
    )

    selecao_grafico = ft.Dropdown(
        label="Selecione a Análise",
        width=400,
        options=[
            ft.dropdown.Option("Evolução Temporal (Linha)"),
            ft.dropdown.Option("Média de Dose por Médico"),
            ft.dropdown.Option("Média de Tempo por Médico"),
            ft.dropdown.Option("Média de Dose por Exame"),
            ft.dropdown.Option("Média de Tempo por Exame"),
        ],
        value="Evolução Temporal (Linha)", 
        on_select=atualizar_apenas_graficos
    )
    # --- LAYOUT CRUD ---
    btn_add = ft.FilledButton("Adicionar", icon=ft.Icons.ADD, style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN, color=ft.Colors.WHITE), on_click=open_add_dialog)
    btn_edit = ft.FilledButton("Editar", icon=ft.Icons.EDIT, style=ft.ButtonStyle(bgcolor=ft.Colors.ORANGE, color=ft.Colors.WHITE), on_click=open_edit_ask_id)
    btn_rem = ft.FilledButton("Remover", icon=ft.Icons.DELETE, style=ft.ButtonStyle(bgcolor=ft.Colors.RED, color=ft.Colors.WHITE), on_click=open_del_dialog)
    btn_file = ft.Button(content="Selecionar Data Base", icon=ft.Icons.UPLOAD_FILE, on_click=handle_pick_files,)
    btn_tema = ft.IconButton(icon=ft.Icons.DARK_MODE, on_click=toggle_tema, tooltip="Alternar Tema")

    # Layout das Linhas de Filtro
    linha_1 = ft.Row(controls=[min_dose, max_dose, ft.VerticalDivider(), min_dap_entry, max_dap_entry, ft.VerticalDivider(), min_tempo_entry, max_tempo_entry, ft.VerticalDivider()], scroll=ft.ScrollMode.ADAPTIVE)
    linha_2 = ft.Row(controls=[medico_entry, ft.Row([exame_entry, btn_config_exames], spacing=0), ft.VerticalDivider(), ft.Row([sala_entry, btn_config_equipamento], spacing=0), ft.VerticalDivider(), sexo_entry, id_paciente_entry, btn_calendar, txt_datas,], scroll=ft.ScrollMode.ADAPTIVE)    
    linha_3 = ft.Row(controls=[btn_file, btn_filtrar, btn_limpar, btn_upload, btn_apoio, selecao_grafico, btn_tema, btn_toggle_filtros], scroll=ft.ScrollMode.ADAPTIVE)

    # Layout Conteúdo Tabela
    conteudo_tabela = ft.Column(
        controls=[ft.Row(controls=[btn_add, btn_edit, btn_rem], alignment=ft.MainAxisAlignment.CENTER), ft.Row(scroll=ft.ScrollMode.ADAPTIVE, controls=[tabela]), ft.Row(controls=[controles_paginacao, btn_csv_filter, btn_csv_full, btn_pdf ])],
        scroll=ft.ScrollMode.ADAPTIVE, expand=True, visible=True
    )
    
    # Layout Conteúdo Dashboard

    container_grafico_ativo = ft.Container(
        padding=20,
        expand=True,
        border_radius=10,
        border=ft.Border.all(1, ft.Colors.GREY_300)
    )

    conteudo_dashboard = ft.Column(
        controls=[container_grafico_ativo],
        expand=True, 
        visible=False,
        scroll=ft.ScrollMode.ADAPTIVE
    )

    # Navegação
    def trocar_aba(e):
        index = e.control.selected_index
        if index == 0: # Aba Tabela
            conteudo_tabela.visible = True
            conteudo_dashboard.visible = False
            conteudo_tabela.update()
        else: # Aba Dashboard
            conteudo_tabela.visible = False
            conteudo_dashboard.visible = True
            conteudo_dashboard.update()

    nav_bar = ft.NavigationBar(selected_index=0, on_change=trocar_aba, destinations=[ft.NavigationBarDestination(icon=ft.Icons.LIST_ALT, label="Dados"), ft.NavigationBarDestination(icon=ft.Icons.BAR_CHART, label="Dashboard")])
    page.add( ft.Divider(), linha_1, linha_2, linha_3, ft.Divider(), ft.Column(controls=[conteudo_tabela, conteudo_dashboard], expand=True), nav_bar),
    atualizar_tudo()

if __name__ == "__main__":
    ft.run(main)
