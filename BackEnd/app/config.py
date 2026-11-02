"""
Configurações da aplicação.

Os valores sensíveis (como a SECRET_KEY) ficam no arquivo .env,
que não vai para o GitHub. Aqui só lemos esses valores.
"""
import os
import secrets
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

# Pasta BackEnd/ (um nível acima desta pasta app/)
PASTA_BACKEND = Path(__file__).resolve().parent.parent
# Pasta FrontEnd/ (ao lado de BackEnd/)
PASTA_FRONTEND = PASTA_BACKEND.parent / "FrontEnd"

# Lê o arquivo BackEnd/.env, se existir
load_dotenv(PASTA_BACKEND / ".env")

SECRET_KEY = os.getenv("SECRET_KEY") or ""
if not SECRET_KEY:
    # Sem chave definida: gera uma aleatória só para esta execução.
    # Funciona, mas todo login é perdido quando o servidor reinicia.
    SECRET_KEY = secrets.token_hex(32)
    print("[AVISO] SECRET_KEY não definida no .env. Usando uma chave temporária.")

DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{PASTA_BACKEND / 'recloset.db'}"

TOKEN_EXPIRA_MINUTOS = int(os.getenv("TOKEN_EXPIRA_MINUTOS", "120"))

# Por quantos minutos o link de "Esqueci minha senha" vale
TOKEN_SENHA_EXPIRA_MINUTOS = int(os.getenv("TOKEN_SENHA_EXPIRA_MINUTOS", "30"))

# Endereço do site, usado para montar o link de redefinição de senha
URL_SITE = (os.getenv("URL_SITE") or "http://localhost:8000").rstrip("/")

# Decimal evita erros de arredondamento com dinheiro (0.1 + 0.2 != 0.3 em float)
VALOR_ENTREGA = Decimal(os.getenv("VALOR_ENTREGA", "15.00"))

# Onde ficam as fotos enviadas (perfil e anúncios). Pode ser trocada pelo .env
PASTA_UPLOADS = Path(os.getenv("PASTA_UPLOADS") or PASTA_BACKEND / "uploads")

# Tamanho máximo de cada imagem enviada, em megabytes
TAMANHO_MAX_IMAGEM_MB = int(os.getenv("TAMANHO_MAX_IMAGEM_MB", "5"))

CORS_ORIGENS = [
    origem.strip()
    for origem in os.getenv("CORS_ORIGENS", "").split(",")
    if origem.strip()
]
