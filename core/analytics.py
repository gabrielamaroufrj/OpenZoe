# core/analytics.py
import datetime
from core import database as db

def calcular_evolucao_temporal(data_inicio, data_fim, min_d, max_d, n_medico, exm, min_tempo, max_tempo, min_dap, max_dap, sala, sexo, id_pac):
    modo_multiplo = False
    if n_medico and ";" in str(n_medico):
        modo_multiplo = True

    try:
        conn = db.conectar()
        if conn is None: return [], modo_multiplo
        cursor = conn.cursor()
        sql_where, params = db.montar_query_filtros(data_inicio, data_fim, min_d, max_d, n_medico, exm, min_tempo, max_tempo, min_dap, max_dap, sala, sexo, id_pac)
        
        if modo_multiplo:
            sql = f"SELECT date(data), medico, COUNT(*) {sql_where} GROUP BY date(data), medico ORDER BY date(data)"
        else:
            sql = f"SELECT date(data), COUNT(*) {sql_where} GROUP BY date(data) ORDER BY date(data)"
            
        cursor.execute(sql, params)
        res = cursor.fetchall()
        conn.close()

        if not res: return [], modo_multiplo

        datas = [r[0] for r in res]
        str_inicio = min(datas)
        str_fim = max(datas)

        d_inicio = datetime.datetime.strptime(str_inicio, "%Y-%m-%d").date()
        d_fim = datetime.datetime.strptime(str_fim, "%Y-%m-%d").date()

        todas_datas = []
        delta = d_fim - d_inicio
        for i in range(delta.days + 1):
            dia = d_inicio + datetime.timedelta(days=i)
            todas_datas.append(dia.strftime("%Y-%m-%d"))

        res_preenchido = []
        if not modo_multiplo:
            mapa_dados = {r[0]: r[1] for r in res}
            for d in todas_datas:
                res_preenchido.append((d, mapa_dados.get(d, 0)))
        else:
            medicos = list(set([r[1] for r in res]))
            mapa_dados = {m: {} for m in medicos}
            for r in res:
                mapa_dados[r[1]][r[0]] = r[2] 
            for d in todas_datas:
                for m in medicos:
                    res_preenchido.append((d, m, mapa_dados[m].get(d, 0)))

        return res_preenchido, modo_multiplo
    except Exception as e:
        print(f"Erro Evolução: {e}")
        return [], False

def calcular_media_medico(data_inicio, data_fim, min_d, max_d, n_medico, exm, min_tempo, max_tempo, min_dap, max_dap, sala, sexo, id_pac):
    resultados = []
    try:
        conn = db.conectar()
        cursor = conn.cursor()
        sql_where, params = db.montar_query_filtros(data_inicio, data_fim, min_d, max_d, n_medico, exm, min_tempo, max_tempo, min_dap, max_dap, sala, sexo, id_pac)
        
        sql_media = f"""
            SELECT medico, AVG(CAST(REPLACE(dose_mgy, ',', '.') AS REAL)) as media_dose,
                MIN(CAST(REPLACE(dose_mgy, ',', '.') AS REAL)) as min_dose,
                MAX(CAST(REPLACE(dose_mgy, ',', '.') AS REAL)) as max_dose,
                COUNT(*) as qtd
            {sql_where} GROUP BY medico ORDER BY media_dose DESC
        """
        cursor.execute(sql_media, params)
        resultados = cursor.fetchall()
        conn.close()
    except Exception as e: print(f"Erro SQL Media: {e}")
    return resultados

def calcular_media_tempo_medico(data_inicio, data_fim, min_d, max_d, n_medico, exm, min_tempo, max_tempo, min_dap, max_dap, sala, sexo, id_pac):
    try:
        conn = db.conectar()
        if not conn: return []
        cursor = conn.cursor()
        sql_where, params = db.montar_query_filtros(data_inicio, data_fim, min_d, max_d, n_medico, exm, min_tempo, max_tempo, min_dap, max_dap, sala, sexo, id_pac)
        calc_minutos = "(CAST(substr(tempo, 1, 2) AS INTEGER) * 60 + CAST(substr(tempo, 4, 2) AS INTEGER) + CAST(substr(tempo, 7, 2) AS REAL)/60)"
        sql = f"""
            SELECT medico, AVG({calc_minutos}) as media, MIN({calc_minutos}) as minimo, MAX({calc_minutos}) as maximo, COUNT(*) as qtd
            {sql_where} GROUP BY medico ORDER BY media DESC
        """
        cursor.execute(sql, params)
        resultados = cursor.fetchall()
        conn.close()
        return resultados
    except Exception as e:
        print(f"Erro Media Tempo SQL: {e}")
        return []

def calcular_media_exame(data_inicio, data_fim, min_d, max_d, n_medico, exm, min_tempo, max_tempo, min_dap, max_dap, sala, sexo, id_pac):
    resultados = []; modo_multiplo = False
    if n_medico and ";" in str(n_medico): modo_multiplo = True
    try:
        conn = db.conectar(); cursor = conn.cursor()
        sql_where, params = db.montar_query_filtros(data_inicio, data_fim, min_d, max_d, n_medico, exm, min_tempo, max_tempo, min_dap, max_dap, sala, sexo, id_pac)
        if modo_multiplo:
            sql_media = f"""SELECT exam, medico, AVG(CAST(REPLACE(dose_mgy, ',', '.') AS REAL)) as media_dose, MIN(CAST(REPLACE(dose_mgy, ',', '.') AS REAL)) as min_dose, MAX(CAST(REPLACE(dose_mgy, ',', '.') AS REAL)) as max_dose, COUNT(*) as qtd {sql_where} GROUP BY exam, medico ORDER BY exam"""
        else:
            sql_media = f"""SELECT exam, AVG(CAST(REPLACE(dose_mgy, ',', '.') AS REAL)) as media_dose, MIN(CAST(REPLACE(dose_mgy, ',', '.') AS REAL)) as min_dose, MAX(CAST(REPLACE(dose_mgy, ',', '.') AS REAL)) as max_dose, COUNT(*) as qtd {sql_where} GROUP BY exam ORDER BY media_dose DESC"""
        cursor.execute(sql_media, params)
        resultados = cursor.fetchall(); conn.close()
    except Exception as e: print(f"Erro SQL Media Exame: {e}")
    return resultados, modo_multiplo

def calcular_media_tempo_exame(data_inicio, data_fim, min_d, max_d, n_medico, exm, min_tempo, max_tempo, min_dap, max_dap, sala, sexo, id_pac):
    modo_multiplo = False
    if n_medico and ";" in str(n_medico): modo_multiplo = True
    try:
        conn = db.conectar()
        if not conn: return [], modo_multiplo
        cursor = conn.cursor()
        sql_where, params = db.montar_query_filtros(data_inicio, data_fim, min_d, max_d, n_medico, exm, min_tempo, max_tempo, min_dap, max_dap, sala, sexo, id_pac)
        calc_minutos = "(CAST(substr(tempo, 1, 2) AS INTEGER) * 60 + CAST(substr(tempo, 4, 2) AS INTEGER) + CAST(substr(tempo, 7, 2) AS REAL)/60)"
        if modo_multiplo:
            sql = f"""SELECT exam, medico, AVG({calc_minutos}) as media, MIN({calc_minutos}) as minimo, MAX({calc_minutos}) as maximo, COUNT(*) as qtd {sql_where} GROUP BY exam, medico ORDER BY exam"""
        else:
            sql = f"""SELECT exam, AVG({calc_minutos}) as media, MIN({calc_minutos}) as minimo, MAX({calc_minutos}) as maximo, COUNT(*) as qtd {sql_where} GROUP BY exam ORDER BY media DESC"""
        cursor.execute(sql, params)
        resultados = cursor.fetchall(); conn.close()
        return resultados, modo_multiplo
    except Exception as e:
        print(f"Erro Media Tempo Exame SQL: {e}")
        return [], False
