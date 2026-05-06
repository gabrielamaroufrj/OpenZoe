import flet as ft
from core import database as db

def salvar_adicao(page, db_module, inputs):
    if db_module.inserir_exame(inputs):
        page.pop_dialog()
        return True, "Adição Confirmada"
    return False, "Erro!"

def confirmar_remocao(page, db_module, f_id_target, on_update):
    entrada = f_id_target.value
    if not entrada:
        return 0, "Nenhum ID informado"
    
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
        if db_module.deletar_exame(id_limpo):
            removidos_qtd += 1
    
    if removidos_qtd > 0:
        page.pop_dialog()
        on_update()
        return removidos_qtd, f"Sucesso: {removidos_qtd} itens removidos!"
    return 0, "Nenhum ID válido encontrado ou erro ao deletar."

def carregar_para_editar(page, db_module, f_id_target, f_data, f_medico, f_exame, f_dose, f_tempo, f_dap, f_paciente_id, f_sexo, f_sala, dlg_form_edit):
    d = db_module.buscar_exame_por_id(f_id_target.value) if f_id_target.value else None
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
        return True
    else:
        page.show_dialog(ft.SnackBar(ft.Text("Não encontrado"), bgcolor="red"))
        return False

def salvar_edicao(page, db_module, f_id_target, inputs, on_update):
    if db_module.atualizar_exame(f_id_target.value, inputs):
        page.pop_dialog()
        on_update()
        return True, "Editado!"
    return False, "Erro!"

def carregar_lista_exames(page, db_module, lista_view_exames):
    lista_view_exames.controls.clear()
    conn = db_module.conectar()
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
                        on_click=lambda e, n=nome: remove_exame_click_handler(page, db_module, n, lambda: carregar_lista_exames(page, db_module, lista_view_exames), lambda: atualizar_dropdowns_globais_handler(page, db_module, None, None, None, None))
                    )
                ], alignment="spaceBetween")
            )
    except Exception as e:
        print(f"Erro ao carregar lista: {e}")
    page.update()

def add_exame_click_handler(page, db_module, txt_novo_exame, on_update_list, on_update_dropdowns):
    if not txt_novo_exame.value: return
    if db_module.adicionar_tipo_exame_db(txt_novo_exame.value):
        txt_novo_exame.value = ""
        on_update_list()
        on_update_dropdowns()
        page.update()

def remove_exame_click_handler(page, db_module, nome_alvo, on_update_list, on_update_dropdowns):
    if db_module.remover_tipo_exame_db(nome_alvo):
        on_update_list()
        on_update_dropdowns()
        page.update()

def carregar_lista_equipamentos(page, db_module, lista_view_equipamento):
    lista_view_equipamento.controls.clear()
    conn = db_module.conectar()
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
                        on_click=lambda e, n=nome: remove_equipamento_click_handler(page, db_module, n, lambda: carregar_lista_equipamentos(page, db_module, lista_view_equipamento), lambda: atualizar_dropdowns_globais_handler(page, db_module, None, None, None, None))
                    )
                ], alignment="spaceBetween")
            )
    except Exception as e:
        print(f"Erro ao carregar lista: {e}")
    page.update()

def add_equipamento_click_handler(page, db_module, txt_novo_equipamento, on_update_list, on_update_dropdowns):
    if not txt_novo_equipamento.value: return
    if db_module.adicionar_tipo_equipamento_db(txt_novo_equipamento.value):
        txt_novo_equipamento.value = ""
        on_update_list()
        on_update_dropdowns()
        page.update()

def remove_equipamento_click_handler(page, db_module, nome_alvo, on_update_list, on_update_dropdowns):
    if db_module.remover_tipo_equipamento_db(nome_alvo):
        on_update_list()
        on_update_dropdowns()
        page.update()

def atualizar_dropdowns_globais_handler(page, db_module, exame_entry, f_exame, sala_entry, f_sala):
    lista_atualizada_exm = db_module.inicializar_tipos_exames()
    lista_atualizada_eqp = db_module.inicializar_equipamento()
    novas_opcoes_exm = [ft.dropdown.Option(x) for x in lista_atualizada_exm]
    novas_opcoes_eqp = [ft.dropdown.Option(x) for x in lista_atualizada_eqp]
    if exame_entry: exame_entry.options = novas_opcoes_exm
    if f_exame: f_exame.options = novas_opcoes_exm
    if sala_entry: sala_entry.options = novas_opcoes_eqp
    if f_sala: f_sala.options = novas_opcoes_eqp
    page.update()
