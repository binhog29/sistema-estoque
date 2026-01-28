from django.shortcuts import render
from django.http import HttpResponse
from .models import Equipamento, Movimentacao
from fpdf import FPDF
from datetime import datetime

# Tela Inicial
def index(request):
    equipamentos = Equipamento.objects.all().order_by('nome')
    return render(request, 'estoque/index.html', {'equipamentos': equipamentos})

# Nova Classe do PDF (Configuração Visual)
class PDF(FPDF):
    def header(self):
        # Título em Arial Negrito 14
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'FUTURANET - Controle de Estoque (Filial)', 0, 1, 'C')
        self.ln(5) # Pula linha

    def footer(self):
        # Rodapé com número da página
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def gerar_relatorio_pdf(request):
    # Cria o objeto PDF
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    # --- SEÇÃO 1: ESTOQUE ATUAL ---
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "1. Posicao de Estoque Atual", 0, 1, 'L')
    
    # Cabeçalho da Tabela
    pdf.set_fill_color(200, 220, 255) # Azul claro
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(80, 8, "Produto", 1, 0, 'L', 1)
    pdf.cell(40, 8, "Tipo", 1, 0, 'C', 1)
    pdf.cell(30, 8, "Qtd", 1, 0, 'C', 1)
    pdf.cell(40, 8, "Status", 1, 1, 'C', 1)

    # Dados da Tabela
    pdf.set_font("Arial", size=9)
    equipamentos = Equipamento.objects.all().order_by('nome')
    
    for item in equipamentos:
        pdf.cell(80, 8, f"{item.nome[:35]}", 1) # Corta nome longo
        pdf.cell(40, 8, item.get_tipo_display(), 1, 0, 'C')
        pdf.cell(30, 8, str(item.quantidade), 1, 0, 'C')
        
        # Lógica para mostrar se está baixo
        status = "BAIXO" if item.quantidade <= item.minimo else "Normal"
        pdf.cell(40, 8, status, 1, 1, 'C')

    pdf.ln(10) # Espaço grande

    # --- SEÇÃO 2: ÚLTIMAS MOVIMENTAÇÕES ---
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "2. Historico Recente (Ultimos 20)", 0, 1, 'L')

    # Cabeçalho
    pdf.set_fill_color(230, 230, 230) # Cinza
    pdf.set_font("Arial", 'B', 8)
    pdf.cell(35, 8, "Data/Hora", 1, 0, 'L', 1)
    pdf.cell(40, 8, "Tecnico", 1, 0, 'L', 1)
    pdf.cell(20, 8, "Acao", 1, 0, 'C', 1)
    pdf.cell(60, 8, "Item", 1, 0, 'L', 1)
    pdf.cell(35, 8, "Obs", 1, 1, 'L', 1)

    # Dados
    pdf.set_font("Arial", size=8)
    movimentacoes = Movimentacao.objects.all().order_by('-data')[:20]
    
    for mov in movimentacoes:
        data_fmt = mov.data.strftime("%d/%m %H:%M")
        pdf.cell(35, 8, data_fmt, 1)
        pdf.cell(40, 8, mov.tecnico.username, 1)
        pdf.cell(20, 8, mov.tipo, 1, 0, 'C')
        pdf.cell(60, 8, mov.equipamento.nome[:30], 1)
        obs_texto = mov.obs if mov.obs else "-"
        pdf.cell(35, 8, obs_texto[:20], 1, 1)

    # Gerar e Retornar o PDF
    response = HttpResponse(content_type='application/pdf')
    # O comando 'attachment' força o download.
    response['Content-Disposition'] = 'attachment; filename="relatorio_estoque.pdf"'
    
    # Gera o binário do PDF
    pdf_output = pdf.output(dest='S').encode('latin-1', 'ignore')
    response.write(pdf_output)
    
    return response
