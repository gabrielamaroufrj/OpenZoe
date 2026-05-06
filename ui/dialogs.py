import flet as ft

def create_add_dialog(f_data, f_medico, f_exame, f_dose, f_tempo, f_dap, f_paciente_id, f_sexo, f_sala, on_save, on_cancel):
    return ft.AlertDialog(
        title=ft.Text("Novo"),
        content=ft.Column(
            [f_data, f_medico, f_exame, f_dose, f_tempo, f_dap, f_paciente_id, f_sexo, f_sala],
            height=600,
            scroll=ft.ScrollMode.ADAPTIVE
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=on_cancel),
            ft.FilledButton("Salvar", on_click=on_save)
        ]
    )

def create_del_dialog(f_id_target, on_confirm, on_cancel):
    return ft.AlertDialog(
        title=ft.Text("Remover"),
        content=ft.Column([ft.Text("ID para excluir:"), f_id_target], height=100),
        actions=[
            ft.TextButton("Cancelar", on_click=on_cancel),
            ft.FilledButton(
                "Remover",
                style=ft.ButtonStyle(bgcolor=ft.Colors.RED, color=ft.Colors.WHITE),
                on_click=on_confirm
            )
        ]
    )

def create_edit_ask_dialog(f_id_target, on_search, on_cancel):
    return ft.AlertDialog(
        title=ft.Text("Editar"),
        content=ft.Column([ft.Text("ID para editar:"), f_id_target], height=100),
        actions=[
            ft.TextButton("Cancelar", on_click=on_cancel),
            ft.FilledButton("Buscar", on_click=on_search)
        ]
    )

def create_edit_form_dialog(f_data, f_medico, f_exame, f_dose, f_tempo, f_dap, f_paciente_id, f_sexo, f_sala, on_save, on_cancel):
    return ft.AlertDialog(
        title=ft.Text("Editando"),
        content=ft.Column(
            [f_data, f_medico, f_exame, f_dose, f_tempo, f_dap, f_paciente_id, f_sexo, f_sala],
            height=600,
            scroll=ft.ScrollMode.AUTO
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=on_cancel),
            ft.FilledButton("Salvar", on_click=on_save)
        ]
    )

def create_manage_exames_dialog(txt_novo_exame, lista_view_exames, on_add, on_close):
    return ft.AlertDialog(
        title=ft.Text("Gerenciar Lista de Exames"),
        content=ft.Container(
            width=400,
            height=400,
            content=ft.Column([
                ft.Row([txt_novo_exame, ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_color="green", on_click=on_add)]),
                ft.Divider(),
                ft.Text("Exames Cadastrados:", weight="bold"),
                lista_view_exames,
            ])
        ),
        actions=[ft.TextButton("Fechar", on_click=on_close)]
    )

def create_manage_equipamento_dialog(txt_novo_equipamento, lista_view_equipamento, on_add, on_close):
    return ft.AlertDialog(
        title=ft.Text("Gerenciar Lista de Equipamentos"),
        content=ft.Container(
            width=400,
            height=400,
            content=ft.Column([
                ft.Row([txt_novo_equipamento, ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_color="green", on_click=on_add)]),
                ft.Divider(),
                ft.Text("Equipamentos Cadastrados:", weight="bold"),
                lista_view_equipamento,
            ])
        ),
        actions=[ft.TextButton("Fechar", on_click=on_close)]
    )

def create_pix_dialog(chave_pix, on_copy, on_close):
    return ft.AlertDialog(
        title=ft.Text("Apoie o Projeto"),
        content=ft.Column([
            ft.Text("Este software é gratuito e de código aberto (Open Source). Ele foi desenvolvido para auxiliar profissionais de radiologia e continuará sendo livre para sempre. Se este programa economizou seu tempo ou ajudou no seu trabalho, considere fazer uma doação voluntária para manter o desenvolvimento ativo e pagar os cafés das madrugadas de programação."),
            ft.Button(content="Ver no GitHub", icon=ft.Icons.CODE, url="https://github.com/gabrielamaroufrj/OpenZoe.git"),
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
                value=chave_pix,
                read_only=True,
                text_size=12,
                height=40,
                border_radius=10,
            )
        ], tight=True, width=600, height=650, alignment="center", scroll=ft.ScrollMode.ADAPTIVE),
        actions=[
            ft.TextButton("Fechar", on_click=on_close),
            ft.FilledButton("Copiar Chave", icon=ft.Icons.COPY, on_click=on_copy),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
