"""
OpenZoe v1.0.3
------------------
Sistema de gerenciamento e análise de doses radiológicas baseado em arquivos DICOM SR.
Desenvolvido com Python, Flet, SQLite, Pydicom e Matplotlib.

Autor: Gabriel Amaro
Licença: MIT
"""

import flet as ft
import flet_charts as fch
import datetime
import math 
import os
import tempfile
from config import state
from core import database as db
from core import dicom_parser
from reports.csv_export import gerar_csv_string
from reports.pdf_export import RelatorioPDF
from core import analytics
from reports import charts_export
from core.utils import formatar_data, formatar_tempo
from ui import charts_ui

# ==============================================================================
#                           INTERFACE GRÁFICA (FLET)
# ==============================================================================

def main(page: ft.Page):
    page.title = "OpenZoe - Gerenciador de Radiologia"

    def toggle_tema(e):
        page.theme_mode = ft.ThemeMode.LIGHT if page.theme_mode == ft.ThemeMode.DARK else ft.ThemeMode.DARK
        btn_tema.icon = ft.Icons.DARK_MODE if page.theme_mode == ft.ThemeMode.LIGHT else ft.Icons.LIGHT_MODE
        page.update()

    # --- FUNÇÕES PARA SALVAR GRÁFICOS (VIA MÓDULOS) ---
    def salvar_grafico_evolucao(caminho_oculto=None):
        dados, modo = analytics.calcular_evolucao_temporal(state.data_inicio, state.data_final, min_dose.value, max_dose.value, medico_entry.value, exame_entry.value, min_tempo_entry.value, max_tempo_entry.value, min_dap_entry.value, max_dap_entry.value, sala_entry.value, sexo_entry.value, id_paciente_entry.value)
        if not dados:
            if not caminho_oculto: page.show_dialog(ft.SnackBar(ft.Text("Sem dados para salvar!"), bgcolor="red"))
            return False
        sucesso, msg = charts_export.gerar_png_evolucao(dados, modo, state.directory_path, caminho_oculto)
        if sucesso and not caminho_oculto: page.show_dialog(ft.SnackBar(ft.Text(f"Salvo como: {msg}"), bgcolor="green"))
        elif not sucesso: page.show_dialog(ft.SnackBar(ft.Text(f"Erro: {msg}"), bgcolor="red"))
        return sucesso

    def salvar_grafico_dose_medico(caminho_oculto=None):
        dados = analytics.calcular_media_medico(state.data_inicio, state.data_final, min_dose.value, max_dose.value, medico_entry.value, exame_entry.value, min_tempo_entry.value, max_tempo_entry.value, min_dap_entry.value, max_dap_entry.value, sala_entry.value, sexo_entry.value, id_paciente_entry.value)
        if not dados:
            if not caminho_oculto: page.show_dialog(ft.SnackBar(ft.Text("Sem dados para salvar!"), bgcolor="red"))
            return False
        sucesso, msg = charts_export.gerar_png_dose_medico(dados, state.directory_path, caminho_oculto)
        if sucesso and not caminho_oculto: page.show_dialog(ft.SnackBar(ft.Text(f"Salvo como: {msg}"), bgcolor="green"))
        return sucesso

    def salvar_grafico_tempo_medico(caminho_oculto=None):
        dados = analytics.calcular_media_tempo_medico(state.data_inicio, state.data_final, min_dose.value, max_dose.value, medico_entry.value, exame_entry.value, min_tempo_entry.value, max_tempo_entry.value, min_dap_entry.value, max_dap_entry.value, sala_entry.value, sexo_entry.value, id_paciente_entry.value)
        if not dados:
            if not caminho_oculto: page.show_dialog(ft.SnackBar(ft.Text("Sem dados para salvar!"), bgcolor="red"))
            return False
        sucesso, msg = charts_export.gerar_png_tempo_medico(dados, state.directory_path, caminho_oculto)
        if sucesso and not caminho_oculto: page.show_dialog(ft.SnackBar(ft.Text(f"Salvo como: {msg}"), bgcolor="green"))
        return sucesso

    def salvar_grafico_dose_exame(caminho_oculto=None):
        dados, modo = analytics.calcular_media_exame(state.data_inicio, state.data_final, min_dose.value, max_dose.value, medico_entry.value, exame_entry.value, min_tempo_entry.value, max_tempo_entry.value, min_dap_entry.value, max_dap_entry.value, sala_entry.value, sexo_entry.value, id_paciente_entry.value)
        if not dados:
            if not caminho_oculto: page.show_dialog(ft.SnackBar(ft.Text("Sem dados para salvar!"), bgcolor="red"))
            return False
        sucesso, msg = charts_export.gerar_png_dose_exame(dados, modo, state.directory_path, caminho_oculto)
        if sucesso and not caminho_oculto: page.show_dialog(ft.SnackBar(ft.Text(f"Salvo como: {msg}"), bgcolor="green"))
        return sucesso

    def salvar_grafico_tempo_exame(caminho_oculto=None):
        dados, modo = analytics.calcular_media_tempo_exame(state.data_inicio, state.data_final, min_dose.value, max_dose.value, medico_entry.value, exame_entry.value, min_tempo_entry.value, max_tempo_entry.value, min_dap_entry.value, max_dap_entry.value, sala_entry.value, sexo_entry.value, id_paciente_entry.value)
        if not dados:
            if not caminho_oculto: page.show_dialog(ft.SnackBar(ft.Text("Sem dados para salvar!"), bgcolor="red"))
            return False
        sucesso, msg = charts_export.gerar_png_tempo_exame(dados, modo, state.directory_path, caminho_oculto)
        if sucesso and not caminho_oculto: page.show_dialog(ft.SnackBar(ft.Text(f"Salvo como: {msg}"), bgcolor="green"))
        return sucesso

    # --- HANDLERS (SELEÇÃO DE ARQUIVOS) ---

    async def handle_pick_files(e: ft.Event[ft.Button]):
        files = await ft.FilePicker().pick_files(allow_multiple=True)
        if files:
            state.FILE_PATH = files[0].path
            conn = db.conectar()
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
            db.inicializar_tipos_exames() 
            db.inicializar_equipamento()
            atualizar_dropdowns_globais()
            
            cursor.execute(sql_create)
            conn.commit()
            conn.close()
            
            db.criar_indices()
            atualizar_tudo()
            page.show_dialog(ft.SnackBar(ft.Text(f"Arquivo Selecionado: {state.FILE_PATH}"), bgcolor="green"))
        else:
            page.update()

    async def handle_get_directory_path_evolucao(e: ft.Event[ft.Button]):
        state.directory_path = await ft.FilePicker().get_directory_path()
        if state.directory_path:
            salvar_grafico_evolucao()
        else:
            page.update()

    async def handle_get_directory_path_dose_medico(e: ft.Event[ft.Button]):
        state.directory_path = await ft.FilePicker().get_directory_path()
        if state.directory_path:
            salvar_grafico_dose_medico()
        else:
            page.update()

    async def handle_get_directory_path_tempo_medico(e: ft.Event[ft.Button]):
        state.directory_path = await ft.FilePicker().get_directory_path()
        if state.directory_path:
            salvar_grafico_tempo_medico()
        else:
            page.update()

    async def handle_get_directory_path_dose_exame(e: ft.Event[ft.Button]):
        state.directory_path = await ft.FilePicker().get_directory_path()
        if state.directory_path:
            salvar_grafico_dose_exame()
        else:
            page.update()

    async def handle_get_directory_path_tempo_exame(e: ft.Event[ft.Button]):
        state.directory_path = await ft.FilePicker().get_directory_path()
        if state.directory_path:
            salvar_grafico_tempo_exame()
        else:
            page.update()
 
    async def handle_get_directory_path_upload(e: ft.Event[ft.Button]):
        state.upload_path = await ft.FilePicker().get_directory_path()
        if state.upload_path:
            # 1. Avisa que começou (opcional, deixa a interface mais amigável)
            page.show_dialog(ft.SnackBar(ft.Text("Lendo arquivos DICOM, aguarde..."), bgcolor="blue"))
            page.update()

            # 2. Chama o nosso novo módulo isolado
            qtd_sucesso, qtd_erros = dicom_parser.processar_diretorio_dicom(state.upload_path)

            # 3. Atualiza a tabela com os novos dados
            atualizar_tudo()

            # 4. Dá o feedback final com a contagem exata
            if qtd_erros > 0:
                msg = f"Importação: {qtd_sucesso} lidos, {qtd_erros} erros (ver terminal)."
                cor = "orange"
            else:
                msg = f"Importação Finalizada! {qtd_sucesso} arquivos lidos com sucesso."
                cor = "green"

            page.show_dialog(ft.SnackBar(ft.Text(msg), bgcolor=cor))
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
                gerou_com_sucesso = funcao_grafico(caminho_oculto=temp_file) 
                
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
                
                # --- LÓGICA DE CORES DA DOSE (RGB) ---
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
            page.show_dialog(ft.SnackBar(ft.Text("Relatório PDF gerado com sucesso!"), bgcolor="green"))

        except Exception as err:
            page.show_dialog(ft.SnackBar(ft.Text(f"Erro ao gerar PDF: {err}"), bgcolor="red"))

    
    # --- TABELA ---
    tabela = charts_ui.criar_tabela_dados()

    # --- CONFIG GRÁFICOS ---
    # Instanciando gráficos da nova UI
    grafico_barras = charts_ui.criar_grafico_base("Dose Média")
    grafico_tempo = charts_ui.criar_grafico_base("Minutos Médios")
    grafico_exame = charts_ui.criar_grafico_base("Dose / Exame")
    grafico_tempo_exame = charts_ui.criar_grafico_base("Tempo / Exame")
    grafico_linha = charts_ui.criar_grafico_linha_base("Qtd Exames")

    # --- INPUTS ---
    min_dose = ft.TextField(label="Dose min", keyboard_type="number", width=150)
    max_dose = ft.TextField(label="Dose max", keyboard_type="number", width=150)
    medico_entry = ft.TextField(label="Medico (Use ; para vários)", width=150)
    exame_entry = ft.Dropdown(label="Exame", width=150, options=[])
    min_tempo_entry = ft.TextField(label="Tempo min", width=150)
    max_tempo_entry = ft.TextField(label="Tempo max", width=150)
    min_dap_entry = ft.TextField(label="DAP min", keyboard_type="number", width=150)
    max_dap_entry = ft.TextField(label="DAP max", keyboard_type="number", width=150)
    sala_entry = ft.Dropdown(label="Sala", width=150, options=[])
    sexo_entry = ft.Dropdown(label="Sexo", width=105, options=[
        ft.dropdown.Option("F"), 
        ft.dropdown.Option("M"), 
        ft.dropdown.Option("NI")
    ])
    id_paciente_entry = ft.TextField(label="ID Paciente", width=150)
    txt_datas = ft.Text("Nenhuma data selecionada")

    def handle_change(e):
        if e.control.start_value: state.data_inicio = e.control.start_value.strftime('%Y-%m-%d')
        if e.control.end_value: state.data_final = e.control.end_value.strftime('%Y-%m-%d')
        txt_datas.value = f"De: {formatar_data(state.data_inicio)} Até: {formatar_data(state.data_final)}"
        page.update()

    today = datetime.datetime.now()
    drp = ft.DateRangePicker(start_value=datetime.datetime(year=today.year, month=today.month, day=1), end_value=datetime.datetime(year=today.year, month=today.month, day=15), on_change=handle_change)
    page.overlay.append(drp)

    
    # --- FUNÇÃO PRINCIPAL DE ATUALIZAÇÃO DA TELA ---

    # 1. ATUALIZA SÓ A TABELA (Leve e Rápida)
    def atualizar_apenas_tabela():
        v_min, v_max = min_dose.value, max_dose.value
        v_min_t, v_max_t = min_tempo_entry.value, max_tempo_entry.value
        v_min_dap, v_max_dap = min_dap_entry.value, max_dap_entry.value
        v_med, v_exm, v_sala = medico_entry.value, exame_entry.value, sala_entry.value
        v_sexo, v_id_pac = sexo_entry.value, id_paciente_entry.value
        
        offset = (state.pagina_atual - 1) * state.itens_por_pagina
        
        dados, total_registros = db.carregar_dados_banco(state.data_inicio, state.data_final, v_min, v_max, v_med, v_exm, v_min_t, v_max_t, v_min_dap, v_max_dap, v_sala, v_sexo, v_id_pac, state.itens_por_pagina, offset)
        
        tabela.rows.clear()
        
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
        
        total_paginas = math.ceil(total_registros / state.itens_por_pagina) if total_registros > 0 else 1
        txt_paginacao.value = f"Página {state.pagina_atual} de {total_paginas} (Total: {total_registros})"
        btn_anterior.disabled = (state.pagina_atual == 1)
        btn_proximo.disabled = (state.pagina_atual >= total_paginas)
        tabela.update()
        controles_paginacao.update()


    # 2. ATUALIZA SÓ O GRÁFICO SELECIONADO (Otimizado)
    def atualizar_apenas_graficos(e=None):
        tipo = selecao_grafico.value
        
        v_min, v_max = min_dose.value, max_dose.value
        v_min_t, v_max_t = min_tempo_entry.value, max_tempo_entry.value
        v_min_dap, v_max_dap = min_dap_entry.value, max_dap_entry.value
        v_med, v_exm, v_sala = medico_entry.value, exame_entry.value, sala_entry.value
        v_sexo, v_id_pac = sexo_entry.value, id_paciente_entry.value

        grafico_obj = None
        titulo_grafico = ""
        funcao_salvar = None

        if tipo == "Evolução Temporal (Linha)":
            titulo_grafico = "Evolução Temporal (Exames/Dia)"
            funcao_salvar = handle_get_directory_path_evolucao
            
            dados_evo, modo_mult_evo = analytics.calcular_evolucao_temporal(state.data_inicio, state.data_final, v_min, v_max, v_med, v_exm, v_min_t, v_max_t, v_min_dap, v_max_dap, v_sala, v_sexo, v_id_pac)
            
            if dados_evo:
                if not modo_mult_evo:
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
                    datas_unicas = sorted(list(set(r[0] for r in dados_evo)))
                    medicos_unicos = sorted(list(set(r[1] for r in dados_evo)))

                    mapa_dados = {med: {d: 0 for d in datas_unicas} for med in medicos_unicos}
                    for r in dados_evo:
                        mapa_dados[r[1]][r[0]] = r[2] 

                    cores = [ft.Colors.CYAN, ft.Colors.PINK, ft.Colors.LIME, ft.Colors.ORANGE, ft.Colors.PURPLE, ft.Colors.RED]
                    series = []
                    max_y_val = 0

                    for idx_med, medico in enumerate(medicos_unicos):
                        pontos = []
                        cor = cores[idx_med % len(cores)]
                        for i, data_exm in enumerate(datas_unicas):
                            qtd = mapa_dados[medico][data_exm]
                            if qtd > max_y_val: max_y_val = qtd
                            pontos.append(fch.LineChartDataPoint(x=i, y=qtd, tooltip=f"{medico}\nData: {data_exm}\nQtd: {qtd}"))
                        
                        series.append(fch.LineChartData(points=pontos, stroke_width=3, color=cor, curved=True))

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
            res = analytics.calcular_media_medico(state.data_inicio, state.data_final, v_min, v_max, v_med, v_exm, v_min_t, v_max_t, v_min_dap, v_max_dap, v_sala, v_sexo, v_id_pac)
            charts_ui.popular_grafico_simples(res, grafico_barras, [ft.Colors.GREEN, ft.Colors.BLUE, ft.Colors.RED, ft.Colors.ORANGE, ft.Colors.PURPLE])
            grafico_obj = grafico_barras

        elif tipo == "Média de Tempo por Médico":
            titulo_grafico = "Média Tempo/Médico"
            funcao_salvar = handle_get_directory_path_tempo_medico
            res = analytics.calcular_media_tempo_medico(state.data_inicio, state.data_final, v_min, v_max, v_med, v_exm, v_min_t, v_max_t, v_min_dap, v_max_dap, v_sala, v_sexo, v_id_pac)
            charts_ui.popular_grafico_simples(res, grafico_tempo, [ft.Colors.DEEP_ORANGE, ft.Colors.INDIGO, ft.Colors.AMBER], " min")
            grafico_obj = grafico_tempo

        elif tipo == "Média de Dose por Exame":
            titulo_grafico = "Média Dose/Exame"
            funcao_salvar = handle_get_directory_path_dose_exame
            res, modo_mult = analytics.calcular_media_exame(state.data_inicio, state.data_final, v_min, v_max, v_med, v_exm, v_min_t, v_max_t, v_min_dap, v_max_dap, v_sala, v_sexo, v_id_pac)
            charts_ui.popular_grafico_agrupado(res, grafico_exame, modo_mult, [ft.Colors.BLUE, ft.Colors.RED, ft.Colors.GREEN])
            grafico_obj = grafico_exame

        elif tipo == "Média de Tempo por Exame":
            titulo_grafico = "Média Tempo/Exame"
            funcao_salvar = handle_get_directory_path_tempo_exame
            res, modo_mult = analytics.calcular_media_tempo_exame(state.data_inicio, state.data_final, v_min, v_max, v_med, v_exm, v_min_t, v_max_t, v_min_dap, v_max_dap, v_sala, v_sexo, v_id_pac)
            charts_ui.popular_grafico_agrupado(res, grafico_tempo_exame, modo_mult, [ft.Colors.BROWN, ft.Colors.CYAN, ft.Colors.LIME], " min")
            grafico_obj = grafico_tempo_exame

        cabecalho = ft.Row([
            ft.Text(titulo_grafico, size=20, weight="bold"),
            ft.IconButton(
                icon=ft.Icons.SAVE_ALT, 
                tooltip="Salvar Gráfico como PNG", 
                on_click=funcao_salvar
            )
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        container_grafico_ativo.content = ft.Column([
            cabecalho,
            ft.Container(height=20),
            ft.Container(content=grafico_obj, height=600)
        ])
        
        container_grafico_ativo.update()

    # 3. O MAESTRO (Atualiza o que for necessário)
    def atualizar_tudo(e=None):
        atualizar_apenas_tabela()
        atualizar_apenas_graficos()

    # --- DIÁLOGOS DE EDIÇÃO (MODAIS) ---

    f_data = ft.TextField(label="Data", value=datetime.date.today().strftime("%Y-%m-%d"))
    f_medico = ft.TextField(label="Médico"); f_exame = ft.Dropdown(label="Exame", options=[])
    f_dose = ft.TextField(label="Dose", keyboard_type="number"); f_tempo = ft.TextField(label="Tempo", keyboard_type="number")
    f_dap = ft.TextField(label="DAP", keyboard_type="number"); f_sala = ft.Dropdown(label="Sala", options=[])
    f_id_target = ft.TextField(label="Informe o ID", keyboard_type="number", width=150)
    f_paciente_id = ft.TextField(label="ID Paciente", keyboard_type="number")
    f_sexo = ft.Dropdown(label="Sexo", options=[ft.dropdown.Option("F"), ft.dropdown.Option("M"), ft.dropdown.Option("NI")])

    def open_add_dialog(e):
        f_medico.value = ""; f_exame.value = None; f_dose.value = ""; f_tempo.value = ""
        f_dap.value = ""; f_paciente_id.value = ""; f_sexo.value = ""; f_sala.value = ""
        page.show_dialog(dlg_add)

    def salvar_adicao(e):
        if db.inserir_exame((f_data.value, f_medico.value, f_exame.value, f_dose.value, f_tempo.value, f_dap.value, f_paciente_id.value, f_sexo.value, f_sala.value)):
            page.pop_dialog(); atualizar_tudo(); page.show_dialog(ft.SnackBar(ft.Text("Adição Confirmada"), bgcolor="green"))
        else: page.show_dialog(ft.SnackBar(ft.Text("Erro!"), bgcolor="red"))

    dlg_add = ft.AlertDialog(title=ft.Text("Novo"), content=ft.Column([f_data, f_medico, f_exame, f_dose, f_tempo, f_dap, f_paciente_id, f_sexo, f_sala
    ], height=600, scroll=ft.ScrollMode.ADAPTIVE), actions=[ft.Button(content="Cancelar", on_click=lambda e: page.pop_dialog()), ft.FilledButton("Salvar", on_click=salvar_adicao)])

    def open_del_dialog(e): f_id_target.value = ""; page.show_dialog(dlg_del)

    def confirmar_remocao(e):
        entrada = f_id_target.value
        
        if not entrada:
            return

        tokens = entrada.replace(',', ' ').split()
        ids_para_processar = []

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

        removidos_qtd = 0
        ids_unicos = set(ids_para_processar) 

        for id_limpo in ids_unicos:
            if db.deletar_exame(id_limpo):
                removidos_qtd += 1

        if removidos_qtd > 0:
            page.pop_dialog()
            atualizar_tudo()
            page.show_dialog(ft.SnackBar(ft.Text(f"Sucesso: {removidos_qtd} itens removidos!"), bgcolor="green"))
        else:
            page.show_dialog(ft.SnackBar(ft.Text("Nenhum ID válido encontrado ou erro ao deletar."), bgcolor="red"))
            
    dlg_del = ft.AlertDialog(title=ft.Text("Remover"), content=ft.Column([ft.Text("ID para excluir:"), f_id_target], height=100), actions=[ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()), ft.FilledButton("Remover", style=ft.ButtonStyle(bgcolor=ft.Colors.RED, color=ft.Colors.WHITE), on_click=confirmar_remocao)])

    def open_edit_ask_id(e): f_id_target.value = ""; page.show_dialog(dlg_ask_edit)
    def carregar_para_editar(e):
        d = db.buscar_exame_por_id(f_id_target.value) if f_id_target.value else None
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
        if db.atualizar_exame(f_id_target.value, (f_data.value, f_medico.value, f_exame.value, f_dose.value, f_tempo.value, f_dap.value, f_paciente_id.value, f_sexo.value, f_sala.value)):
            page.pop_dialog(); atualizar_tudo(); page.show_dialog(ft.SnackBar(ft.Text("Editado!"), bgcolor="green"))
        else: page.show_dialog(ft.SnackBar(ft.Text("Erro!"), bgcolor="red"))

    dlg_ask_edit = ft.AlertDialog(title=ft.Text("Editar"), content=ft.Column([ft.Text("ID para editar:"), f_id_target], height=100), actions=[ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()), ft.FilledButton("Buscar", on_click=carregar_para_editar)])
    dlg_form_edit = ft.AlertDialog(title=ft.Text("Editando"), content=ft.Column([f_data, f_medico, f_exame, f_dose, f_tempo, f_dap, f_paciente_id, f_sexo, f_sala
    ], height=600, scroll=ft.ScrollMode.AUTO), actions=[ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()), ft.FilledButton("Salvar", on_click=salvar_edicao)])

    # --- LOGICA DE GERENCIAR EXAMES ---
    
    txt_novo_exame = ft.TextField(label="Novo Tipo", expand=True, on_submit=lambda e: add_exame_click(e))
    lista_view_exames = ft.Column(scroll=ft.ScrollMode.AUTO, height=300)

    def carregar_lista_exames():
        lista_view_exames.controls.clear()
        
        conn = db.conectar()
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
        if db.adicionar_tipo_exame_db(txt_novo_exame.value):
            txt_novo_exame.value = ""
            carregar_lista_exames()
            atualizar_dropdowns_globais() 
            page.update()

    def remove_exame_click(nome_alvo):
        if db.remover_tipo_exame_db(nome_alvo):
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
        
        conn = db.conectar()
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
        if db.adicionar_tipo_equipamento_db(txt_novo_equipamento.value):
            txt_novo_equipamento.value = ""
            carregar_lista_equipamentos() 
            atualizar_dropdowns_globais() 
            page.update()

    def remove_equipamento_click(nome_alvo):
        if db.remover_tipo_equipamento_db(nome_alvo):
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
        lista_atualizada_exm = db.inicializar_tipos_exames()
        lista_atualizada_eqp = db.inicializar_equipamento()
        novas_opcoes_exm = [ft.dropdown.Option(x) for x in lista_atualizada_exm]
        novas_opcoes_eqp = [ft.dropdown.Option(x) for x in lista_atualizada_eqp]
        exame_entry.options = novas_opcoes_exm
        f_exame.options = novas_opcoes_exm
        sala_entry.options = novas_opcoes_eqp
        f_sala.options = novas_opcoes_eqp
        page.update()


    # --- BOTÕES AÇÃO ---
    def acao_filtrar(e): 
        state.pagina_atual = 1
        atualizar_tudo()
        
    def limpar_filtros(e):
        state.data_inicio = ""
        state.data_final = ""
        state.pagina_atual = 1
        min_dose.value = ""; max_dose.value = ""; min_tempo_entry.value = ""; max_tempo_entry.value = ""; min_dap_entry.value = ""; max_dap_entry.value = ""; medico_entry.value = ""; exame_entry.value = None
        sala_entry.value = ""; txt_datas.value = "Nenhuma data selecionada"
        sexo_entry.value = None
        id_paciente_entry.value = ""
        atualizar_tudo()
        
    def mudar_pagina(d):
        state.pagina_atual += d
        state.pagina_atual = max(1, state.pagina_atual) 
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
            ft.Button(content="Ver no GitHub",icon=ft.Icons.CODE, url="https://github.com/gabrielamaroufrj/OpenZoe.git"),
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
    txt_paginacao = ft.Text(f"Página {state.pagina_atual}")
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
            ft.dropdown.Option("Média de Dose por Médico"),
            ft.dropdown.Option("Média de Tempo por Médico"),
            ft.dropdown.Option("Média de Dose por Exame"),
            ft.dropdown.Option("Média de Tempo por Exame"),
            ft.dropdown.Option("Evolução Temporal (Linha)"),
        ],
        value="Média de Dose por Médico", 
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
    page.add( ft.Divider(), linha_1, linha_2, linha_3, ft.Divider(), ft.Column(controls=[conteudo_tabela, conteudo_dashboard], expand=True), nav_bar)
    atualizar_tudo()

if __name__ == "__main__":
    ft.run(main)
