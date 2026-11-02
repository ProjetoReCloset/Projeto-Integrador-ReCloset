/* meus_pedidos.js — usado em meus_pedidos.html (página privada) */

const listaPedidos = document.getElementById("lista-pedidos");
const estadoPedidos = document.getElementById("estado-pedidos");
const textoEstadoPedidos = document.getElementById("texto-estado-pedidos");


/* Cartão no mesmo formato do HTML original (div.pedido) */
function criarCartaoPedido(pedido) {
    const status = STATUS_PEDIDO[pedido.status] || { texto: pedido.status, classe: "" };
    const primeiro = pedido.itens[0].produto;
    const outros = pedido.itens.length - 1;

    const cartao = document.createElement("div");
    cartao.className = "pedido";

    const topo = document.createElement("div");
    topo.className = "pedido-topo";
    const numero = document.createElement("strong");
    numero.textContent = `Pedido ${numeroPedido(pedido.id)}`;
    const etiqueta = document.createElement("span");
    etiqueta.className = `status ${status.classe}`;
    etiqueta.textContent = status.texto;
    topo.append(numero, etiqueta);

    const produto = document.createElement("div");
    produto.className = "pedido-produto";
    const caixaImagem = document.createElement("div");
    caixaImagem.className = "produto-imagem";
    const img = document.createElement("img");
    img.src = urlArquivo(primeiro.imagens[0]?.caminho);
    img.alt = primeiro.nome;
    caixaImagem.append(img);

    const info = document.createElement("div");
    info.className = "produto-info";
    const titulo = document.createElement("h2");
    // Ex.: "Blusa de tricô" ou "Blusa de tricô e mais 2 peças"
    titulo.textContent = outros > 0
        ? `${primeiro.nome} e mais ${outros} ${outros === 1 ? "peça" : "peças"}`
        : primeiro.nome;
    const total = document.createElement("p");
    total.textContent = formatarPreco(pedido.total);
    const data = document.createElement("small");
    data.textContent = "Pedido realizado em " + new Date(pedido.criado_em).toLocaleDateString("pt-BR");
    info.append(titulo, total, data);
    produto.append(caixaImagem, info);

    const detalhes = document.createElement("button");
    detalhes.type = "button";
    detalhes.className = "botao-detalhes";
    detalhes.textContent = "Ver detalhes";
    detalhes.addEventListener("click", () => {
        window.location.href = `pedido.html?id=${pedido.id}`;
    });

    cartao.append(topo, produto, detalhes);
    return cartao;
}


async function carregarPedidos() {
    try {
        const pedidos = await apiFetch("/pedidos");
        listaPedidos.replaceChildren(...pedidos.map(criarCartaoPedido));

        if (pedidos.length === 0) {
            textoEstadoPedidos.innerHTML =
                'Você ainda não fez nenhum pedido. <a href="ver_mais.html">Ver peças</a>';
        } else {
            estadoPedidos.hidden = true;
        }
    } catch (erro) {
        textoEstadoPedidos.textContent = "Não foi possível carregar seus pedidos. " + erro.message;
    }
}


carregarPedidos();
