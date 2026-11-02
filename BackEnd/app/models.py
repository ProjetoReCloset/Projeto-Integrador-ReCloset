"""
Modelos do banco de dados (cada classe = uma tabela).

Relacionamentos principais:
- Um Usuario cadastra vários Produtos (anúncios).
- Um Usuario tem vários Favoritos e vários itens no carrinho.
- Um Usuario tem no máximo UM Endereco.
- Um Pedido pertence a um Usuario e tem vários ItemPedido.
- Cada ItemPedido aponta para um Produto. Como cada peça é única,
  um Produto só pode aparecer em UM ItemPedido (regra garantida pelo banco).
"""
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def agora():
    """Data/hora atual em UTC (padrão para gravar no banco)."""
    return datetime.now(timezone.utc)


# Valores permitidos (usados também nos schemas e nas regras)
SEXOS = ("feminino", "masculino", "outros")
STATUS_PRODUTO = ("disponivel", "vendido")
STATUS_PEDIDO = ("confirmado", "enviado", "entregue")


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # Guardamos SOMENTE o hash da senha, nunca a senha em si.
    senha_hash: Mapped[str] = mapped_column(String(100))
    sexo: Mapped[str] = mapped_column(String(10))
    telefone: Mapped[str | None] = mapped_column(String(20))
    descricao: Mapped[str | None] = mapped_column(String(300))
    foto: Mapped[str | None] = mapped_column(String(255))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)

    produtos: Mapped[list["Produto"]] = relationship(back_populates="vendedor")
    endereco: Mapped["Endereco | None"] = relationship(
        back_populates="usuario", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(f"sexo IN {SEXOS}", name="ck_usuario_sexo"),
    )


class Categoria(Base):
    """Categorias fixas: Feminino, Masculino, Acessórios, Calçados."""
    __tablename__ = "categoria"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(50), unique=True)
    # "slug" é o nome sem acento, usado em links e filtros (ex.: ?categoria=calcados)
    slug: Mapped[str] = mapped_column(String(50), unique=True)


class Produto(Base):
    """Um anúncio = uma peça usada, única (não existe 'estoque')."""
    __tablename__ = "produto"

    id: Mapped[int] = mapped_column(primary_key=True)
    vendedor_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), index=True)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categoria.id"), index=True)
    nome: Mapped[str] = mapped_column(String(120))
    # Na descrição o vendedor também informa o estado de conservação da peça.
    descricao: Mapped[str] = mapped_column(Text)
    tamanho: Mapped[str | None] = mapped_column(String(30))
    # Numeric(10, 2): até 99.999.999,99 com 2 casas decimais exatas
    preco: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(15), default="disponivel", index=True)
    # Nome + descrição sem acentos e em minúsculas, usado só na busca.
    # Assim "trico", "TRICÔ" e "tricô" encontram a mesma peça.
    texto_busca: Mapped[str] = mapped_column(Text, default="")
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=agora, onupdate=agora
    )

    vendedor: Mapped[Usuario] = relationship(back_populates="produtos")
    categoria: Mapped[Categoria] = relationship()
    imagens: Mapped[list["ImagemProduto"]] = relationship(
        back_populates="produto",
        cascade="all, delete-orphan",
        order_by="ImagemProduto.ordem",
    )

    __table_args__ = (
        CheckConstraint("preco > 0", name="ck_produto_preco_positivo"),
        CheckConstraint(f"status IN {STATUS_PRODUTO}", name="ck_produto_status"),
    )


class ImagemProduto(Base):
    """Um anúncio pode ter várias fotos."""
    __tablename__ = "imagem_produto"

    id: Mapped[int] = mapped_column(primary_key=True)
    produto_id: Mapped[int] = mapped_column(
        ForeignKey("produto.id", ondelete="CASCADE"), index=True
    )
    # Caminho do arquivo salvo na pasta de uploads (ex.: "produtos/abc123.jpg")
    caminho: Mapped[str] = mapped_column(String(255))
    ordem: Mapped[int] = mapped_column(default=0)

    produto: Mapped[Produto] = relationship(back_populates="imagens")


class Favorito(Base):
    __tablename__ = "favorito"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"))
    produto_id: Mapped[int] = mapped_column(ForeignKey("produto.id", ondelete="CASCADE"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)

    produto: Mapped[Produto] = relationship()

    # Impede o mesmo produto duas vezes nos favoritos do mesmo usuário
    __table_args__ = (
        UniqueConstraint("usuario_id", "produto_id", name="uq_favorito_usuario_produto"),
    )


class ItemCarrinho(Base):
    """
    O carrinho é o conjunto de itens de um usuário.
    Não criamos uma tabela "Carrinho" separada porque ela teria só o
    usuario_id — cada usuário tem exatamente um carrinho.
    """
    __tablename__ = "item_carrinho"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"))
    produto_id: Mapped[int] = mapped_column(ForeignKey("produto.id", ondelete="CASCADE"))
    adicionado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)

    produto: Mapped[Produto] = relationship()

    # Peça única: não faz sentido o mesmo produto 2x no carrinho
    __table_args__ = (
        UniqueConstraint("usuario_id", "produto_id", name="uq_carrinho_usuario_produto"),
    )


class Endereco(Base):
    __tablename__ = "endereco"

    id: Mapped[int] = mapped_column(primary_key=True)
    # unique=True -> cada usuário tem no máximo um endereço
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE"), unique=True
    )
    cep: Mapped[str] = mapped_column(String(9))
    rua: Mapped[str] = mapped_column(String(150))
    numero: Mapped[str] = mapped_column(String(10))
    complemento: Mapped[str | None] = mapped_column(String(100))
    bairro: Mapped[str] = mapped_column(String(100))
    cidade: Mapped[str] = mapped_column(String(100))
    estado: Mapped[str] = mapped_column(String(2))

    usuario: Mapped[Usuario] = relationship(back_populates="endereco")


class Pedido(Base):
    __tablename__ = "pedido"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), index=True)
    # Valores calculados SEMPRE pelo servidor, nunca recebidos do navegador
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    valor_entrega: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(15), default="confirmado")
    # Cópia do endereço no momento da compra. Se o usuário editar o
    # endereço depois, o pedido antigo continua com o endereço correto.
    endereco_entrega: Mapped[str] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)

    itens: Mapped[list["ItemPedido"]] = relationship(
        back_populates="pedido", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(f"status IN {STATUS_PEDIDO}", name="ck_pedido_status"),
    )


class ItemPedido(Base):
    __tablename__ = "item_pedido"

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedido.id", ondelete="CASCADE"))
    # unique=True -> uma peça NUNCA pode estar em dois pedidos.
    # Mesmo que o código tenha um erro, o banco recusa a venda duplicada.
    produto_id: Mapped[int] = mapped_column(ForeignKey("produto.id"), unique=True)
    # Preço no momento da compra (o vendedor não pode alterar depois)
    preco: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    pedido: Mapped[Pedido] = relationship(back_populates="itens")
    produto: Mapped[Produto] = relationship()


class TokenRedefinicaoSenha(Base):
    """Usado no fluxo 'Esqueci minha senha'."""
    __tablename__ = "token_redefinicao_senha"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"))
    # Guardamos o hash do token (como fazemos com a senha)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usado: Mapped[bool] = mapped_column(default=False)
