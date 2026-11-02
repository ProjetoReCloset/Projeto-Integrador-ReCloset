"""
Salvar imagens enviadas pelos usuários (foto de perfil e fotos dos anúncios).

Regras de segurança:
1. Não confiamos no nome do arquivo nem no "tipo" informado pelo navegador:
   qualquer um pode renomear "virus.exe" para "foto.jpg".
   Por isso lemos os primeiros bytes do arquivo (a "assinatura") para
   descobrir se é mesmo JPEG, PNG ou WEBP.
2. Limitamos o tamanho do arquivo.
3. O arquivo é salvo com um nome aleatório gerado por nós. Assim ninguém
   consegue sobrescrever arquivos ou usar nomes como "../../main.py".
"""
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.config import PASTA_UPLOADS, TAMANHO_MAX_IMAGEM_MB

TAMANHO_MAXIMO = TAMANHO_MAX_IMAGEM_MB * 1024 * 1024  # em bytes


def descobrir_extensao(inicio: bytes) -> str | None:
    """Identifica o formato pelos primeiros bytes. Devolve None se não for imagem aceita."""
    if inicio.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if inicio.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if inicio[:4] == b"RIFF" and inicio[8:12] == b"WEBP":
        return ".webp"
    return None


async def salvar_imagem(arquivo: UploadFile, subpasta: str) -> str:
    """
    Valida e salva a imagem em uploads/<subpasta>/.
    Devolve o caminho relativo (ex.: "perfis/3f2a....jpg"), que é o que vai para o banco.
    """
    # Lê no máximo 1 byte além do limite: se passar, sabemos que é grande demais
    conteudo = await arquivo.read(TAMANHO_MAXIMO + 1)

    if len(conteudo) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "O arquivo enviado está vazio.")
    if len(conteudo) > TAMANHO_MAXIMO:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"A imagem deve ter no máximo {TAMANHO_MAX_IMAGEM_MB} MB.",
        )

    extensao = descobrir_extensao(conteudo[:12])
    if extensao is None:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "Formato não aceito. Envie uma imagem JPG, PNG ou WEBP.",
        )

    pasta = PASTA_UPLOADS / subpasta
    pasta.mkdir(parents=True, exist_ok=True)

    nome = uuid.uuid4().hex + extensao  # nome aleatório, impossível de adivinhar
    (pasta / nome).write_bytes(conteudo)

    return f"{subpasta}/{nome}"


def apagar_imagem(caminho: str | None) -> None:
    """Remove um arquivo salvo anteriormente (ex.: foto de perfil antiga)."""
    if not caminho:
        return
    arquivo = (PASTA_UPLOADS / caminho).resolve()
    # Garante que o arquivo está mesmo dentro da pasta de uploads
    if arquivo.is_relative_to(PASTA_UPLOADS.resolve()) and arquivo.is_file():
        arquivo.unlink()
