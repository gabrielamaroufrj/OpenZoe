# reports/pdf_export.py
import os
from fpdf import FPDF

class RelatorioPDF(FPDF):
    def header(self):
        # Sobe um nível para achar a pasta raiz do projeto e buscar a logo
        diretorio_atual = os.path.dirname(os.path.abspath(__file__))
        diretorio_raiz = os.path.dirname(diretorio_atual)
        caminho_logo = os.path.join(diretorio_raiz, "assets", "icon.png")
        
        if os.path.exists(caminho_logo):
            self.image(caminho_logo, x=10, y=8, w=12) 

        self.set_font("helvetica", "B", 16)
        self.set_text_color(0, 51, 102) 
        self.cell(0, 10, "OpenZoe - Relatório de Dosimetria e Qualidade", align="C", new_x="LMARGIN", new_y="NEXT")
        
        self.line(10, 24, 200, 24) 
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Página {self.page_no()}", align="C")
