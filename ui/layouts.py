import flet as ft
from ui import styles

def create_filter_rows(min_dose, max_dose, min_dap_entry, max_dap_entry, min_tempo_entry, max_tempo_entry, medico_entry, exame_entry, btn_config_exames, sala_entry, btn_config_equipamento, sexo_entry, id_paciente_entry, btn_calendar, txt_datas):
    # Card 1: Dosimetry Limits
    card_dosimetry = ft.Container(
        content=ft.Column([
            ft.Text("Limites de Dosimetria", weight="bold", size=16, color=styles.PRIMARY_COLOR),
            ft.Row(
                controls=[
                    ft.Row([min_dose, max_dose]),
                    ft.VerticalDivider(),
                    ft.Row([min_dap_entry, max_dap_entry]),
                    ft.VerticalDivider(),
                    ft.Row([min_tempo_entry, max_tempo_entry]),
                ],
                scroll=ft.ScrollMode.ADAPTIVE
            )
        ]),
        padding=styles.CARD_STYLE["padding"],
        border_radius=styles.CARD_STYLE["border_radius"],
        border=styles.CARD_STYLE["border"]
    )

    # Card 2: Patient & Exam Info
    card_info = ft.Container(
        content=ft.Column([
            ft.Text("Informações do Paciente e Exame", weight="bold", size=16, color=styles.PRIMARY_COLOR),
            ft.Row(
                controls=[
                    medico_entry, 
                    ft.Row([exame_entry, btn_config_exames], spacing=0), 
                    ft.VerticalDivider(), 
                    ft.Row([sala_entry, btn_config_equipamento], spacing=0), 
                    ft.VerticalDivider(), 
                    sexo_entry, 
                    id_paciente_entry, 
                    btn_calendar, 
                    txt_datas
                ], 
                scroll=ft.ScrollMode.ADAPTIVE
            )
        ]),
        padding=styles.CARD_STYLE["padding"],
        border_radius=styles.CARD_STYLE["border_radius"],
        border=styles.CARD_STYLE["border"]
    )

    return ft.Row([card_dosimetry, card_info], scroll=ft.ScrollMode.ADAPTIVE, alignment=ft.MainAxisAlignment.START), None

def create_export_menu(btn_csv_filter, btn_csv_full, btn_pdf):
    return ft.PopupMenuButton(
        icon=ft.Icons.DOWNLOAD,
        tooltip="Exportar Dados",
        items=[
            ft.PopupMenuItem(content=ft.Text("CSV Filtrado"), icon=ft.Icons.FILTER_ALT_OFF, on_click=btn_csv_filter.on_click),
            ft.PopupMenuItem(content=ft.Text("CSV Completo"), icon=ft.Icons.DOWNLOAD, on_click=btn_csv_full.on_click),
            ft.PopupMenuItem(content=ft.Text("Relatório PDF"), icon=ft.Icons.PICTURE_AS_PDF, on_click=btn_pdf.on_click),
        ]
    )

def create_action_row(btn_file, btn_filtrar, btn_limpar, btn_upload, btn_apoio, selecao_grafico, btn_tema, btn_toggle_filtros, export_menu):
    return ft.Row(
        controls=[btn_file, btn_filtrar, btn_limpar, btn_upload, btn_apoio, selecao_grafico, btn_tema, btn_toggle_filtros, export_menu], 
        scroll=ft.ScrollMode.ADAPTIVE,
        alignment=ft.MainAxisAlignment.START
    )

def create_table_content(btn_add, btn_rem, tabela, controles_paginacao):
    return ft.Column(
        controls=[
            ft.Row(scroll=ft.ScrollMode.ADAPTIVE, controls=[tabela]), 
            ft.Row(controls=[controles_paginacao])
        ],
        scroll=ft.ScrollMode.ADAPTIVE, 
        expand=True, 
        visible=True
    )

def create_dashboard_content(container_grafico_ativo):
    return ft.Column(
        controls=[container_grafico_ativo],
        expand=True, 
        visible=False,
        scroll=ft.ScrollMode.ADAPTIVE
    )

def create_kpi_row(kpi_total, kpi_dose, kpi_tempo, kpi_dap):
    def create_kpi_card(label, value, unit, color):
        return ft.Container(
            content=ft.Column([
                ft.Text(label, size=14, color=ft.Colors.GREY_600),
                ft.Row([
                    ft.Text(value, size=24, weight="bold", color=color),
                    ft.Text(unit, size=14, color=ft.Colors.GREY_600),
                ], alignment=ft.MainAxisAlignment.START)
            ], spacing=5),
            padding=styles.PADDING_MEDIUM,
            border_radius=styles.BORDER_RADIUS_MEDIUM,
            border=ft.Border.all(1, styles.BORDER_COLOR),
            expand=True
        )

    return ft.Row(
        controls=[
            create_kpi_card("Total Exames", kpi_total, "", styles.PRIMARY_COLOR),
            create_kpi_card("Dose Média", kpi_dose, " mGy", styles.SUCCESS_COLOR),
            create_kpi_card("Tempo Médio", kpi_tempo, " min", styles.WARNING_COLOR),
            create_kpi_card("DAP Médio", kpi_dap, " μGym²", styles.ACCENT_COLOR),
        ],
        scroll=ft.ScrollMode.ADAPTIVE,
        alignment=ft.MainAxisAlignment.START
    )
