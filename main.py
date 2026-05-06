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
from ui import charts_ui, dialogs, forms, layouts, export_handlers, data_handlers, view_handlers

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
    # --- HANDLERS (SELEÇÃO DE ARQUIVOS) ---
    
    def get_current_inputs():
        return {
            'min_dose': min_dose.value, 'max_dose': max_dose.value,
            'medico': medico_entry.value, 'exame': exame_entry.value,
            'min_tempo': min_tempo_entry.value, 'max_tempo': max_tempo_entry.value,
            'min_dap': min_dap_entry.value, 'max_dap': max_dap_entry.value,
            'sala': sala_entry.value, 'sexo': sexo_entry.value,
            'id_paciente': id_paciente_entry.value
        }

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
            export_handlers.salvar_grafico_evolucao(page, state, get_current_inputs())
        else:
            page.update()

    async def handle_get_directory_path_dose_medico(e: ft.Event[ft.Button]):
        state.directory_path = await ft.FilePicker().get_directory_path()
        if state.directory_path:
            export_handlers.salvar_grafico_dose_medico(page, state, get_current_inputs())
        else:
            page.update()

    async def handle_get_directory_path_tempo_medico(e: ft.Event[ft.Button]):
        state.directory_path = await ft.FilePicker().get_directory_path()
        if state.directory_path:
            export_handlers.salvar_grafico_tempo_medico(page, state, get_current_inputs())
        else:
            page.update()

    async def handle_get_directory_path_dose_exame(e: ft.Event[ft.Button]):
        state.directory_path = await ft.FilePicker().get_directory_path()
        if state.directory_path:
            export_handlers.salvar_grafico_dose_exame(page, state, get_current_inputs())
        else:
            page.update()

    async def handle_get_directory_path_tempo_exame(e: ft.Event[ft.Button]):
        state.directory_path = await ft.FilePicker().get_directory_path()
        if state.directory_path:
            export_handlers.salvar_grafico_tempo_exame(page, state, get_current_inputs())
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
        await export_handlers.handle_export_csv_completo(
            page, 
            lambda msg: page.show_dialog(ft.SnackBar(ft.Text(msg), bgcolor="green")),
            lambda msg: page.show_dialog(ft.SnackBar(ft.Text(msg), bgcolor="red"))
        )

    async def exportar_csv_filtrado(e: ft.Event[ft.Button]):
        filtros_atuais = {
            'min_d': min_dose.value, 'max_d': max_dose.value,
            'med': medico_entry.value, 'exm': exame_entry.value,
            'min_t': min_tempo_entry.value, 'max_t': max_tempo_entry.value,
            'min_dap': min_dap_entry.value, 'max_dap': max_dap_entry.value,
            'sala': sala_entry.value, 'sexo': sexo_entry.value,
            'id_pac': id_paciente_entry.value
        }
        await export_handlers.handle_export_csv_filtrado(
            page,
            filtros_atuais,
            lambda msg: page.show_dialog(ft.SnackBar(ft.Text(msg), bgcolor="green")),
            lambda msg: page.show_dialog(ft.SnackBar(ft.Text(msg), bgcolor="red")),
            lambda: page.show_dialog(ft.SnackBar(ft.Text("Sem dados com esses filtros."), bgcolor="orange"))
        )

    # --- Hendler Para montar Relatório (PDF) ---

    # --- Hendler Para montar Relatório (PDF) ---

    async def exportar_pdf_filtrado(e: ft.Event[ft.Button]):
        v_min, v_max = min_dose.value, max_dose.value
        v_min_t, v_max_t = min_tempo_entry.value, max_tempo_entry.value
        v_min_dap, v_max_dap = min_dap_entry.value, max_dap_entry.value
        v_med, v_exm, v_sala = medico_entry.value, exame_entry.value, sala_entry.value
        v_sexo, v_id_pac = sexo_entry.value, id_paciente_entry.value

        inputs = get_current_inputs()

        await export_handlers.exportar_pdf_filtrado(
            page, 
            state, 
            inputs, 
            lambda msg: page.show_dialog(ft.SnackBar(ft.Text(msg), bgcolor="green")),
            lambda msg: page.show_dialog(ft.SnackBar(ft.Text(msg), bgcolor="red"))
        )


    
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

    def atualizar_apenas_tabela():
        inputs = get_current_inputs()
        view_handlers.atualizar_apenas_tabela(
            page, state, db, tabela, txt_paginacao, btn_anterior, btn_proximo, controles_paginacao, inputs
        )

    def atualizar_apenas_graficos(e=None):
        inputs = get_current_inputs()
        handle_get_dir_funcs = {
            'evolucao': handle_get_directory_path_evolucao,
            'dose_medico': handle_get_directory_path_dose_medico,
            'tempo_medico': handle_get_directory_path_tempo_medico,
            'dose_exame': handle_get_directory_path_dose_exame,
            'tempo_exame': handle_get_directory_path_tempo_exame,
        }
        view_handlers.atualizar_apenas_graficos(
            page, state, inputs, selecao_grafico, grafico_linha, grafico_barras, 
            grafico_tempo, grafico_exame, grafico_tempo_exame, container_grafico_ativo, handle_get_dir_funcs
        )

    # 3. O MAESTRO (Atualiza o que for necessário)
    def atualizar_tudo(e=None):
        atualizar_apenas_tabela()
        atualizar_apenas_graficos()

    # --- DIÁLOGOS DE EDIÇÃO (MODAIS) ---

    f_data = forms.create_text_field(label="Data", value=datetime.date.today().strftime("%Y-%m-%d"))
    f_medico = forms.create_text_field(label="Médico")
    f_exame = forms.create_dropdown(label="Exame", options=[])
    f_dose = forms.create_text_field(label="Dose", keyboard_type="number")
    f_tempo = forms.create_text_field(label="Tempo", keyboard_type="number")
    f_dap = forms.create_text_field(label="DAP", keyboard_type="number")
    f_sala = forms.create_dropdown(label="Sala", options=[])
    f_id_target = forms.create_text_field(label="Informe o ID", keyboard_type="number", width=150)
    f_paciente_id = forms.create_text_field(label="ID Paciente", keyboard_type="number")
    f_sexo = forms.create_dropdown(label="Sexo", options=[ft.dropdown.Option("F"), ft.dropdown.Option("M"), ft.dropdown.Option("NI")])

    def open_add_dialog(e):
        f_medico.value = ""; f_exame.value = None; f_dose.value = ""; f_tempo.value = ""
        f_dap.value = ""; f_paciente_id.value = ""; f_sexo.value = ""; f_sala.value = ""
        page.show_dialog(dlg_add)

    def salvar_adicao_handler(e):
        inputs = (f_data.value, f_medico.value, f_exame.value, f_dose.value, f_tempo.value, f_dap.value, f_paciente_id.value, f_sexo.value, f_sala.value)
        sucesso, msg = data_handlers.salvar_adicao(page, db, inputs)
        if sucesso:
            atualizar_tudo()
            page.show_dialog(ft.SnackBar(ft.Text(msg), bgcolor="green"))
        else:
            page.show_dialog(ft.SnackBar(ft.Text(msg), bgcolor="red"))

    dlg_add = dialogs.create_add_dialog(f_data, f_medico, f_exame, f_dose, f_tempo, f_dap, f_paciente_id, f_sexo, f_sala, salvar_adicao_handler, lambda e: page.pop_dialog())

    def open_del_dialog(e): f_id_target.value = ""; page.show_dialog(dlg_del)

    def confirmar_remocao_handler(e):
        qtd, msg = data_handlers.confirmar_remocao(page, db, f_id_target, atualizar_tudo)
        page.show_dialog(ft.SnackBar(ft.Text(msg), bgcolor="green" if qtd > 0 else "red"))

    dlg_del = dialogs.create_del_dialog(f_id_target, confirmar_remocao_handler, lambda e: page.pop_dialog())

    def open_edit_ask_id(e): f_id_target.value = ""; page.show_dialog(dlg_ask_edit)
    def carregar_para_editar_handler(e):
        data_handlers.carregar_para_editar(page, db, f_id_target, f_data, f_medico, f_exame, f_dose, f_tempo, f_dap, f_paciente_id, f_sexo, f_sala, dlg_form_edit)

    def salvar_edicao_handler(e):
        inputs = (f_data.value, f_medico.value, f_exame.value, f_dose.value, f_tempo.value, f_dap.value, f_paciente_id.value, f_sexo.value, f_sala.value)
        sucesso, msg = data_handlers.salvar_edicao(page, db, f_id_target, inputs, atualizar_tudo)
        if sucesso:
            page.show_dialog(ft.SnackBar(ft.Text(msg), bgcolor="green"))
        else:
            page.show_dialog(ft.SnackBar(ft.Text(msg), bgcolor="red"))

    dlg_ask_edit = dialogs.create_edit_ask_dialog(f_id_target, carregar_para_editar_handler, lambda e: page.pop_dialog())
    dlg_form_edit = dialogs.create_edit_form_dialog(f_data, f_medico, f_exame, f_dose, f_tempo, f_dap, f_paciente_id, f_sexo, f_sala, salvar_edicao_handler, lambda e: page.pop_dialog())

    # --- LOGICA DE GERENCIAR EXAMES ---
    
    txt_novo_exame = ft.TextField(label="Novo Tipo", expand=True, on_submit=lambda e: add_exame_click(e))
    lista_view_exames = ft.Column(scroll=ft.ScrollMode.AUTO, height=300)

    def carregar_lista_exames():
        data_handlers.carregar_lista_exames(page, db, lista_view_exames)

    def add_exame_click(e):
        data_handlers.add_exame_click_handler(page, db, txt_novo_exame, carregar_lista_exames, atualizar_dropdowns_globais)

    def remove_exame_click(nome_alvo):
        data_handlers.remove_exame_click_handler(page, db, nome_alvo, carregar_lista_exames, atualizar_dropdowns_globais)

    dlg_gerenciar_exames = dialogs.create_manage_exames_dialog(txt_novo_exame, lista_view_exames, add_exame_click, lambda e: page.pop_dialog())

    def abrir_gerenciador_exames(e):
        carregar_lista_exames() 
        page.show_dialog(dlg_gerenciar_exames)

    # --- LOGICA DE GERENCIAR EQUIPAMENTOS S/N ---

    txt_novo_equipamento = ft.TextField(label="Novo Tipo", expand=True, on_submit=lambda e: add_equipamento_click(e))
    lista_view_equipamento = ft.Column(scroll=ft.ScrollMode.AUTO, height=300)

    def carregar_lista_equipamentos():
        data_handlers.carregar_lista_equipamentos(page, db, lista_view_equipamento)

    def add_equipamento_click(e):
        data_handlers.add_equipamento_click_handler(page, db, txt_novo_equipamento, carregar_lista_equipamentos, atualizar_dropdowns_globais)

    def remove_equipamento_click(nome_alvo):
        data_handlers.remove_equipamento_click_handler(page, db, nome_alvo, carregar_lista_equipamentos, atualizar_dropdowns_globais)

    dlg_gerenciar_equipamento = dialogs.create_manage_equipamento_dialog(txt_novo_equipamento, lista_view_equipamento, add_equipamento_click, lambda e: page.pop_dialog())

    def abrir_gerenciador_equipamento(e):
        carregar_lista_equipamentos() 
        page.show_dialog(dlg_gerenciar_equipamento)

    def atualizar_dropdowns_globais():
        data_handlers.atualizar_dropdowns_globais_handler(page, db, exame_entry, f_exame, sala_entry, f_sala)

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

    dlg_pix = dialogs.create_pix_dialog(chave_pix_copia_cola, copiar_pix, fechar_pix)

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
    linha_1, linha_2 = layouts.create_filter_rows(min_dose, max_dose, min_dap_entry, max_dap_entry, min_tempo_entry, max_tempo_entry, medico_entry, exame_entry, btn_config_exames, sala_entry, btn_config_equipamento, sexo_entry, id_paciente_entry, btn_calendar, txt_datas)
    linha_3 = layouts.create_action_row(btn_file, btn_filtrar, btn_limpar, btn_upload, btn_apoio, selecao_grafico, btn_tema, btn_toggle_filtros)

    # Layout Conteúdo Tabela
    conteudo_tabela = layouts.create_table_content(btn_add, btn_edit, btn_rem, tabela, controles_paginacao, btn_csv_filter, btn_csv_full, btn_pdf)
    
    # Layout Conteúdo Dashboard
    container_grafico_ativo = ft.Container(
        padding=20,
        expand=True,
        border_radius=10,
        border=ft.Border.all(1, ft.Colors.GREY_300)
    )

    conteudo_dashboard = layouts.create_dashboard_content(container_grafico_ativo)

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
