
from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.colors import green, yellow, red, black, orange
import os
import logging
from io import BytesIO

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///taxistas.db'
app.secret_key = os.environ.get('SECRET_KEY', 'defaultsecretkey')  # Variável de ambiente para chave secreta
PASSWORD = os.environ.get('ADMIN_PASSWORD', 'defaultpassword')  # Variável de ambiente para senha de administrador

db = SQLAlchemy(app)

# Senha definida para a ação de zerar histórico
#PASSWORD = 'Nika@102550'

# Configuração de logging
logging.basicConfig(level=logging.DEBUG)

class Data_hora():
    @staticmethod
    def _data_hora():
        fuso_BR = pytz.timezone('Brazil/East')
        horario_BR = datetime.now(fuso_BR)
        return horario_BR

class Taxista(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    condutax = db.Column(db.String(10), nullable=False)
    vencimento_condutax = db.Column(db.DateTime, nullable=True)
    placa_veiculo = db.Column(db.String(8), nullable=False)
    veiculo = db.Column(db.String(50), nullable=True)
    licenciamento = db.Column(db.String(20), nullable=True)
    dt_cadastro = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'Taxista({self.nome}, {self.condutax})'

class HistoricoAcao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo_acao = db.Column(db.String(50), nullable=False)
    nome = db.Column(db.String(150), nullable=False)
    placa_veiculo = db.Column(db.String(8), nullable=False)
    condutax = db.Column(db.String(10), nullable=False)
    data_hora = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'HistoricoAcao({self.tipo_acao}, {self.nome}, {self.placa_veiculo}, {self.condutax}, {self.data_hora})'

def registrar_historico(tipo_acao, taxista):
    historico = HistoricoAcao(
        tipo_acao=tipo_acao,
        nome=taxista.nome,
        placa_veiculo=taxista.placa_veiculo,
        condutax=taxista.condutax,
        data_hora=Data_hora._data_hora()
    )
    db.session.add(historico)
    db.session.commit()

def cor_tipo_acao(tipo_acao):
    if tipo_acao == 'Cadastro':
        return green
    elif tipo_acao == 'Editado':
        return orange
    elif tipo_acao == 'Deleção':
        return red
    return black

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome_formatado = request.form['nome'].title()  # Formata o nome
        taxista = Taxista(
            nome=nome_formatado,
            telefone=request.form['telefone'],
            condutax=request.form['condutax'],
            vencimento_condutax=datetime.strptime(request.form['vencimento_condutax'], '%Y-%m-%d'),
            placa_veiculo=request.form['placa_veiculo'],
            veiculo=request.form['veiculo'],
            licenciamento=request.form['licenciamento'],
            dt_cadastro=Data_hora._data_hora()
        )
        try:
            db.session.add(taxista)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logging.error(f'Erro ao adicionar taxista: {e}')
            flash('Erro ao adicionar taxista. Por favor, tente novamente.')

        registrar_historico('Cadastro', taxista)
        return redirect(url_for('lista_taxistas'))
    return render_template('cadastro.html')

@app.route('/lista_taxistas')
def lista_taxistas():
    taxistas = Taxista.query.all()
    if not taxistas:
        flash('Nenhum taxista encontrado no sistema.', 'warning')
    return render_template('lista_taxistas.html', taxistas=taxistas)
    

@app.route('/editar_taxista/<int:id>', methods=['GET', 'POST'])
def editar_taxista(id):
    taxista = Taxista.query.get_or_404(id)
    if request.method == 'POST':
        taxista.nome = request.form['nome']
        taxista.telefone = request.form['telefone']
        taxista.condutax = request.form['condutax']
        taxista.vencimento_condutax = datetime.strptime(request.form['vencimento_condutax'], '%Y-%m-%d')
        taxista.placa_veiculo = request.form['placa_veiculo']
        taxista.veiculo = request.form['veiculo']
        taxista.licenciamento = request.form['licenciamento']
        db.session.commit()
        registrar_historico('Editado', taxista)
        return redirect(url_for('lista_taxistas'))
    return render_template('editar.html', taxista=taxista)

@app.route('/deletar_taxista/<int:id>')
def deletar_taxista(id):
    taxista = Taxista.query.get(id)
    if taxista:
        registrar_historico('Deleção', taxista)
        db.session.delete(taxista)
        db.session.commit()
    return redirect(url_for('lista_taxistas'))

@app.route('/historico')
def historico():
    historico_acoes = HistoricoAcao.query.all()
    return render_template('historico.html', historico_acoes=historico_acoes)


@app.route('/gerar_relatorio_pdf')
def gerar_relatorio_pdf():
    historico_acoes = HistoricoAcao.query.all()
    data_hora_atual = datetime.now().strftime('%d-%m-%Y__%Hh%Mmin') 
    relatorio_path = os.path.join('instance', f'relatorio_historico_{data_hora_atual}.pdf')
    
    c = canvas.Canvas(relatorio_path, pagesize=landscape(letter))
    width, height = landscape(letter)
    
    # Centralizar o título
    titulo = "Relatório de Histórico de Ações"
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2.0, height - 50, titulo)

    # Cabeçalhos
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, height - 80, "Tipo de Ação")
    c.drawString(130, height - 80, "Nome")
    c.drawString(380, height - 80, "Placa")
    c.drawString(480, height - 80, "Condutax")
    c.drawString(580, height - 80, "Data e Hora")

    y = height - 100
    for acao in historico_acoes:
        cor = cor_tipo_acao(acao.tipo_acao)
        c.setFillColor(cor)
        c.drawString(30, y, acao.tipo_acao)
        c.drawString(130, y, acao.nome)
        c.drawString(380, y, acao.placa_veiculo)
        c.drawString(480, y, acao.condutax)
        c.drawString(580, y, acao.data_hora.strftime('%d/%m/%Y %H:%M:%S'))
        y -= 20

    c.save()
    return send_file(relatorio_path, as_attachment=True)


@app.route('/confirmar_zerar_historico', methods=['POST'])
def confirmar_zerar_historico():
    senha = request.form['senha']
    logging.debug(f'Senha recebida: {senha}')
    if senha == PASSWORD:
        logging.debug('Senha correta. Gerando relatório e zerando histórico.')
        gerar_relatorio_pdf()
        zerar_historico()
        flash('Senha inserida corretamente')
        return redirect(url_for('zerar_historico'))
    else:
        flash('Senha incorreta. Tente novamente.')
        logging.debug('Senha incorreta.')
        return redirect(url_for('historico'))
    

@app.route('/zerar_historico')
def zerar_historico():
    try:
        logging.debug('Iniciando processo de zerar histórico de ações.')
        historico_acoes = HistoricoAcao.query.all()
        if historico_acoes:
            db.session.query(HistoricoAcao).delete()
            db.session.commit()
            logging.debug('Histórico de ações zerado com sucesso.')
        else:
            logging.debug('Nenhum registro encontrado no histórico.')
    except Exception as e:
        logging.error(f'Erro ao zerar histórico: {e}')
        flash('Ocorreu um erro ao tentar zerar o histórico. Por favor, tente novamente.')
    return redirect(url_for('historico'))


@app.route('/consulta', methods=['GET', 'POST'])
def consulta():
    if request.method == 'POST':
        data_inicial = request.form['data_inicial']
        data_final = request.form['data_final']
        logging.debug(f'Data Inicial: {data_inicial}, Data Final: {data_final}')
        return redirect(url_for('consulta_resultados', data_inicial=data_inicial, data_final=data_final))
    
    return render_template('consulta.html')

@app.route('/consulta_resultados', methods=['GET', 'POST'])
def consulta_resultados():
    data_inicial = request.args.get('data_inicial')
    data_final = request.args.get('data_final')
    
    if data_inicial and data_final:
        try:
            # Verificar se as datas estão no formato correto 'dd/mm/yyyy'
            datetime.strptime(data_inicial, '%d/%m/%Y')
            datetime.strptime(data_final, '%d/%m/%Y')
        except ValueError as e:
            logging.error(f"Erro ao converter data: {e}")
            return "Formato de data inválido. Use dd/mm/yyyy."
        
        # Converter as datas para datetime
        try:
            data_inicial_dt = datetime.strptime(data_inicial, '%d/%m/%Y')
            data_final_dt = datetime.strptime(data_final, '%d/%m/%Y')
        except ValueError as e:
            logging.error(f"Erro ao converter data: {e}")
            return "Data inválida. Por favor, insira uma data válida no formato dd/mm/yyyy."
        
        # Consultar e ordenar os resultados
        taxistas = Taxista.query.filter(Taxista.vencimento_condutax >= data_inicial_dt,
                                        Taxista.vencimento_condutax <= data_final_dt) \
                                .order_by(Taxista.vencimento_condutax.asc()).all()
        return render_template('consulta.html', taxistas=taxistas, data_inicial=data_inicial, data_final=data_final)
    else:
        return "Datas de início e fim não fornecidas."


@app.route('/gerar_pdf', methods=['POST'])
def gerar_pdf():
    data_inicial = request.form['data_inicial']
    data_final = request.form['data_final']
    
    if data_inicial and data_final:
        try:
            # Verificar se as datas estão no formato correto 'dd/mm/yyyy'
            datetime.strptime(data_inicial, '%d/%m/%Y')
            datetime.strptime(data_final, '%d/%m/%Y')
        except ValueError as e:
            logging.error(f"Erro ao converter data: {e}")
            return "Formato de data inválido. Use dd/mm/yyyy."
        
        # Converter as datas para datetime
        try:
            data_inicial_dt = datetime.strptime(data_inicial, '%d/%m/%Y')
            data_final_dt = datetime.strptime(data_final, '%d/%m/%Y')
        except ValueError as e:
            logging.error(f"Erro ao converter data: {e}")
            return "Data inválida. Por favor, insira uma data válida no formato dd/mm/yyyy."
        
        # Consultar e ordenar os resultados
        taxistas = Taxista.query.filter(Taxista.vencimento_condutax >= data_inicial_dt,
                                        Taxista.vencimento_condutax <= data_final_dt) \
                                .order_by(Taxista.vencimento_condutax.asc()).all()
        
        if not taxistas:
            return "Nenhum resultado encontrado para as datas fornecidas."
        
        # Gerar PDF em modo paisagem
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=landscape(letter))
        pdf.setTitle("Relatório de Taxistas")
        
        # Configurações de layout
        pdf.setFont("Helvetica-Bold", 14)
        x = 20
        y = 580
        line_height = 20
        col_widths = [200, 100, 60, 80, 130, 100, 120]  # Ajustar larguras das colunas
        
        # Adicionar o título e a linha dupla
        pdf.drawString(x, y, f"Relatório de Taxistas de {data_inicial} até {data_final}")
        y -= line_height
        y -= line_height  # Mover o título uma linha abaixo
        pdf.setLineWidth(2)
        pdf.line(x, y, 770, y)  # Linha dupla
        pdf.setLineWidth(0.5)
        pdf.line(x, y - 2, 770, y - 2)  # Linha dupla
        y -= line_height
        
        # Adicionar cabeçalho da tabela
        pdf.setFont("Helvetica-Bold", 12)
        col_x = x
        headers = ["Nome", "Telefone", "Placa", "Condutax", "Vencto Condutax", "Veículo", "Licenciamento"]
        for header, width in zip(headers, col_widths):
            pdf.drawString(col_x, y, header)
            col_x += width
        y -= line_height
        
        pdf.setFont("Helvetica", 10)
        # Adicionar conteúdo ao PDF
        for taxista in taxistas:
            col_x = x
            campos = [taxista.nome, taxista.telefone, taxista.placa_veiculo, taxista.condutax, taxista.vencimento_condutax.strftime('%d/%m/%Y'), taxista.veiculo, taxista.licenciamento]
            for campo, width in zip(campos, col_widths):
                pdf.drawString(col_x, y, campo)
                col_x += width
            y -= line_height
            if y < 50:
                pdf.showPage()
                pdf.setFont("Helvetica", 10)
                y = 580
        
        pdf.showPage()
        pdf.save()
        
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name="relatorio_taxistas.pdf", mimetype='application/pdf')
    else:
        return "Datas de início e fim não fornecidas."
    
    

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

