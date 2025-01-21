from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///taxistas.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class Taxista(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(11), nullable=False, unique=True)
    telefone = db.Column(db.String(20), nullable=False)
    placa_veiculo = db.Column(db.String(10), nullable=False)
    modelo_veiculo = db.Column(db.String(50), nullable=True)
    condutax = db.Column(db.String(20), nullable=False)
    vencimento_condutax = db.Column(db.DateTime, nullable=False)
    licenciamento = db.Column(db.String(20), nullable=True)
    vencimento_licenciamento = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"Taxista({self.nome}, {self.cpf})"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        taxista = Taxista(
            nome=request.form["nome"],
            cpf=request.form["cpf"],
            telefone=request.form["telefone"],
            placa_veiculo=request.form["placa_veiculo"],
            modelo_veiculo=request.form["modelo_veiculo"],
            condutax=request.form["condutax"],
            vencimento_condutax=datetime.strptime(request.form["vencimento_condutax"], "%Y-%m-%d"),
            licenciamento=request.form["licenciamento"],
            vencimento_licenciamento=datetime.strptime(request.form["vencimento_licenciamento"], "%Y-%m-%d"),
        )
        db.session.add(taxista)
        db.session.commit()
        return redirect(url_for("lista_taxistas"))
    return render_template("cadastro.html")

@app.route("/lista_taxistas")
def lista_taxistas():
    taxistas = Taxista.query.all()
    return render_template("lista_taxistas.html", taxistas=taxistas)

@app.route("/deletar_taxista/<int:id>")
def deletar_taxista(id):
    taxista = Taxista.query.get(id)
    if taxista:
        db.session.delete(taxista)
        db.session.commit()
    return redirect(url_for("lista_taxistas"))

if __name__ == "__main__":
    db.create_all()
    app.run(debug=True)

