"""
Recuperação de senha ("Esqueci minha senha").

Como funciona:
1. A pessoa informa o e-mail.
2. Geramos um TOKEN aleatório (impossível de adivinhar) e guardamos no
   banco apenas o HASH dele (como fazemos com a senha). Assim, mesmo
   quem tivesse acesso ao banco não conseguiria usar os tokens.
3. O link com o token é "enviado por e-mail". Como o projeto não tem um
   servidor de e-mail, o link aparece no TERMINAL onde o servidor está
   rodando. Para um sistema real, bastaria trocar a função
   enviar_link_por_email() por um envio de verdade (SMTP).
4. O token vale por pouco tempo e só pode ser usado UMA vez.
"""
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import TOKEN_SENHA_EXPIRA_MINUTOS, URL_SITE
from app.models import TokenRedefinicaoSenha, Usuario
from app.security import gerar_hash_senha

log = logging.getLogger("uvicorn.error")  # aparece no mesmo terminal do servidor


def _hash_token(token: str) -> str:
    # SHA-256 é suficiente aqui porque o token já é longo e aleatório
    # (para SENHAS usamos bcrypt, que é lento de propósito).
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def enviar_link_por_email(email: str, link: str) -> None:
    """Simulação do envio do e-mail: mostra o link no terminal."""
    log.warning("[E-MAIL SIMULADO] Para: %s | Link para redefinir a senha: %s", email, link)


def solicitar_redefinicao(db: Session, email: str) -> None:
    usuario = db.scalar(select(Usuario).where(Usuario.email == email))
    if usuario is None:
        # Não avisamos que o e-mail não existe (a rota responde igual nos dois casos)
        return

    # Um pedido novo cancela os links antigos que ainda não foram usados
    db.execute(
        update(TokenRedefinicaoSenha)
        .where(TokenRedefinicaoSenha.usuario_id == usuario.id, TokenRedefinicaoSenha.usado.is_(False))
        .values(usado=True)
    )

    token = secrets.token_urlsafe(32)  # 43 caracteres aleatórios
    db.add(TokenRedefinicaoSenha(
        usuario_id=usuario.id,
        token_hash=_hash_token(token),
        expira_em=datetime.now(timezone.utc) + timedelta(minutes=TOKEN_SENHA_EXPIRA_MINUTOS),
    ))
    db.commit()

    enviar_link_por_email(usuario.email, f"{URL_SITE}/redefinir_senha.html?token={token}")


def redefinir_senha(db: Session, token: str, nova_senha: str) -> None:
    erro = HTTPException(
        status.HTTP_400_BAD_REQUEST,
        "Este link é inválido ou expirou. Peça um novo em \"Esqueci minha senha\".",
    )

    registro = db.scalar(select(TokenRedefinicaoSenha).where(
        TokenRedefinicaoSenha.token_hash == _hash_token(token)))
    if registro is None or registro.usado:
        raise erro

    expira_em = registro.expira_em
    if expira_em.tzinfo is None:  # o SQLite devolve a data sem fuso (está em UTC)
        expira_em = expira_em.replace(tzinfo=timezone.utc)
    if expira_em < datetime.now(timezone.utc):
        raise erro

    # Marca como usado de forma condicional, para o mesmo link não ser
    # aproveitado duas vezes ao mesmo tempo (mesma ideia da compra)
    resultado = db.execute(
        update(TokenRedefinicaoSenha)
        .where(TokenRedefinicaoSenha.id == registro.id, TokenRedefinicaoSenha.usado.is_(False))
        .values(usado=True)
    )
    if resultado.rowcount != 1:
        db.rollback()
        raise erro

    usuario = db.get(Usuario, registro.usuario_id)
    usuario.senha_hash = gerar_hash_senha(nova_senha)
    db.commit()
