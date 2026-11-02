"""
Ponto de entrada da aplicação ReCloset.

Para rodar (dentro da pasta BackEnd/):
    uvicorn app.main:app --reload

Depois abra:
    http://localhost:8000          -> o site (pasta FrontEnd/)
    http://localhost:8000/docs     -> Swagger, para testar a API
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.config import CORS_ORIGENS, PASTA_FRONTEND, PASTA_UPLOADS
from app.database import Base, SessionLocal, engine
from app.models import Categoria
from app.routers import auth, carrinho, categorias, endereco, favoritos, pedidos, produtos, usuarios

CATEGORIAS_FIXAS = [
    ("Feminino", "feminino"),
    ("Masculino", "masculino"),
    ("Acessórios", "acessorios"),
    ("Calçados", "calcados"),
]


def preparar_banco():
    """Cria as tabelas que ainda não existem e cadastra as categorias fixas."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        for nome, slug in CATEGORIAS_FIXAS:
            if not db.scalar(select(Categoria).where(Categoria.slug == slug)):
                db.add(Categoria(nome=nome, slug=slug))
        db.commit()


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    preparar_banco()  # roda uma vez, quando o servidor liga
    yield


app = FastAPI(
    title="ReCloset API",
    description="API do brechó online ReCloset. Use o botão **Authorize** para fazer login.",
    version="1.0.0",
    lifespan=ciclo_de_vida,
)

# CORS: só é necessário se o frontend for aberto por outro endereço
# (ex.: Live Server na porta 5500). Abrindo por localhost:8000 não precisa.
if CORS_ORIGENS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGENS,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# ---------- Mensagens de validação em português ----------

TRADUCOES = {
    "missing": "é obrigatório",
    "string_too_short": "está curto demais (mínimo {min_length} caracteres)",
    "string_too_long": "está longo demais (máximo {max_length} caracteres)",
    "literal_error": "tem um valor inválido",
    "greater_than": "deve ser maior que {gt}",
    "less_than_equal": "deve ser no máximo {le}",
    "decimal_max_places": "pode ter no máximo 2 casas decimais",
    "decimal_parsing": "deve ser um número",
    "int_parsing": "deve ser um número inteiro",
}

NOMES_CAMPOS = {"nome": "Nome", "email": "E-mail", "senha": "Senha", "sexo": "Sexo",
                "telefone": "Telefone", "descricao": "Descrição", "cep": "CEP",
                "rua": "Rua", "numero": "Número", "complemento": "Complemento",
                "bairro": "Bairro", "cidade": "Cidade", "estado": "Estado", "foto": "Foto",
                "preco": "Preço", "tamanho": "Tamanho", "categoria": "Categoria",
                "imagens": "Fotos", "nova_senha": "Nova senha", "token": "Link"}


@app.exception_handler(RequestValidationError)
async def erro_de_validacao(_request: Request, exc: RequestValidationError):
    """
    Quando os dados enviados não passam nos schemas, o FastAPI responde 422
    com mensagens em inglês. Aqui transformamos em uma frase em português
    que o frontend pode mostrar direto para o usuário.
    """
    mensagens = []
    for erro in exc.errors():
        campo = str(erro["loc"][-1])
        nome_campo = NOMES_CAMPOS.get(campo, campo)
        modelo = TRADUCOES.get(erro["type"])
        if modelo:
            texto = modelo.format(**erro.get("ctx", {}))
        elif campo == "email":
            texto = "não é um e-mail válido"
        else:
            # value_error vindo dos nossos validadores já está em português
            texto = str(erro.get("msg", "é inválido")).removeprefix("Value error, ")
        mensagens.append(f"{nome_campo}: {texto}")
    return JSONResponse(status_code=422, content={"detail": "; ".join(mensagens)})


# ---------- Rotas da API (todas começam com /api) ----------

app.include_router(auth.router, prefix="/api")
app.include_router(usuarios.router, prefix="/api")
app.include_router(categorias.router, prefix="/api")
app.include_router(endereco.router, prefix="/api")
app.include_router(produtos.router, prefix="/api")
app.include_router(favoritos.router, prefix="/api")
app.include_router(carrinho.router, prefix="/api")
app.include_router(pedidos.router, prefix="/api")


# ---------- Fotos enviadas pelos usuários ----------
# Ex.: o caminho "perfis/abc.jpg" fica acessível em /uploads/perfis/abc.jpg
PASTA_UPLOADS.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=PASTA_UPLOADS), name="uploads")


# ---------- Site (arquivos da pasta FrontEnd/) ----------
# Fica por último: qualquer endereço que não seja /api/... ou /docs
# é procurado como arquivo dentro de FrontEnd/.
app.mount("/", StaticFiles(directory=PASTA_FRONTEND, html=True), name="frontend")
