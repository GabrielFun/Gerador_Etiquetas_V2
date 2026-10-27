import os
import pandas as pd
from flask import Flask, render_template, request, send_file
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

app = Flask(__name__)

# --- CONFIGURAÇÃO DA PLANILHA ---
SHEET_ID = '1HZlgL6pQ9LrjycWqm6xIffcPdNQMiOqLmCE5dAk0VSE' 

# Você precisa olhar a URL da sua planilha e pegar o número do GID de cada aba!
GID_DESTINOS = '0' # Geralmente é 0 se for a primeira aba
GID_ORIGENS = '1181340066'

URL_DESTINOS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_DESTINOS}"
URL_ORIGENS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ORIGENS}"

# --- CONFIGURAÇÕES DE FONTE ---
try:
    pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
    pdfmetrics.registerFont(TTFont('Arial-Bold', 'arialbd.ttf'))
except Exception as e:
    print(f"AVISO: Não foi possível carregar fontes: {e}")

# --- FUNÇÕES DE MANIPULAÇÃO DE DADOS ---
def carregar_destinos():
    try:
        return pd.read_csv(URL_DESTINOS, encoding='utf-8')
    except Exception as e:
        print(f"Erro ao ler destinos: {e}")
        return pd.DataFrame(columns=['sigla', 'nome_recebedor', 'cnpj_recebedor', 'endereco_recebedor', 'cidade_recebedor', 'uf_recebedor', 'cep_recebedor', 'pais_recebedor'])

def carregar_origens():
    try:
        return pd.read_csv(URL_ORIGENS, encoding='utf-8')
    except Exception as e:
        print(f"Erro ao ler origens: {e}")
        return pd.DataFrame(columns=['sigla_origem', 'nome_origem', 'cnpj_origem', 'endereco_origem', 'cidade_origem', 'uf_origem', 'cep_origem'])

# --- ROTA PRINCIPAL (GERAR ETIQUETAS) ---
@app.route('/', methods=['GET', 'POST'])
def index():
    # 1. Carrega os Destinos
    df_destinos = carregar_destinos()
    df_destinos.columns = df_destinos.columns.str.strip()
    if not df_destinos.empty and 'sigla' in df_destinos.columns:
        df_destinos = df_destinos.dropna(subset=['sigla'])
        df_destinos['sigla'] = df_destinos['sigla'].astype(str).str.strip().str.upper()
        destinos_dict = df_destinos.set_index('sigla').to_dict('index')
    else:
        destinos_dict = {}

    # 2. Carrega as Origens
    df_origens = carregar_origens()
    df_origens.columns = df_origens.columns.str.strip()
    if not df_origens.empty and 'sigla_origem' in df_origens.columns:
        df_origens = df_origens.dropna(subset=['sigla_origem'])
        df_origens['sigla_origem'] = df_origens['sigla_origem'].astype(str).str.strip().str.upper()
        origens_dict = df_origens.set_index('sigla_origem').to_dict('index')
    else:
        origens_dict = {}

    if request.method == 'POST':
        sigla_recebida = request.form.get('sigla')
        origem_recebida = request.form.get('origem') # <--- Capturando a nova escolha!
        quantidade_str = request.form.get('quantidade')

        if not sigla_recebida or not origem_recebida or not quantidade_str:
            return "Erro: Sigla de destino, origem ou quantidade não foram informados.", 400

        sigla = sigla_recebida.strip().upper()
        sigla_origem = origem_recebida.strip().upper()
        
        try:
            quantidade = int(quantidade_str)
        except ValueError:
            return "Erro: Quantidade inválida.", 400

        if sigla not in destinos_dict:
            return f"Erro: O destino '{sigla}' não foi encontrado.", 404
            
        if sigla_origem not in origens_dict:
            return f"Erro: A origem '{sigla_origem}' não foi encontrada.", 404

        # Pegando os dados das duas abas
        dados_recebedor = destinos_dict[sigla]
        dados_expedidor = origens_dict[sigla_origem] 

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=(100 * mm, 100 * mm))
        styles = getSampleStyleSheet()
        style_normal = ParagraphStyle(name='Normal', parent=styles['Normal'], fontName='Arial', fontSize=9, leading=11)

        for i in range(1, quantidade + 1):
            margem_h = 4 * mm
            largura_maxima = 92 * mm 

            c.setFont('Arial-Bold', 33)
            c.drawString(margem_h, 82 * mm, sigla)

            numero_str = f"#{i}"
            c.setFont('Arial-Bold', 32)
            largura_texto_num = c.stringWidth(numero_str, 'Arial-Bold', 34)
            c.drawString((100 * mm) - margem_h - largura_texto_num, 82 * mm, numero_str)

            c.setFont('Arial-Bold', 34)
            c.drawString(margem_h, 68 * mm, "OVERPACK")
            c.drawString(margem_h, 57 * mm, "USED")

            # MÁGICA AQUI: O Expedidor agora é preenchido dinamicamente de acordo com a escolha!
            expedidor_text = f"<b>EXPEDIDOR:</b> {dados_expedidor['nome_origem']} ENDEREÇO: {dados_expedidor['endereco_origem']} MUNICÍPIO: {dados_expedidor['cidade_origem']} - {dados_expedidor['uf_origem']} CEP: {dados_expedidor['cep_origem']} CNPJ: {dados_expedidor['cnpj_origem']} PAÍS: BRASIL"
            expedidor_text = expedidor_text.replace('&', '&amp;')

            recebedor_text = f"<b>RECEBEDOR:</b> {dados_recebedor['nome_recebedor']} CNPJ {dados_recebedor['cnpj_recebedor']} ENDEREÇO: {dados_recebedor['endereco_recebedor']}, {dados_recebedor['cidade_recebedor']} - {dados_recebedor['uf_recebedor']} CEP: {dados_recebedor['cep_recebedor']}"
            recebedor_text = recebedor_text.replace('&', '&amp;')

            p_expedidor = Paragraph(expedidor_text, style_normal)
            p_expedidor.wrapOn(c, largura_maxima, 40 * mm)
            p_expedidor.drawOn(c, margem_h, 28 * mm)

            p_recebedor = Paragraph(recebedor_text, style_normal)
            p_recebedor.wrapOn(c, largura_maxima, 25 * mm)
            p_recebedor.drawOn(c, margem_h, 5 * mm)

            c.showPage()

        c.save()
        buffer.seek(0)
        # O nome do PDF agora informa a origem e o destino
        return send_file(buffer, as_attachment=True, download_name=f'etiquetas_{sigla_origem}_para_{sigla}_100x100.pdf', mimetype='application/pdf')

    # Passamos ambas as listas (Origens e Destinos) para o HTML construir as caixas de seleção
    return render_template('index.html', destinos=destinos_dict.keys(), origens=origens_dict.keys())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
