/* pedido.js — detalhes de um pedido: pedido.html?id=7 (página privada) */

const parametrosPedido = new URLSearchParams(location.search);
const idPedido = parametrosPedido.get("id");
const pedidoNovo = parametrosPedido.get("novo") === "1"; // veio direto da compra?

const estadoPedido = document.getElementById("estado-pedido");
const textoEstadoPedido = document.getElementById("texto-estado-pedido");


function criarItemPedido(item) {
    const link = `produto.html?id=${item.produto.id}`;

    const linha = document.createElement("div");
    linha.className = "item-pedido";

    const caixaImagem = document.createElement("div");
    caixaImagem.className = "produto-imagem";
    const img = document.createElement("img");
    img.src = urlArquivo(item.produto.imagens[0]?.caminho);
    img.alt = item.produto.nome;
    caixaImagem.append(img);

    const info = document.createElement("div");
    info.className = "produto-info";
    const titulo = document.createElement("h2");
    const linkTitulo = document.createElement("a");
    linkTitulo.href = link;
    linkTitulo.textContent = item.produto.nome;
    titulo.append(linkTitulo);
    // item.preco = preço pago (gravado no pedido), não o preço atual do anúncio
    const preco = document.createElement("p");
    preco.textContent = formatarPreco(item.preco);
    info.append(titulo, preco);

    linha.append(caixaImagem, info);
    return linha;
}


async function carregarPedido() {
    if (!idPedido) {
        textoEstadoPedido.innerHTML = 'Pedido não informado. <a href="meus_pedidos.html">Ver meus pedidos</a>';
        return;
    }
    try {
        const pedido = await apiFetch(`/pedidos/${encodeURIComponent(idPedido)}`);
        const status = STATUS_PEDIDO[pedido.status] || { texto: pedido.status, classe: "" };

        document.title = `Pedido ${numeroPedido(pedido.id)} - ReCloset`;
        document.getElementById("titulo-pedido").textContent = `Pedido ${numeroPedido(pedido.id)}`;
        const data = new Date(pedido.criado_em);
        document.getElementById("data-pedido").textContent =
            `Realizado em ${data.toLocaleDateString("pt-BR")} às ${data.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}`;

        const etiqueta = document.getElementById("status-pedido");
        etiqueta.textContent = status.texto;
        etiqueta.classList.add(status.classe);

        const qtd = pedido.itens.length;
        document.getElementById("qtd-itens").textContent = `${qtd} ${qtd === 1 ? "peça" : "peças"}`;
        document.getElementById("itens-pedido").replaceChildren(...pedido.itens.map(criarItemPedido));

        document.getElementById("valor-subtotal").textContent = formatarPreco(pedido.subtotal);
        document.getElementById("valor-entrega").textContent = formatarPreco(pedido.valor_entrega);
        document.getElementById("valor-total").textContent = formatarPreco(pedido.total);
        document.getElementById("endereco-pedido").textContent = pedido.endereco_entrega;

        if (pedidoNovo) {
            mostrarMensagem(document.getElementById("mensagem-pedido"),
                "Pedido confirmado! Obrigado por comprar no ReCloset.", "sucesso");
            // Tira o "&novo=1" do endereço: ao recarregar, a mensagem não aparece de novo
            history.replaceState(null, "", `pedido.html?id=${pedido.id}`);
        }

        estadoPedido.hidden = true;
        document.getElementById("conteudo-pedido").hidden = false;
    } catch (erro) {
        if (erro.status === 404 || erro.status === 422) {
            textoEstadoPedido.innerHTML = 'Pedido não encontrado. <a href="meus_pedidos.html">Ver meus pedidos</a>';
        } else {
            textoEstadoPedido.textContent = "Não foi possível carregar o pedido. " + erro.message;
        }
    }
}


carregarPedido();
