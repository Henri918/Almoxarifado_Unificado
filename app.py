from flask import Flask, request, jsonify, render_template, redirect, session, url_for
from flask_cors import CORS
import mysql.connector, bcrypt, os, secrets
from functools import wraps
from contextlib import contextmanager

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "troque-esta-chave-em-producao")
CORS(app)

DB = {
    "host": os.getenv("DB_HOST", "mysql"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "root"),
    "database": os.getenv("DB_NAME", "login")
}


tokens = {}

@contextmanager
def db():
    con = mysql.connector.connect(**DB)
    cur = con.cursor(dictionary=True)
    try:
        yield con, cur
    except:
        con.rollback()
        raise
    finally:
        cur.close()
        con.close()


def resp(msg="", ok=False, code=200, **data):
    return jsonify({"success": ok, "message": msg, **data}), code


def usuario_token():
    auth = request.headers.get("Authorization", "")
    return tokens.get(auth[7:].strip()) if auth.startswith("Bearer ") else None


def auth(admin=False):
    def deco(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = usuario_token()

            if not user:
                return resp("Não autenticado", code=401)

            if admin and user["tipo"] != "admin":
                return resp(
                    "Acesso permitido somente para administradores",
                    code=403
                )

            request.usuario = user
            return f(*args, **kwargs)

        return wrapper
    return deco


login_required = auth()
admin_required = auth(True)


def produto_dados():
    d = request.get_json(silent=True) or {}

    nome = str(d.get("nome", "")).strip()
    categoria = str(d.get("categoria", "")).strip()

    try:
        quantidade = int(d.get("quantidade", 0))
        estoque_minimo = int(d.get("estoque_minimo", 0))
        preco = float(d.get("preco", 0))
    except (ValueError, TypeError):
        return None, resp("Valores inválidos", code=400)

    if not nome or not categoria:
        return None, resp(
            "Nome e categoria são obrigatórios",
            code=400
        )

    return {
        "nome": nome,
        "categoria": categoria,
        "quantidade": quantidade,
        "estoque_minimo": estoque_minimo,
        "preco": preco,
        "foto": d.get("foto")
    }, None

@app.get("/api")
def inicio():
    return resp(
        "API do Almoxarifado funcionando",
        True
    )


@app.get("/api/health")
def health():
    try:
        with db():
            return resp(
                "Flask e MySQL funcionando",
                True
            )
    except Exception as e:
        print("ERRO HEALTH:", e)
        return resp("MySQL indisponível", code=500)

@app.post("/api/login")
@app.post("/api/auth/login")
def login():
    d = request.get_json(silent=True) or {}

    email = str(d.get("email", "")).strip().lower()
    senha = str(d.get("senha", ""))

    if not email or not senha:
        return resp("Preencha e-mail e senha", code=400)

    try:
        with db() as (_, cur):
            cur.execute(
                "SELECT id,email,senha,tipo FROM usuario WHERE email=%s",
                (email,)
            )

            user = cur.fetchone()

            if not user:
                return resp(
                    "E-mail ou senha incorretos",
                    code=401
                )

            try:
                valido = bcrypt.checkpw(
                    senha.encode(),
                    user["senha"].encode()
                )
            except:
                valido = False

            if not valido:
                return resp(
                    "E-mail ou senha incorretos",
                    code=401
                )

            publico = {
                "id": user["id"],
                "email": user["email"],
                "tipo": user["tipo"]
            }

            token = secrets.token_urlsafe(32)
            tokens[token] = publico

            return resp(
                "Login realizado com sucesso",
                True,
                data={
                    "token": token,
                    "user": publico
                }
            )

    except Exception as e:
        print("ERRO LOGIN:", e)
        return resp("Erro ao realizar login", code=500)


@app.post("/api/auth/logout")
@login_required
def logout():
    token = request.headers.get("Authorization", "")[7:].strip()
    tokens.pop(token, None)

    return resp("Logout realizado", True)


@app.get("/api/auth/me")
@login_required
def me():
    return jsonify({
        "success": True,
        "user": request.usuario
    })

@app.post("/api/register")
@app.post("/api/auth/register")
def register():
    d = request.get_json(silent=True) or {}

    email = str(d.get("email", "")).strip().lower()
    senha = str(d.get("senha", ""))

    if not email or not senha:
        return resp("Preencha e-mail e senha", code=400)

    if len(senha) < 6:
        return resp(
            "A senha deve ter pelo menos 6 caracteres",
            code=400
        )

    try:
        with db() as (con, cur):
            cur.execute(
                "SELECT id FROM usuario WHERE email=%s",
                (email,)
            )

            if cur.fetchone():
                return resp(
                    "Este e-mail já está cadastrado",
                    code=409
                )

            senha = bcrypt.hashpw(
                senha.encode(),
                bcrypt.gensalt()
            ).decode()

            cur.execute(
                """
                INSERT INTO usuario(email,senha,tipo)
                VALUES(%s,%s,%s)
                """,
                (email, senha, "usuario")
            )

            con.commit()

            return resp(
                "Conta criada com sucesso",
                True,
                201,
                user={
                    "id": cur.lastrowid,
                    "email": email,
                    "tipo": "usuario"
                }
            )

    except Exception as e:
        print("ERRO REGISTER:", e)
        return resp("Erro ao criar conta", code=500)

CAMPOS = """
id,nome,categoria,quantidade,estoque_minimo,preco,foto
"""


@app.get("/api/produtos")
@login_required
def listar_produtos():
    try:
        with db() as (_, cur):
            cur.execute(
                f"""
                SELECT {CAMPOS}
                FROM produtos
                ORDER BY id DESC
                """
            )

            return jsonify({
                "success": True,
                "data": cur.fetchall()
            })

    except Exception as e:
        print("ERRO PRODUTOS:", e)
        return resp(
            "Erro ao buscar produtos",
            code=500
        )


@app.get("/api/produtos/<int:id>")
@login_required
def buscar_produto(id):
    try:
        with db() as (_, cur):
            cur.execute(
                f"""
                SELECT {CAMPOS}
                FROM produtos
                WHERE id=%s
                """,
                (id,)
            )

            produto = cur.fetchone()

            if not produto:
                return resp(
                    "Produto não encontrado",
                    code=404
                )

            return jsonify({
                "success": True,
                "data": produto
            })

    except Exception as e:
        print("ERRO BUSCAR PRODUTO:", e)
        return resp(
            "Erro ao buscar produto",
            code=500
        )


@app.post("/api/produtos")
@admin_required
def criar_produto():
    p, erro = produto_dados()

    if erro:
        return erro

    if p["quantidade"] < 0 or p["estoque_minimo"] < 0 or p["preco"] < 0:
        return resp(
            "Os valores não podem ser negativos",
            code=400
        )

    try:
        with db() as (con, cur):
            cur.execute(
                """
                INSERT INTO produtos
                (nome,categoria,quantidade,estoque_minimo,preco,foto)
                VALUES(%s,%s,%s,%s,%s,%s)
                """,
                tuple(p.values())
            )

            con.commit()

            return resp(
                "Produto criado com sucesso",
                True,
                201,
                data={"id": cur.lastrowid}
            )

    except Exception as e:
        print("ERRO CRIAR:", e)
        return resp(
            "Erro ao criar produto",
            code=500
        )


@app.put("/api/produtos/<int:id>")
@admin_required
def editar_produto(id):
    p, erro = produto_dados()

    if erro:
        return erro

    try:
        with db() as (con, cur):
            cur.execute(
                "SELECT id FROM produtos WHERE id=%s",
                (id,)
            )

            if not cur.fetchone():
                return resp(
                    "Produto não encontrado",
                    code=404
                )

            cur.execute(
                """
                UPDATE produtos
                SET nome=%s,
                    categoria=%s,
                    quantidade=%s,
                    estoque_minimo=%s,
                    preco=%s,
                    foto=%s
                WHERE id=%s
                """,
                (*p.values(), id)
            )

            con.commit()

            return resp(
                "Produto atualizado com sucesso",
                True
            )

    except Exception as e:
        print("ERRO EDITAR:", e)
        return resp(
            "Erro ao editar produto",
            code=500
        )

def alterar_estoque(id, quantidade, entrada):
    d = request.get_json(silent=True) or {}

    try:
        quantidade = int(d.get("quantidade"))
    except (ValueError, TypeError):
        return resp("Quantidade inválida", code=400)

    if quantidade <= 0:
        return resp(
            "A quantidade deve ser maior que zero",
            code=400
        )

    tipo = "Entrada" if entrada else "Retirada"

    try:
        with db() as (con, cur):
            cur.execute(
                """
                SELECT id,quantidade
                FROM produtos
                WHERE id=%s
                FOR UPDATE
                """,
                (id,)
            )

            produto = cur.fetchone()

            if not produto:
                return resp(
                    "Produto não encontrado",
                    code=404
                )

            if not entrada and produto["quantidade"] < quantidade:
                return resp(
                    "Estoque insuficiente",
                    code=400
                )

            operador = "+" if entrada else "-"

            cur.execute(
                f"""
                UPDATE produtos
                SET quantidade=quantidade{operador}%s
                WHERE id=%s
                """,
                (quantidade, id)
            )

            cur.execute(
                """
                INSERT INTO movimentacoes
                (produto_id,usuario_id,quantidade,tipo)
                VALUES(%s,%s,%s,%s)
                """,
                (
                    id,
                    request.usuario["id"],
                    quantidade,
                    tipo
                )
            )

            con.commit()

            return resp(
                "Estoque adicionado com sucesso"
                if entrada else
                "Produto retirado com sucesso",
                True
            )

    except Exception as e:
        print("ERRO ESTOQUE:", e)
        return resp(
            "Erro ao alterar estoque",
            code=500
        )


@app.post("/api/produtos/<int:id>/adicionar")
@login_required
def adicionar_produto(id):
    return alterar_estoque(id, None, True)


@app.post("/api/produtos/<int:id>/retirar")
@login_required
def retirar_produto(id):
    return alterar_estoque(id, None, False)

@app.delete("/api/produtos/<int:id>")
@admin_required
def excluir_produto(id):
    try:
        with db() as (con, cur):
            cur.execute(
                "SELECT id FROM produtos WHERE id=%s",
                (id,)
            )

            if not cur.fetchone():
                return resp(
                    "Produto não encontrado",
                    code=404
                )

            cur.execute(
                """
                SELECT COUNT(*) AS total
                FROM movimentacoes
                WHERE produto_id=%s
                """,
                (id,)
            )

            if cur.fetchone()["total"]:
                return resp(
                    "Este produto possui movimentações e não pode ser excluído",
                    code=400
                )

            cur.execute(
                "DELETE FROM produtos WHERE id=%s",
                (id,)
            )

            con.commit()

            return resp(
                "Produto excluído com sucesso",
                True
            )

    except Exception as e:
        print("ERRO EXCLUIR:", e)
        return resp(
            "Erro ao excluir produto",
            code=500
        )

@app.get("/api/movimentacoes")
@login_required
def listar_movimentacoes():
    try:
        with db() as (_, cur):
            cur.execute(
                """
                SELECT
                    m.id,
                    m.produto_id,
                    p.nome AS produto,
                    m.usuario_id,
                    u.email AS usuario,
                    m.quantidade,
                    m.tipo,
                    m.data_hora
                FROM movimentacoes m
                JOIN produtos p ON p.id=m.produto_id
                JOIN usuario u ON u.id=m.usuario_id
                ORDER BY m.data_hora DESC
                """
            )

            return jsonify({
                "success": True,
                "data": cur.fetchall()
            })

    except Exception as e:
        print("ERRO MOVIMENTACOES:", e)
        return resp(
            "Erro ao buscar movimentações",
            code=500
        )

@app.get("/api/usuarios")
@admin_required
def listar_usuarios():
    try:
        with db() as (_, cur):
            cur.execute(
                """
                SELECT id,email,tipo
                FROM usuario
                ORDER BY id DESC
                """
            )

            return jsonify({
                "success": True,
                "data": cur.fetchall()
            })

    except Exception as e:
        print("ERRO USUARIOS:", e)
        return resp(
            "Erro ao buscar usuários",
            code=500
        )

@app.post("/api/usuarios")
@admin_required
def cadastrar_usuario_admin():
    d = request.get_json(silent=True) or {}

    email = str(d.get("email", "")).strip().lower()
    senha = str(d.get("senha", ""))
    tipo = str(d.get("tipo", "usuario")).strip().lower()

    if not email or not senha:
        return resp("Preencha email e senha", code=400)

    if len(senha) < 6:
        return resp(
            "A senha deve ter pelo menos 6 caracteres",
            code=400
        )

    if tipo not in ["admin", "usuario"]:
        return resp("Tipo de usuário inválido", code=400)

    try:
        with db() as (con, cur):
            cur.execute(
                "SELECT id FROM usuario WHERE email=%s",
                (email,)
            )

            if cur.fetchone():
                return resp(
                    "Este email já está cadastrado",
                    code=409
                )

            senha_hash = bcrypt.hashpw(
                senha.encode(),
                bcrypt.gensalt()
            ).decode()

            cur.execute(
                """
                INSERT INTO usuario (email, senha, tipo)
                VALUES (%s, %s, %s)
                """,
                (email, senha_hash, tipo)
            )

            novo_id = cur.lastrowid
            con.commit()

            return resp(
                "Usuário cadastrado com sucesso",
                True,
                201,
                data={
                    "id": novo_id,
                    "email": email,
                    "tipo": tipo
                }
            )

    except mysql.connector.IntegrityError:
        return resp(
            "Este email já está cadastrado",
            code=409
        )

    except Exception as e:
        print("ERRO CADASTRO ADMIN:", e)
        return resp("Erro ao cadastrar usuário", code=500)
    

# ============================================================
# INTERFACE WEB (integrada ao mesmo banco usado pelo aplicativo)
# ============================================================

@app.get("/web")
@app.get("/")
def web_inicio():
    if session.get("tipo") == "admin":
        return redirect("/adm")
    if session.get("tipo") == "usuario":
        return redirect("/dps")
    return render_template("index.html")


@app.post("/login")
def web_login():
    email = str(request.form.get("email", "")).strip().lower()
    senha = str(request.form.get("senha", ""))
    if not email or not senha:
        return "Preencha e-mail e senha", 400
    try:
        with db() as (_, cur):
            cur.execute("SELECT id,email,senha,tipo FROM usuario WHERE email=%s", (email,))
            user = cur.fetchone()
        if not user or not bcrypt.checkpw(senha.encode(), user["senha"].encode()):
            return "E-mail ou senha incorretos", 401
        session["user_id"] = user["id"]
        session["email"] = user["email"]
        session["tipo"] = user["tipo"]
        return redirect("/adm" if user["tipo"] == "admin" else "/dps")
    except Exception as e:
        print("ERRO WEB LOGIN:", e)
        return "Erro ao realizar login", 500


@app.post("/cadastrar")
def web_cadastrar():
    email = str(request.form.get("email", "")).strip().lower()
    senha = str(request.form.get("senha", ""))
    if not email or len(senha) < 6:
        return "Informe um e-mail e uma senha com pelo menos 6 caracteres", 400
    try:
        with db() as (con, cur):
            cur.execute("INSERT INTO usuario(email,senha,tipo) VALUES(%s,%s,'usuario')",
                        (email, bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()))
            con.commit()
        return redirect("/")
    except mysql.connector.IntegrityError:
        return "Este e-mail já está cadastrado", 409
    except Exception as e:
        print("ERRO WEB CADASTRO:", e)
        return "Erro ao cadastrar", 500


def web_exigir_login(admin=False):
    if not session.get("user_id"):
        return redirect("/")
    if admin and session.get("tipo") != "admin":
        return redirect("/dps")
    return None


@app.get("/adm")
def web_adm():
    bloqueio = web_exigir_login(admin=True)
    if bloqueio: return bloqueio
    with db() as (_, cur):
        cur.execute("SELECT id,nome,categoria,quantidade,estoque_minimo,preco,foto FROM produtos ORDER BY id DESC")
        produtos = [tuple(p.values()) for p in cur.fetchall()]
    return render_template("adm.html", produtos=produtos)


@app.get("/dps")
def web_dps():
    bloqueio = web_exigir_login()
    if bloqueio: return bloqueio
    with db() as (_, cur):
        cur.execute("SELECT id,nome,categoria,quantidade,estoque_minimo,preco,foto FROM produtos ORDER BY id DESC")
        produtos = [tuple(p.values()) for p in cur.fetchall()]
    return render_template("dps.html", produtos=produtos)


@app.post("/cadastrarproduto")
def web_cadastrar_produto():
    bloqueio = web_exigir_login(admin=True)
    if bloqueio: return bloqueio
    nome = request.form.get("nome", "").strip()
    categoria = request.form.get("categoria", "").strip()
    foto = request.form.get("foto2", "").strip() or None
    try:
        quantidade = int(request.form.get("quantidade", "0"))
        if not nome or not categoria or quantidade < 0: raise ValueError()
        with db() as (con, cur):
            cur.execute("""INSERT INTO produtos(nome,categoria,quantidade,estoque_minimo,preco,foto)
                           VALUES(%s,%s,%s,0,0,%s)""", (nome,categoria,quantidade,foto))
            pid = cur.lastrowid
            cur.execute("""INSERT INTO movimentacoes(produto_id,usuario_id,quantidade,tipo)
                           VALUES(%s,%s,%s,'Entrada')""", (pid,session["user_id"],quantidade))
            con.commit()
        return redirect("/adm")
    except (ValueError, TypeError):
        return "Dados do produto inválidos", 400


@app.get("/retirar/<int:id>/<int:qtd>")
def web_retirar(id, qtd):
    bloqueio = web_exigir_login()
    if bloqueio: return bloqueio
    if qtd <= 0: return "Quantidade inválida", 400
    try:
        with db() as (con, cur):
            cur.execute("SELECT quantidade FROM produtos WHERE id=%s FOR UPDATE", (id,))
            p = cur.fetchone()
            if not p: return "Produto não encontrado", 404
            if p["quantidade"] < qtd: return "Quantidade indisponível no estoque", 400
            cur.execute("UPDATE produtos SET quantidade=quantidade-%s WHERE id=%s", (qtd,id))
            cur.execute("""INSERT INTO movimentacoes(produto_id,usuario_id,quantidade,tipo)
                           VALUES(%s,%s,%s,'Retirada')""", (id,session["user_id"],qtd))
            con.commit()
        return redirect("/dps")
    except Exception as e:
        print("ERRO WEB RETIRADA:", e)
        return "Erro ao retirar produto", 500


@app.get("/adicionarquantidade/<int:id>/<int:quantidade>")
def web_adicionar_quantidade(id, quantidade):
    bloqueio = web_exigir_login(admin=True)
    if bloqueio: return bloqueio
    if quantidade <= 0: return "Quantidade inválida", 400
    try:
        with db() as (con, cur):
            cur.execute("SELECT id FROM produtos WHERE id=%s", (id,))
            if not cur.fetchone(): return "Produto não encontrado", 404
            cur.execute("UPDATE produtos SET quantidade=quantidade+%s WHERE id=%s", (quantidade,id))
            cur.execute("""INSERT INTO movimentacoes(produto_id,usuario_id,quantidade,tipo)
                           VALUES(%s,%s,%s,'Entrada')""", (id,session["user_id"],quantidade))
            con.commit()
        return redirect("/adm")
    except Exception as e:
        print("ERRO WEB ENTRADA:", e)
        return "Erro ao adicionar estoque", 500


@app.get("/editarquantidade/<int:id>/<int:qtd>")
def web_editar_quantidade(id, qtd):
    bloqueio = web_exigir_login(admin=True)
    if bloqueio: return bloqueio
    if qtd < 0: return "Quantidade inválida", 400
    try:
        with db() as (con, cur):
            cur.execute("SELECT quantidade FROM produtos WHERE id=%s", (id,))
            p = cur.fetchone()
            if not p: return "Produto não encontrado", 404
            diferenca = abs(qtd - p["quantidade"])
            cur.execute("UPDATE produtos SET quantidade=%s WHERE id=%s", (qtd,id))
            if diferenca:
                cur.execute("""INSERT INTO movimentacoes(produto_id,usuario_id,quantidade,tipo)
                               VALUES(%s,%s,%s,'Edição')""", (id,session["user_id"],diferenca))
            con.commit()
        return redirect("/adm")
    except Exception as e:
        print("ERRO WEB EDICAO:", e)
        return "Erro ao editar quantidade", 500


@app.get("/deletar/<int:id>")
def web_deletar(id):
    bloqueio = web_exigir_login(admin=True)
    if bloqueio: return bloqueio
    try:
        with db() as (con, cur):
            cur.execute("SELECT COUNT(*) AS total FROM movimentacoes WHERE produto_id=%s", (id,))
            if cur.fetchone()["total"]:
                return "Este produto possui movimentações e não pode ser excluído", 400
            cur.execute("DELETE FROM produtos WHERE id=%s", (id,))
            con.commit()
        return redirect("/adm")
    except Exception as e:
        print("ERRO WEB EXCLUSAO:", e)
        return "Erro ao excluir produto", 500


@app.get("/movimentacos")
@app.get("/movimentacoes-web")
def web_movimentacoes():
    bloqueio = web_exigir_login(admin=True)
    if bloqueio: return bloqueio
    with db() as (_, cur):
        cur.execute("""SELECT m.id,m.produto_id,p.nome,m.tipo,m.quantidade,u.email,m.data_hora
                       FROM movimentacoes m
                       JOIN produtos p ON p.id=m.produto_id
                       JOIN usuario u ON u.id=m.usuario_id
                       ORDER BY m.data_hora DESC""")
        movimentacoes = cur.fetchall()
    # Os templates antigos usam índices de tupla.
    linhas = [(m["id"],m["produto_id"],m["nome"],m["tipo"],m["quantidade"],m["email"],m["data_hora"]) for m in movimentacoes]
    return render_template("movimentacos.html", movimentacoes=linhas)


@app.get("/usuarios")
def web_usuarios():
    bloqueio = web_exigir_login(admin=True)
    if bloqueio: return bloqueio
    with db() as (_, cur):
        cur.execute("SELECT id,email,tipo FROM usuario ORDER BY id DESC")
        usuarios = cur.fetchall()
    return render_template("usuarios.html", usuarios=[(u["id"],u["email"],u["tipo"]) for u in usuarios])


@app.post("/cadastrarusuario")
def web_cadastrar_usuario():
    bloqueio = web_exigir_login(admin=True)
    if bloqueio: return bloqueio
    email = str(request.form.get("email", "")).strip().lower()
    senha = str(request.form.get("senha", ""))
    tipo = str(request.form.get("tipo", "usuario"))
    if not email or len(senha) < 6 or tipo not in ("admin","usuario"):
        return "Dados inválidos. A senha precisa ter pelo menos 6 caracteres.", 400
    try:
        with db() as (con, cur):
            cur.execute("INSERT INTO usuario(email,senha,tipo) VALUES(%s,%s,%s)",
                        (email,bcrypt.hashpw(senha.encode(),bcrypt.gensalt()).decode(),tipo))
            con.commit()
        return redirect("/usuarios")
    except mysql.connector.IntegrityError:
        return "Este e-mail já está cadastrado", 409


@app.get("/logout")
def web_logout():
    session.clear()
    return redirect("/")



if __name__ == "__main__":
    print("======================================")
    print(" ALMOXARIFADO - API FLASK")
    print("======================================")
    print(f"Banco: {DB['host']}:{DB['port']}/{DB['database']}")
    print("Servidor: http://0.0.0.0:5000")
    print("======================================")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
