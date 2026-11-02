"""
Rotas de autenticação: cadastro e login.

O logout não precisa de rota: o token é guardado no navegador e
"sair" significa apagá-lo de lá (ver FrontEnd/js/api.js).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Usuario
from app.schemas import (
    EsqueciSenhaEntrada,
    Mensagem,
    RedefinirSenhaEntrada,
    Token,
    UsuarioCadastro,
    UsuarioPublico,
)
from app.security import HASH_FICTICIO, criar_token, gerar_hash_senha, verificar_senha
from app.services.senha import redefinir_senha, solicitar_redefinicao

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post(
    "/cadastro",
    response_model=UsuarioPublico,
    status_code=status.HTTP_201_CREATED,
    summary="Criar uma nova conta",
)
def cadastrar(dados: UsuarioCadastro, db: Session = Depends(get_db)):
    ja_existe = db.scalar(select(Usuario).where(Usuario.email == dados.email))
    if ja_existe:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este e-mail já está cadastrado.")

    usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=gerar_hash_senha(dados.senha),
        sexo=dados.sexo,
    )
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError:
        # Duas pessoas cadastrando o mesmo e-mail ao mesmo tempo:
        # a verificação acima passou para as duas, mas o UNIQUE do banco barra a segunda.
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Este e-mail já está cadastrado.")
    db.refresh(usuario)
    return usuario


@router.post("/login", response_model=Token, summary="Entrar (devolve o token)")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Recebe os dados como formulário (padrão OAuth2), o que permite usar
    o botão **Authorize** do Swagger. O campo `username` é o **e-mail**.
    """
    email = form.username.strip().lower()
    usuario = db.scalar(select(Usuario).where(Usuario.email == email))

    # Mesmo se o e-mail não existir, comparamos com um hash fictício.
    # Assim a resposta demora o mesmo tempo nos dois casos e ninguém
    # descobre quais e-mails estão cadastrados medindo o tempo.
    hash_para_comparar = usuario.senha_hash if usuario else HASH_FICTICIO
    senha_ok = verificar_senha(form.password, hash_para_comparar)

    if not usuario or not senha_ok:
        # Mensagem genérica de propósito: não dizemos qual dos dois está errado
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "E-mail ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return Token(access_token=criar_token(usuario.id))


@router.post("/esqueci-senha", response_model=Mensagem, summary="Pedir link para redefinir a senha")
def esqueci_senha(dados: EsqueciSenhaEntrada, db: Session = Depends(get_db)):
    """
    A resposta é SEMPRE a mesma, exista ou não o e-mail. Assim ninguém
    usa esta tela para descobrir quem tem conta no ReCloset.

    Como não há servidor de e-mail, o link aparece no terminal do servidor.
    """
    solicitar_redefinicao(db, dados.email)
    return Mensagem(mensagem="Se este e-mail estiver cadastrado, enviaremos um link para redefinir a senha.")


@router.post("/redefinir-senha", response_model=Mensagem, summary="Definir nova senha usando o link")
def redefinir(dados: RedefinirSenhaEntrada, db: Session = Depends(get_db)):
    redefinir_senha(db, dados.token, dados.nova_senha)
    return Mensagem(mensagem="Senha alterada com sucesso. Faça login com a nova senha.")
