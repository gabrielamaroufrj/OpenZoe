# database.py
import sqlite3
from config import state

def conectar():
    if not state.FILE_PATH: 
        return None
    return sqlite3.connect(state.FILE_PATH)

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

def carregar_dados_banco(data_inicio, data_fim, min_d, max_d, n_medico, exm, min_tempo, max_tempo, min_dap, max_dap, sala, sexo, id_pac, limit=15, offset=0):
    dados = []
    total_registros = 0
    try:
        conn = conectar()
        if not conn: return dados, total_registros
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
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_data ON exames(data)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_medico ON exames(medico)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_exam ON exames(exam)")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erro ao criar índices: {e}")

def inserir_exame(dados):
    try:
        conn = conectar()
        if not conn: return False
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
    except Exception as e: 
        print(f"Erro Insert: {e}")
        return False

def deletar_exame(id_row):
    try:
        conn = conectar()
        if not conn: return False
        cursor = conn.cursor()
        cursor.execute("DELETE FROM exames WHERE rowid = ?", (id_row,))
        if cursor.rowcount == 0: 
            conn.close()
            return False 
        conn.commit()
        conn.close()
        return True
    except Exception as e: 
        print(f"Erro Delete: {e}")
        return False

def buscar_exame_por_id(id_row):
    try:
        conn = conectar()
        if not conn: return None
        cursor = conn.cursor()
        cursor.execute("SELECT data, medico, exam, dose_mgy, tempo, dap, paciente_id, sexo, sala FROM exames WHERE rowid = ?", (id_row,))
        dados = cursor.fetchone()
        conn.close()
        return dados
    except Exception as e: 
        print(f"Erro Busca ID: {e}")
        return None

def atualizar_exame(id_row, dados):
    try:
        conn = conectar()
        if not conn: return False
        cursor = conn.cursor()
        sql = """UPDATE exames SET data=?, medico=?, exam=?, dose_mgy=?, tempo=?, dap=?, paciente_id=?, sexo=?, sala=? WHERE rowid=?"""
        params = list(dados)
        params.append(id_row)
        cursor.execute(sql, params)
        conn.commit()
        conn.close()
        return True
    except Exception as e: 
        print(f"Erro Update: {e}")
        return False

def inicializar_tipos_exames():
    padroes = []
    try:
        conn = conectar()
        if not conn: return padroes    
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS tipos_exames (nome TEXT PRIMARY KEY)")
        
        cursor.execute("SELECT COUNT(*) FROM tipos_exames")
        if cursor.fetchone()[0] == 0:
            for item in padroes:
                cursor.execute("INSERT INTO tipos_exames (nome) VALUES (?)", (item,))
            conn.commit()
        
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
    except Exception: return False

def remover_tipo_exame_db(nome):
    try:
        conn = conectar()
        if not conn: return False 
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tipos_exames WHERE nome = ?", (nome,))
        conn.commit()
        conn.close()
        return True
    except Exception: return False

def inicializar_equipamento():
    padroes = []
    try:
        conn = conectar()
        if not conn: return padroes    
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS tipos_equipamento (nome TEXT PRIMARY KEY)")
        
        cursor.execute("SELECT COUNT(*) FROM tipos_equipamento")
        if cursor.fetchone()[0] == 0:
            for item in padroes:
                cursor.execute("INSERT INTO tipos_equipamento (nome) VALUES (?)", (item,))
            conn.commit()
        
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
    except Exception: return False

def remover_tipo_equipamento_db(nome):
    try:
        conn = conectar()
        if not conn: return False 
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tipos_equipamento WHERE nome = ?", (nome,))
        conn.commit()
        conn.close()
        return True
    except Exception: return False
