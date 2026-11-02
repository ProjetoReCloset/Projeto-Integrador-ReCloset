/* ver_mais.js — catálogo completo (página pública)
 *
 * Os filtros ficam no endereço da página, por exemplo:
 *   ver_mais.html?busca=blusa&categoria=feminino&ordem=menor_preco
 * Assim dá para recarregar, voltar ou compartilhar o link sem perder a busca.
 */

const listaCatalogo = document.getElementById("lista-catalogo");
const estadoCatalogo = document.getElementById("estado-catalogo");
const resumoBusca = document.getElementById("resumo-busca");
const seletorOrdem = document.getElementById("ordem");

const NOMES_CATEGORIAS = {
    feminino: "Feminino", masculino: "Masculino", acessorios: "Acessórios", calcados: "Calçados",
};

// Filtros atuais, lidos do endereço da página
const parametros = new URLSearchParams(location.search);
const filtros = {
    busca: parametros.get("busca") || "",
    categoria: NOMES_CATEGORIAS[parametros.get("categoria")] ? parametros.get("categoria") : "",
    ordem: ["menor_preco", "maior_preco"].includes(parametros.get("ordem")) ? parametros.get("ordem") : "recentes",
};


/* Cartão no mesmo formato que já existia no ver_mais.html */
function criarCartaoCatalogo(produto) {
    const link = `produto.html?id=${produto.id}`;

    const cartao = document.createElement("article");
    cartao.className = "produto";

    const foto = document.createElement("div");
    foto.className = "foto";
    const img = document.createElement("img");
    img.src = urlArquivo(produto.imagens[0]?.caminho);
    img.alt = produto.nome;
    img.loading = "lazy";
    const coracao = document.createElement("button");
    coracao.type = "button";
    coracao.className = "coracao";
    coracao.textContent = "♡";
    coracao.setAttribute("aria-label", `Favoritar ${produto.nome}`);
    coracao.dataset.produtoId = produto.id;          // usado pelo coracoes.js
    coracao.dataset.vendedorId = produto.vendedor.id;
    foto.append(img, coracao);

    const dados = document.createElement("div");
    dados.className = "dados";

    const categoria = document.createElement("p");
    categoria.className = "categoria";
    categoria.textContent = produto.categoria.nome;

    const titulo = document.createElement("h2");
    const linkTitulo = document.createElement("a");
    linkTitulo.href = link;
    linkTitulo.textContent = produto.nome;
    titulo.append(linkTitulo);

    const tamanho = document.createElement("p");
    tamanho.className = "tamanho";
    tamanho.textContent = produto.tamanho ? `Tamanho ${produto.tamanho}` : "Tamanho único";

    const preco = document.createElement("p");
    preco.className = "preco";
    preco.textContent = formatarPreco(produto.preco);

    const botao = document.createElement("a");
    botao.className = "botao";
    botao.href = link;
    botao.textContent = "Ver produto";

    dados.append(categoria, titulo, tamanho, preco, botao);
    cartao.append(foto, dados);
    return cartao;
}


/* Atualiza a aparência dos controles conforme os filtros */
function desenharControles() {
    document.querySelectorAll(".filtro").forEach((botao) => {
        botao.classList.toggle("ativo", botao.dataset.categoria === filtros.categoria);
    });
    seletorOrdem.value = filtros.ordem;

    if (filtros.busca) {
        resumoBusca.replaceChildren(`Resultados para "${filtros.busca}"`);
        const limpar = document.createElement("a");
        limpar.href = "#";
        limpar.textContent = "Limpar busca";
        limpar.addEventListener("click", (evento) => {
            evento.preventDefault();
            filtros.busca = "";
            document.querySelector(".pesquisa input").value = "";
            aplicarFiltros();
        });
        resumoBusca.append(limpar);
        resumoBusca.classList.remove("escondido");
    } else {
        resumoBusca.classList.add("escondido");
    }
}


async function carregarCatalogo() {
    desenharControles();
    estadoCatalogo.textContent = "Carregando peças...";

    // Só envia para a API os filtros que estão preenchidos
    const consulta = new URLSearchParams({ ordem: filtros.ordem });
    if (filtros.busca) consulta.set("busca", filtros.busca);
    if (filtros.categoria) consulta.set("categoria", filtros.categoria);

    try {
        const produtos = await apiFetch(`/produtos?${consulta}`);
        listaCatalogo.replaceChildren(...produtos.map(criarCartaoCatalogo));
        pintarCoracoes(listaCatalogo);

        if (produtos.length > 0) {
            estadoCatalogo.textContent = "";
        } else if (filtros.busca || filtros.categoria) {
            estadoCatalogo.textContent = "Nenhuma peça encontrada com esses filtros.";
        } else {
            estadoCatalogo.textContent = "Ainda não há peças à venda.";
        }
    } catch (erro) {
        listaCatalogo.replaceChildren();
        estadoCatalogo.textContent = "Não foi possível carregar as peças. " + erro.message;
    }
}


/* Grava os filtros no endereço (sem recarregar a página) e busca de novo */
function aplicarFiltros() {
    const novaUrl = new URLSearchParams();
    if (filtros.busca) novaUrl.set("busca", filtros.busca);
    if (filtros.categoria) novaUrl.set("categoria", filtros.categoria);
    if (filtros.ordem !== "recentes") novaUrl.set("ordem", filtros.ordem);
    const texto = novaUrl.toString();
    history.replaceState(null, "", texto ? `?${texto}` : location.pathname);
    carregarCatalogo();
}


document.getElementById("filtros").addEventListener("click", (evento) => {
    const botao = evento.target.closest(".filtro");
    if (!botao) return;
    evento.preventDefault(); // não recarrega: só troca o filtro
    filtros.categoria = botao.dataset.categoria;
    aplicarFiltros();
});

seletorOrdem.addEventListener("change", () => {
    filtros.ordem = seletorOrdem.value;
    aplicarFiltros();
});


ativarCoracoes(listaCatalogo);
// Os favoritos só precisam ser carregados uma vez (não a cada troca de filtro)
carregarFavoritos().then(() => pintarCoracoes(listaCatalogo));
carregarCatalogo();
