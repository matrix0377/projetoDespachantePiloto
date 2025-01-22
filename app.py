
from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import green, yellow, red, black, orange
import os
import logging

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
    
    c = canvas.Canvas(relatorio_path, pagesize=letter)
    width, height = letter
    
    # Centralizar o título
    titulo = "Relatório de Histórico de Ações"
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2.0, height - 50, titulo)

    # Cabeçalhos
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, height - 80, "Tipo de Ação")
    c.drawString(130, height - 80, "Nome")
    c.drawString(230, height - 80, "Placa")
    c.drawString(330, height - 80, "Condutax")
    c.drawString(430, height - 80, "Data e Hora")

    y = height - 100
    for acao in historico_acoes:
        cor = cor_tipo_acao(acao.tipo_acao)
        c.setFillColor(cor)
        c.drawString(30, y, acao.tipo_acao)        
        c.drawString(130, y, acao.nome)
        c.drawString(230, y, acao.placa_veiculo)
        c.drawString(330, y, acao.condutax)
        c.drawString(430, y, acao.data_hora.strftime('%d/%m/%Y %H:%M:%S'))
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

