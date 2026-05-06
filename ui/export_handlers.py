import flet as ft
import datetime
import os
import tempfile
from reports.csv_export import gerar_csv_string
from reports.pdf_export import RelatorioPDF
from core import database as db
from core import analytics
from reports import charts_export

def salvar_grafico_evolucao(page, state, inputs, caminho_oculto=None):
    dados, modo = analytics.calcular_evolucao_temporal(
        state.data_inicio, state.data_final, 
        inputs['min_dose'], inputs['max_dose'], inputs['medico'], inputs['exame'], 
        inputs['min_tempo'], inputs['max_tempo'], inputs['min_dap'], inputs['max_dap'], 
        inputs['sala'], inputs['sexo'], inputs['id_paciente']
    )
    if not dados:
        if not caminho_oculto: page.show_dialog(ft.SnackBar(ft.Text("Sem dados para salvar!"), bgcolor="red"))
        return False
    sucesso, msg = charts_export.gerar_png_evolucao(dados, modo, state.directory_path, caminho_oculto)
    if sucesso and not caminho_oculto: page.show_dialog(ft.SnackBar(ft.Text(f"Salvo como: {msg}"), bgcolor="green"))
    elif not sucesso: page.show_dialog(ft.SnackBar(ft.Text(f"Erro: {msg}"), bgcolor="red"))
    return sucesso

def salvar_grafico_dose_medico(page, state, inputs, caminho_oculto=None):
    dados = analytics.calcular_media_medico(
        state.data_inicio, state.data_final, 
        inputs['min_dose'], inputs['max_dose'], inputs['medico'], inputs['exame'], 
        inputs['min_tempo'], inputs['max_tempo'], inputs['min_dap'], inputs['max_dap'], 
        inputs['sala'], inputs['sexo'], inputs['id_paciente']
    )
    if not dados:
        if not caminho_oculto: page.show_dialog(ft.SnackBar(ft.Text("Sem dados para salvar!"), bgcolor="red"))
        return False
    sucesso, msg = charts_export.gerar_png_dose_medico(dados, state.directory_path, caminho_oculto)
    if sucesso and not caminho_oculto: page.show_dialog(ft.SnackBar(ft.Text(f"Salvo como: {msg}"), bgcolor="green"))
    return sucesso

def salvar_grafico_tempo_medico(page, state, inputs, caminho_oculto=None):
    dados = analytics.calcular_media_tempo_medico(
        state.data_inicio, state.data_final, 
        inputs['min_dose'], inputs['max_dose'], inputs['medico'], inputs['exame'], 
        inputs['min_tempo'], inputs['max_tempo'], inputs['min_dap'], inputs['max_dap'], 
        inputs['sala'], inputs['sexo'], inputs['id_paciente']
    )
    if not dados:
        if not caminho_oculto: page.show_dialog(ft.SnackBar(ft.Text("Sem dados para salvar!"), bgcolor="red"))
        return False
    sucesso, msg = charts_export.gerar_png_tempo_medico(dados, state.directory_path, caminho_oculto)
    if sucesso and not caminho_oculto: page.show_dialog(ft.SnackBar(ft.Text(f"Salvo como: {msg}"), bgcolor="green"))
    return sucesso

def salvar_grafico_dose_exame(page, state, inputs, caminho_oculto=None):
    dados, modo = analytics.calcular_media_exame(
        state.data_inicio, state.data_final, 
        inputs['min_dose'], inputs['max_dose'], inputs['medico'], inputs['exame'], 
        inputs['min_tempo'], inputs['max_tempo'], inputs['min_dap'], inputs['max_dap'], 
        inputs['sala'], inputs['sexo'], inputs['id_paciente']
    )
    if not dados:
        if not caminho_oculto: page.show_dialog(ft.SnackBar(ft.Text("Sem dados para salvar!"), bgcolor="red"))
        return False
    sucesso, msg = charts_export.gerar_png_dose_exame(dados, modo, state.directory_path, caminho_oculto)
    if sucesso and not caminho_oculto: page.show_dialog(ft.SnackBar(ft.Text(f"Salvo como: {msg}"), bgcolor="green"))
    return sucesso

def salvar_grafico_tempo_exame(page, state, inputs, caminho_oculto=None):
    dados, modo = analytics.calcular_media_tempo_exame(
        state.data_inicio, state.data_final, 
        inputs['min_dose'], inputs['max_dose'], inputs['medico'], inputs['exame'], 
        inputs['min_tempo'], inputs['max_tempo'], inputs['min_dap'], inputs['max_dap'], 
        inputs['sala'], inputs['sexo'], inputs['id_paciente']
    )
    if not dados:
        if not caminho_oculto: page.show_dialog(ft.SnackBar(ft.Text("Sem dados para salvar!"), bgcolor="red"))
        return False
    sucesso, msg = charts_export.gerar_png_tempo_exame(dados, modo, state.directory_path, caminho_oculto)
    if sucesso and not caminho_oculto: page.show_dialog(ft.SnackBar(ft.Text(f"Salvo como: {msg}"), bgcolor="green"))
    return sucesso

async def handle_export_csv_completo(page, on_success, on_error):
    texto_csv = gerar_csv_string(apenas_filtrados=False)
    nome_arquivo = f"Relatorio_Completo_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
    resultado = await ft.FilePicker().save_file(file_name=nome_arquivo, allowed_extensions=["csv"])
    
    if resultado:
        try:
            with open(resultado, 'w', newline='', encoding='utf-8-sig') as f:
                f.write(texto_csv)
            on_success("Relatório completo salvo!")
        except Exception as ex:
            on_error(f"Erro: {ex}")

async def handle_export_csv_filtrado(page, filtros, on_success, on_error, on_no_data):
    texto_csv = gerar_csv_string(apenas_filtrados=True, inputs_filtros=filtros)
    
    if not texto_csv:
        on_no_data()
        return

    nome_arquivo = f"Relatorio_Filtrado_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
    resultado = await ft.FilePicker().save_file(file_name=nome_arquivo, allowed_extensions=["csv"])
    
    if resultado:
        try:
            with open(resultado, 'w', newline='', encoding='utf-8-sig') as f:
                f.write(texto_csv)
            on_success("Relatório filtrado salvo!")
        except Exception as ex:
            on_error(f"Erro: {ex}")

async def exportar_pdf_filtrado(page, state, inputs, on_success, on_error):
    v_min, v_max = inputs['min_dose'], inputs['max_dose']
    v_min_t, v_max_t = inputs['min_tempo'], inputs['max_tempo']
    v_min_dap, v_max_dap = inputs['min_dap'], inputs['max_dap']
    v_med, v_exm, v_sala = inputs['medico'], inputs['exame'], inputs['sala']
    v_sexo, v_id_pac = inputs['sexo'], inputs['id_paciente']

    nome_sugerido = f"Relatorio_Dosimetria_{datetime.datetime.now().strftime('%Y%m%d')}.pdf"
    filepath = await ft.FilePicker().save_file(file_name=nome_sugerido, allowed_extensions=["pdf"])
    if not filepath: return

    try:
        conn = db.conectar()
        cursor = conn.cursor()
        sql_where, params = db.montar_query_filtros(state.data_inicio, state.data_final, v_min, v_max, v_med, v_exm, v_min_t, v_max_t, v_min_dap, v_max_dap, v_sala, v_sexo, v_id_pac)

        cursor.execute(f"SELECT data, medico, exam, dose_mgy, tempo {sql_where} ORDER BY CAST(REPLACE(dose_mgy, ',', '.') AS REAL) DESC LIMIT 10", params)
        top10_dados = cursor.fetchall()
        
        cursor.execute(f"SELECT COUNT(*) {sql_where}", params)
        total_exames = cursor.fetchone()[0]
        conn.close()

        pdf = RelatorioPDF()
        pdf.add_page()
        
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 8, "Filtros Aplicados:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "", 10)
        pdf.cell(0, 6, f"Período: {state.data_inicio if state.data_inicio else 'Início'} a {state.data_final if state.data_final else 'Hoje'}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, f"Médico(s): {v_med if v_med else 'Todos'}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, f"Exame: {v_exm if v_exm else 'Todos'}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        def colocar_grafico_no_pdf(funcao_grafico):
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
            gerou_com_sucesso = funcao_grafico(page, state, inputs, caminho_oculto=temp_file) 
            
            if gerou_com_sucesso:
                if pdf.get_y() > 200: pdf.add_page() 
                pdf.image(temp_file, w=180)
                pdf.ln(5)
            
            if os.path.exists(temp_file): os.unlink(temp_file)

        unico_dia = bool(state.data_inicio and state.data_final and state.data_inicio == state.data_final)
        unico_medico = bool(v_med and ";" not in v_med)

        if unico_dia:
            pdf.set_font("helvetica", "B", 14)
            pdf.set_text_color(0, 100, 0)
            dfmt = state.data_inicio[8:10] + "/" + state.data_inicio[5:7] + "/" + state.data_inicio[0:4]
            pdf.cell(0, 10, f"Total de Exames no dia {dfmt}: {total_exames}", new_x="LMARGIN", new_y="NEXT", align="C")
            pdf.set_text_color(0, 0, 0); pdf.ln(5)
        else:
            colocar_grafico_no_pdf(salvar_grafico_evolucao)

        if not unico_medico:
            colocar_grafico_no_pdf(salvar_grafico_dose_medico)
            colocar_grafico_no_pdf(salvar_grafico_tempo_medico)

        colocar_grafico_no_pdf(salvar_grafico_dose_exame)
        colocar_grafico_no_pdf(salvar_grafico_tempo_exame)

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
                valor_dose = float(ds.replace(',', '.'))
                if valor_dose >= 5000:
                    pdf.set_text_color(255, 0, 0) # Vermelho
                    pdf.set_font("helvetica", "B", 9)
                elif valor_dose >= 4000:
                    pdf.set_text_color(255, 128, 0) # Laranja
                    pdf.set_font("helvetica", "B", 9)
                elif valor_dose >= 3000:
                    pdf.set_text_color(204, 153, 0) # Amarelo (Mostarda para leitura no branco)
                    pdf.set_font("helvetica", "B", 9)
                elif valor_dose >= 2000:
                    pdf.set_text_color(0, 0, 255) # Azul
                    pdf.set_font("helvetica", "B", 9)
                elif valor_dose >= 1000:
                    pdf.set_text_color(143, 0, 255) # Roxo
                    pdf.set_font("helvetica", "B", 9)
                else:
                    pdf.set_text_color(0, 0, 0) # Preto padrão
                    pdf.set_font("helvetica", "", 9)
            except (ValueError, TypeError):
                pdf.set_text_color(0, 0, 0) # Falha segura (Preto)
                pdf.set_font("helvetica", "", 9)
            
            pdf.cell(25, 8, ds, border=1)
            pdf.set_text_color(0, 0, 0); pdf.set_font("helvetica", "", 9)
            pdf.cell(25, 8, str(row[4])[:8] if row[4] else "N/A", border=1, new_x="LMARGIN", new_y="NEXT")

        pdf.output(filepath)
        on_success("Relatório PDF gerado com sucesso!")

    except Exception as err:
        on_error(f"Erro ao gerar PDF: {err}")
