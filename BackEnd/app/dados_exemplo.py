"""
Cria dados de EXEMPLO para testar e apresentar o site.

Rodar (dentro de BackEnd/):
    python -m app.dados_exemplo

Cria a vendedora "Loja Exemplo" e 6 peças usando as fotos que já estão
em FrontEnd/img/. Pode rodar mais de uma vez: não duplica nada.
Use apenas em desenvolvimento.
"""
import shutil
from decimal import Decimal

from sqlalchemy import select

from app.config import PASTA_FRONTEND, PASTA_UPLOADS
from app.database import SessionLocal
from app.main import preparar_banco
from app.models import Categoria, ImagemProduto, Produto, Usuario
from app.security import gerar_hash_senha
from app.services.produtos import atualizar_texto_busca

EMAIL = "exemplo@recloset.com"
SENHA = "recloset123"

PECAS = [
    # (nome, categoria, tamanho, preço, foto, descrição)
    ("Blusa de tricô", "feminino", "M", "45.00", "blusatrico.jpg",
     "Blusa de tricô listrada, bem quentinha. Usada poucas vezes, sem furos nem bolinhas."),
    ("Calça jeans wide leg", "feminino", "38", "70.00", "calcawide.jpg",
     "Calça jeans azul escuro, modelo wide leg. Ótimo estado, sem desgaste na barra."),
    ("Tênis branco", "calcados", "37", "120.00", "tenisbranco.jpg",
     "Tênis branco de couro. Solado em bom estado, pequena marca de uso na lateral."),
    ("Camisa xadrez", "masculino", "G", "55.00", "blusaxadrez.jpg",
     "Camisa xadrez preta e branca de flanela. Todos os botões no lugar."),
    ("Short bege", "feminino", "40", "40.00", "shorbege.jpg",
     "Short de sarja bege, cintura alta. Sem manchas."),
    ("Bolsa preta", "acessorios", None, "65.00", "bolsapreta.jpg",
     "Bolsa preta de ombro, alça ajustável. Forro interno em perfeito estado."),
]


def main():
    preparar_banco()
    with SessionLocal() as db:
        vendedora = db.scalar(select(Usuario).where(Usuario.email == EMAIL))
        if vendedora is None:
            vendedora = Usuario(nome="Loja Exemplo", email=EMAIL,
                                senha_hash=gerar_hash_senha(SENHA), sexo="outros",
                                descricao="Conta de exemplo do ReCloset.")
            db.add(vendedora)
            db.flush()  # gera o id sem finalizar a transação

        categorias = {c.slug: c for c in db.scalars(select(Categoria))}
        (PASTA_UPLOADS / "produtos").mkdir(parents=True, exist_ok=True)

        criadas = 0
        for nome, slug, tamanho, preco, foto, descricao in PECAS:
            ja_existe = db.scalar(select(Produto).where(
                Produto.vendedor_id == vendedora.id, Produto.nome == nome))
            if ja_existe:
                continue
            caminho = f"produtos/exemplo_{foto}"
            shutil.copy(PASTA_FRONTEND / "img" / foto, PASTA_UPLOADS / caminho)
            produto = Produto(
                vendedor_id=vendedora.id, categoria_id=categorias[slug].id,
                nome=nome, descricao=descricao, tamanho=tamanho, preco=Decimal(preco),
                imagens=[ImagemProduto(caminho=caminho, ordem=0)],
            )
            atualizar_texto_busca(produto)
            db.add(produto)
            criadas += 1

        db.commit()
    print(f"Pronto! {criadas} peça(s) criada(s).")
    print(f"Login da vendedora de exemplo: {EMAIL} / {SENHA}")


if __name__ == "__main__":
    main()
