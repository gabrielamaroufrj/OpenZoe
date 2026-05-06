import flet as ft

def create_filter_rows(min_dose, max_dose, min_dap_entry, max_dap_entry, min_tempo_entry, max_tempo_entry, medico_entry, exame_entry, btn_config_exames, sala_entry, btn_config_equipamento, sexo_entry, id_paciente_entry, btn_calendar, txt_datas):
    linha_1 = ft.Row(
        controls=[min_dose, max_dose, ft.VerticalDivider(), min_dap_entry, max_dap_entry, ft.VerticalDivider(), min_tempo_entry, max_tempo_entry, ft.VerticalDivider()], 
        scroll=ft.ScrollMode.ADAPTIVE
    )
    linha_2 = ft.Row(
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
    return linha_1, linha_2

def create_action_row(btn_file, btn_filtrar, btn_limpar, btn_upload, btn_apoio, selecao_grafico, btn_tema, btn_toggle_filtros):
    return ft.Row(
        controls=[btn_file, btn_filtrar, btn_limpar, btn_upload, btn_apoio, selecao_grafico, btn_tema, btn_toggle_filtros], 
        scroll=ft.ScrollMode.ADAPTIVE
    )

def create_table_content(btn_add, btn_edit, btn_rem, tabela, controles_paginacao, btn_csv_filter, btn_csv_full, btn_pdf):
    return ft.Column(
        controls=[
            ft.Row(controls=[btn_add, btn_edit, btn_rem], alignment=ft.MainAxisAlignment.CENTER), 
            ft.Row(scroll=ft.ScrollMode.ADAPTIVE, controls=[tabela]), 
            ft.Row(controls=[controles_paginacao, btn_csv_filter, btn_csv_full, btn_pdf])
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
