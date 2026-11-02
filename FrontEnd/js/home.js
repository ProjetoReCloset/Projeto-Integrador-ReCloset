/* home.js — usado em home.html (página pública: não exige login) */

const listaHome = document.getElementById("lista-produtos");
const estadoHome = document.getElementById("estado-lista");

const QTD_DESTAQUES = 6;


/*
 * Monta um cartão no MESMO formato que já existia no HTML:
 * <article class="produto">
 *   <div class="imagem-produto"> <a><img></a> <button class="favoritar">♡</button> </div>
 *   <div class="informacoes-produto"> <h3><a>Nome</a></h3> <p class="preco">R$ ...</p> </div>
 * </article>
 */
function criarCartaoHome(produto) {
    const link = `produto.html?id=${produto.id}`;

    const cartao = document.createElement("article");
    cartao.className = "produto";

    const caixaImagem = document.createElement("div");
    caixaImagem.className = "imagem-produto";
    const linkImagem = document.createElement("a");
    linkImagem.href = link;
    const img = document.createElement("img");
    img.src = urlArquivo(produto.imagens[0]?.caminho);
    img.alt = produto.nome;
    img.loading = "lazy"; // só baixa a foto quando ela aparecer na tela
    linkImagem.append(img);

    const favoritar = document.createElement("button");
    favoritar.type = "button";
    favoritar.className = "favoritar";
    favoritar.textContent = "♡";
    favoritar.setAttribute("aria-label", `Favoritar ${produto.nome}`);
    favoritar.dataset.produtoId = produto.id;          // usado pelo coracoes.js
    favoritar.dataset.vendedorId = produto.vendedor.id;
    caixaImagem.append(linkImagem, favoritar);

    const info = document.createElement("div");
    info.className = "informacoes-produto";
    const titulo = document.createElement("h3");
    const linkTitulo = document.createElement("a");
    linkTitulo.href = link;
    linkTitulo.textContent = produto.nome;
    titulo.append(linkTitulo);
    const preco = document.createElement("p");
    preco.className = "preco";
    preco.textContent = formatarPreco(produto.preco);
    info.append(titulo, preco);

    cartao.append(caixaImagem, info);
    return cartao;
}


async function carregarDestaques() {
    try {
        // As peças mais recentes que ainda estão disponíveis
        // Produtos e favoritos são buscados ao mesmo tempo
        const [produtos] = await Promise.all([
            apiFetch(`/produtos?limite=${QTD_DESTAQUES}`),
            carregarFavoritos(),
        ]);
        listaHome.replaceChildren(...produtos.map(criarCartaoHome));
        pintarCoracoes(listaHome);

        if (produtos.length === 0) {
            estadoHome.innerHTML = 'Ainda não há peças à venda. <a href="vender.html">Que tal anunciar a primeira?</a>';
        } else {
            estadoHome.textContent = "";
        }
    } catch (erro) {
        estadoHome.textContent = "Não foi possível carregar as peças. " + erro.message;
    }
}


ativarCoracoes(listaHome);
carregarDestaques();
