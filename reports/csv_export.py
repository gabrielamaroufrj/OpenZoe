
# reports/csv_export.py
import csv
import io
from core import database as db
from config import state
from core.utils import formatar_data, formatar_tempo

def gerar_csv_string(apenas_filtrados=False, inputs_filtros=None):
    try:
        conn = db.conectar()
        if not conn: return ""
        cursor = conn.cursor()
        
        colunas_header = [
            "ID", "Data", "Médico", "Exame", "Dose (mGy)", 
            "Tempo", "DAP", "ID Paciente", "Sexo", "Sala"
        ]
        
        campos_sql = "rowid, data, medico, exam, dose_mgy, tempo, dap, paciente_id, sexo, sala"

        if apenas_filtrados and inputs_filtros:
            sql_where, params = db.montar_query_filtros(
                state.data_inicio, state.data_final, 
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

        output = io.StringIO()
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_ALL)
        writer.writerow(colunas_header)
        
        for row in dados:
            linha = list(row)
            linha[1] = formatar_data(linha[1])  
            linha[5] = formatar_tempo(linha[5]) 
            if linha[4]: linha[4] = str(linha[4]).replace('.', ',')
            if linha[6]: linha[6] = str(linha[6]).replace('.', ',')
            writer.writerow(linha)
            
        return output.getvalue()

    except Exception as e:
        print(f"Erro CSV: {e}")
        return ""