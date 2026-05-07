import flet as ft
import flet_charts as fch
import math
from core import database as db
from core import analytics
from ui import charts_ui, styles
from core.utils import formatar_data, formatar_tempo

def atualizar_apenas_tabela(page, state, db_module, tabela, txt_paginacao, btn_anterior, btn_proximo, controles_paginacao, inputs, on_edit=None, on_delete=None):
    v_min, v_max = inputs['min_dose'], inputs['max_dose']
    v_min_t, v_max_t = inputs['min_tempo'], inputs['max_tempo']
    v_min_dap, v_max_dap = inputs['min_dap'], inputs['max_dap']
    v_med, v_exm, v_sala = inputs['medico'], inputs['exame'], inputs['sala']
    v_sexo, v_id_pac = inputs['sexo'], inputs['id_paciente']
    
    offset = (state.pagina_atual - 1) * state.itens_por_pagina
    
    dados, total_registros = db_module.carregar_dados_banco(
        state.data_inicio, state.data_final, v_min, v_max, v_med, v_exm, v_min_t, v_max_t, v_min_dap, v_max_dap, v_sala, v_sexo, v_id_pac, 
        state.itens_por_pagina, offset
    )
    
    tabela.rows.clear()
    
    for i, row in enumerate(dados):
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
        
        # Row Actions
        btn_edit_row = ft.IconButton(icon=ft.Icons.EDIT, icon_size=16, tooltip="Editar", on_click=lambda e, r_id=row[0]: on_edit(r_id) if on_edit else None)
        btn_del_row = ft.IconButton(icon=ft.Icons.DELETE, icon_size=16, tooltip="Remover", icon_color=styles.DANGER_COLOR, on_click=lambda e, r_id=row[0]: on_delete(r_id) if on_delete else None)
        celula_acoes = ft.Row([btn_edit_row, btn_del_row], alignment=ft.MainAxisAlignment.CENTER, spacing=0)

        # No zebra striping
        row_color = None

        tabela.rows.append(ft.DataRow(
            cells=[
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
                ft.DataCell(celula_acoes),
            ],
            color=row_color
        ))
    
    total_paginas = math.ceil(total_registros / state.itens_por_pagina) if total_registros > 0 else 1
    txt_paginacao.value = f"Página {state.pagina_atual} de {total_paginas} (Total: {total_registros})"
    btn_anterior.disabled = (state.pagina_atual == 1)
    btn_proximo.disabled = (state.pagina_atual >= total_paginas)
    tabela.update()
    controles_paginacao.update()

def atualizar_apenas_graficos(page, state, inputs, selecao_grafico, grafico_linha, grafico_barras, grafico_tempo, grafico_exame, grafico_tempo_exame, container_grafico_ativo, handle_get_dir_funcs):
    tipo = selecao_grafico.value
    
    grafico_obj = None
    titulo_grafico = ""
    funcao_salvar = None

    if tipo == "Evolução Temporal (Linha)":
        titulo_grafico = "Evolução Temporal (Exames/Dia)"
        funcao_salvar = handle_get_dir_funcs['evolucao']
        
        dados_evo, modo_mult_evo = analytics.calcular_evolucao_temporal(
            state.data_inicio, state.data_final, 
            inputs['min_dose'], inputs['max_dose'], inputs['medico'], inputs['exame'], 
            inputs['min_tempo'], inputs['max_tempo'], inputs['min_dap'], inputs['max_dap'], 
            inputs['sala'], inputs['sexo'], inputs['id_paciente']
        )
        
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
        funcao_salvar = handle_get_dir_funcs['dose_medico']
        res = analytics.calcular_media_medico(
            state.data_inicio, state.data_final, 
            inputs['min_dose'], inputs['max_dose'], inputs['medico'], inputs['exame'], 
            inputs['min_tempo'], inputs['max_tempo'], inputs['min_dap'], inputs['max_dap'], 
            inputs['sala'], inputs['sexo'], inputs['id_paciente']
        )
        charts_ui.popular_grafico_simples(res, grafico_barras, [ft.Colors.GREEN, ft.Colors.BLUE, ft.Colors.RED, ft.Colors.ORANGE, ft.Colors.PURPLE])
        grafico_obj = grafico_barras

    elif tipo == "Média de Tempo por Médico":
        titulo_grafico = "Média Tempo/Médico"
        funcao_salvar = handle_get_dir_funcs['tempo_medico']
        res = analytics.calcular_media_tempo_medico(
            state.data_inicio, state.data_final, 
            inputs['min_dose'], inputs['max_dose'], inputs['medico'], inputs['exame'], 
            inputs['min_tempo'], inputs['max_tempo'], inputs['min_dap'], inputs['max_dap'], 
            inputs['sala'], inputs['sexo'], inputs['id_paciente']
        )
        charts_ui.popular_grafico_simples(res, grafico_tempo, [ft.Colors.DEEP_ORANGE, ft.Colors.INDIGO, ft.Colors.AMBER], " min")
        grafico_obj = grafico_tempo

    elif tipo == "Média de Dose por Exame":
        titulo_grafico = "Média Dose/Exame"
        funcao_salvar = handle_get_dir_funcs['dose_exame']
        res, modo_mult = analytics.calcular_media_exame(
            state.data_inicio, state.data_final, 
            inputs['min_dose'], inputs['max_dose'], inputs['medico'], inputs['exame'], 
            inputs['min_tempo'], inputs['max_tempo'], inputs['min_dap'], inputs['max_dap'], 
            inputs['sala'], inputs['sexo'], inputs['id_paciente']
        )
        charts_ui.popular_grafico_agrupado(res, grafico_exame, modo_mult, [ft.Colors.BLUE, ft.Colors.RED, ft.Colors.GREEN])
        grafico_obj = grafico_exame

    elif tipo == "Média de Tempo por Exame":
        titulo_grafico = "Média Tempo/Exame"
        funcao_salvar = handle_get_dir_funcs['tempo_exame']
        res, modo_mult = analytics.calcular_media_tempo_exame(
            state.data_inicio, state.data_final, 
            inputs['min_dose'], inputs['max_dose'], inputs['medico'], inputs['exame'], 
            inputs['min_tempo'], inputs['max_tempo'], inputs['min_dap'], inputs['max_dap'], 
            inputs['sala'], inputs['sexo'], inputs['id_paciente']
        )
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
