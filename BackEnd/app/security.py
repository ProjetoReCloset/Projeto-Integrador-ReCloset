"""
Segurança: hash de senha (bcrypt) e login por token (JWT).

Como funciona o login:
1. O usuário envia e-mail e senha para /api/auth/login.
2. Conferimos a senha com o hash guardado no banco.
3. Se estiver certa, devolvemos um TOKEN assinado com a SECRET_KEY.
4. Nas próximas requisições, o navegador envia o token no cabeçalho
   "Authorization: Bearer <token>". Como só o servidor conhece a
   SECRET_KEY, ninguém consegue falsificar um token.
"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import SECRET_KEY, TOKEN_EXPIRA_MINUTOS
from app.database import get_db
from app.models import Usuario

ALGORITMO = "HS256"

# Diz ao FastAPI (e ao Swagger) onde fica a rota de login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ---------- Senhas ----------

def gerar_hash_senha(senha: str) -> str:
    # gensalt() cria um "sal" aleatório: duas pessoas com a mesma senha
    # terão hashes diferentes no banco.
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))


# Hash "falso" usado quando o e-mail não existe (explicação em routers/auth.py)
HASH_FICTICIO = gerar_hash_senha("senha-ficticia-para-comparacao")


# ---------- Tokens ----------

def criar_token(usuario_id: int) -> str:
    expira = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRA_MINUTOS)
    dados = {"sub": str(usuario_id), "exp": expira}
    return jwt.encode(dados, SECRET_KEY, algorithm=ALGORITMO)


def get_usuario_atual(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """
    Dependência usada nas rotas privadas. Exemplo:

        @router.get("/me")
        def ver_perfil(usuario: Usuario = Depends(get_usuario_atual)):

    Se o token estiver ausente, vencido ou adulterado, responde 401.
    """
    erro_401 = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sessão inválida ou expirada. Faça login novamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        dados = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITMO])
        usuario_id = int(dados["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise erro_401

    usuario = db.get(Usuario, usuario_id)
    if usuario is None:  # ex.: conta excluída depois do login
        raise erro_401
    return usuario
