"""
Rotas do usuário logado ("me" = eu).

Não existe rota do tipo /usuarios/{id} para editar: cada pessoa só
consegue ver e alterar os PRÓPRIOS dados, identificada pelo token.
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Favorito, Produto, Usuario
from app.schemas import ResumoPerfil, UsuarioAtualizacao, UsuarioPublico
from app.security import get_usuario_atual
from app.services.uploads import apagar_imagem, salvar_imagem

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


@router.get("/me", response_model=UsuarioPublico, summary="Ver meus dados")
def ver_meus_dados(usuario: Usuario = Depends(get_usuario_atual)):
    return usuario


@router.patch("/me", response_model=UsuarioPublico, summary="Editar meus dados")
def editar_meus_dados(
    dados: UsuarioAtualizacao,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    # exclude_unset: pega só os campos que o navegador realmente enviou
    alteracoes = dados.model_dump(exclude_unset=True)

    # nome, email e sexo são obrigatórios na conta: não aceitamos apagá-los
    for campo in ("nome", "email", "sexo"):
        if campo in alteracoes and alteracoes[campo] is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"O campo {campo} não pode ficar vazio.")

    novo_email = alteracoes.get("email")
    if novo_email and novo_email != usuario.email:
        outro = db.scalar(select(Usuario).where(Usuario.email == novo_email))
        if outro:
            raise HTTPException(status.HTTP_409_CONFLICT, "Este e-mail já está em uso.")

    for campo, valor in alteracoes.items():
        setattr(usuario, campo, valor)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Este e-mail já está em uso.")
    db.refresh(usuario)
    return usuario


@router.get("/me/resumo", response_model=ResumoPerfil, summary="Números do meu perfil")
def resumo_do_perfil(usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    # func.count() vira SELECT COUNT(*) no banco: não precisamos carregar os registros
    produtos = db.scalar(
        select(func.count()).select_from(Produto).where(Produto.vendedor_id == usuario.id)
    )
    vendas = db.scalar(
        select(func.count()).select_from(Produto)
        .where(Produto.vendedor_id == usuario.id, Produto.status == "vendido")
    )
    favoritos = db.scalar(
        select(func.count()).select_from(Favorito).where(Favorito.usuario_id == usuario.id)
    )
    return ResumoPerfil(produtos=produtos, vendas=vendas, favoritos=favoritos)


@router.post("/me/foto", response_model=UsuarioPublico, summary="Trocar minha foto de perfil")
async def trocar_foto(
    foto: UploadFile = File(description="Imagem JPG, PNG ou WEBP"),
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    foto_antiga = usuario.foto
    usuario.foto = await salvar_imagem(foto, "perfis")  # valida tipo e tamanho
    db.commit()
    apagar_imagem(foto_antiga)  # só apaga a antiga depois que a nova foi salva
    db.refresh(usuario)
    return usuario
