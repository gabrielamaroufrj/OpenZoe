# ui/charts_ui.py
import flet as ft
import flet_charts as fch

def criar_tabela_dados():
    colunas = [
        ft.DataColumn(ft.Text("ID"), numeric=True), 
        ft.DataColumn(ft.Text("Data")), 
        ft.DataColumn(ft.Text("Médico")),
        ft.DataColumn(ft.Text("Exame")),  
        ft.DataColumn(ft.Text("Tempo"), numeric=True),
        ft.DataColumn(ft.Text("ID Paciente"), numeric=True), 
        ft.DataColumn(ft.Text("Sexo")), 
        ft.DataColumn(ft.Text("Sala")),
        ft.DataColumn(ft.Text(fr"DAP (μGym²)"), numeric=True),
        ft.DataColumn(ft.Text("Dose (mGy)"), numeric=True),
    ]
    return ft.DataTable(
        columns=colunas, 
        rows=[], 
        border=ft.Border.all(1, "grey"), 
        border_radius=ft.BorderRadius.all(10), 
        vertical_lines=ft.border.BorderSide(1, "grey"), 
        data_row_max_height=60
    )

def criar_grafico_base(titulo):
    return fch.BarChart(
        expand=True, interactive=True, max_y=100,
        border=ft.Border.all(1, ft.Colors.GREY_400),
        horizontal_grid_lines=fch.ChartGridLines(color=ft.Colors.GREY_300, width=1, dash_pattern=[3, 3]),
        tooltip=fch.BarChartTooltip(bgcolor=ft.Colors.with_opacity(0.95, ft.Colors.WHITE)),
        left_axis=fch.ChartAxis(label_size=40, title=ft.Text(titulo, weight="bold"), title_size=20, labels=[]),
        bottom_axis=fch.ChartAxis(label_size=40, labels=[]), groups=[]
    )

def criar_grafico_linha_base(titulo):
    return fch.LineChart(
        expand=True, min_y=0, min_x=0,
        border=ft.Border.all(1, ft.Colors.GREY_400),
        horizontal_grid_lines=fch.ChartGridLines(interval=1, color=ft.Colors.GREY_300, width=1),
        tooltip=fch.LineChartTooltip(bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.WHITE)),
        left_axis=fch.ChartAxis(label_size=40, title=ft.Text(titulo, weight="bold"), title_size=20),
        bottom_axis=fch.ChartAxis(label_size=40), data_series=[] 
    )

def popular_grafico_simples(dados_tupla, grafico, cores, unit_suffix=""):
    grp = []; lbl_x = []; max_val = 0
    if not dados_tupla: dados_tupla = [] 
    
    for i, row in enumerate(dados_tupla):
        nome = row[0]
        val = row[1] if row[1] else 0
        mn = row[2] if row[2] else 0
        mx = row[3] if row[3] else 0
        qt = row[4] if row[4] else 0

        if val > max_val: max_val = val
        nome_display = nome[:8] + ".." if nome and len(nome) > 10 else (nome if nome else "N/A")
        
        tooltip_txt = f"{nome}\nMédia: {val:.2f}{unit_suffix}\nMin: {mn:.2f} | Max: {mx:.2f}\nQtd: {qt}"
        
        grp.append(fch.BarChartGroup(x=i, rods=[fch.BarChartRod(from_y=0, to_y=val, width=40 , color=cores[i % len(cores)], tooltip=tooltip_txt, border_radius=0)]))
        lbl_x.append(fch.ChartAxisLabel(value=i, label=ft.Container(ft.Text(nome_display, size=10, weight="bold"), padding=ft.Padding.all(10))))
    
    teto = max_val * 1.4 if max_val > 0 else 10
    grafico.groups = grp; grafico.max_y = teto; grafico.bottom_axis.labels = lbl_x

def popular_grafico_agrupado(res_dados, grafico, modo_multiplo, cores_base, unit_suffix=""):
    if not modo_multiplo:
        popular_grafico_simples(res_dados, grafico, cores_base, unit_suffix)
    else:
        if not res_dados: res_dados = []
        medicos_unicos = sorted(list(set(row[1] for row in res_dados)))
        exames_unicos = sorted(list(set(row[0] for row in res_dados)))
        
        dados_map = {ex: {} for ex in exames_unicos}
        max_val = 0
        for ex, med, val, mn, mx, qt in res_dados:
            if val > max_val: max_val = val
            dados_map[ex][med] = (val, mn, mx, qt)
        
        mapa_cores = {med: cores_base[i % len(cores_base)] for i, med in enumerate(medicos_unicos)}
        grupos = []; eixo_x = []
        
        for i, exame in enumerate(exames_unicos):
            barras = []
            for medico in medicos_unicos:
                dados_med = dados_map[exame].get(medico, (0, 0, 0, 0))
                valor, mn, mx, qt = dados_med
                tooltip_txt = f"{medico}\nMédia: {valor:.2f}{unit_suffix}\nMin: {mn:.2f} | Max: {mx:.2f}\nQtd: {qt}"
                barras.append(fch.BarChartRod(from_y=0, to_y=valor, width=15, color=mapa_cores[medico], tooltip=tooltip_txt, border_radius=0))
            
            grupos.append(fch.BarChartGroup(x=i, rods=barras))
            eixo_x.append(fch.ChartAxisLabel(value=i, label=ft.Container(ft.Text(exame, size=10, weight="bold"), padding=ft.Padding.all(10))))

        teto = max_val * 1.4 if max_val > 0 else 10
        grafico.groups = grupos; grafico.bottom_axis.labels = eixo_x; grafico.max_y = teto
        grafico.left_axis.title.value = f"Valores ({' | '.join(medicos_unicos)})"
