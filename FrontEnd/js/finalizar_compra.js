/* finalizar_compra.js — usado em finalizar_compra.html (página privada)
 *
 * Mostra endereço, itens e valores (calculados pelo servidor) e, ao
 * confirmar, cria o pedido. Toda a proteção contra venda duplicada
 * está no servidor (BackEnd/app/services/pedidos.py).
 */

const caixaMensagemRevisao = document.getElementById("mensagem-revisao");
const estadoRevisao = document.getElementById("estado-revisao");
const conteudoRevisao = document.getElementById("conteudo-revisao");
const botaoConfirmar = document.getElementById("botao-confirmar");

let totalExibido = null; // total que a pessoa está vendo (o servidor confere)


function criarLinhaItem(produto) {
    // Mesmo formato do carrinho, mas sem o botão de excluir
    const linha = document.createElement("article");
    linha.className = "produto-carrinho";

    const caixaImagem = document.createElement("div");
    caixaImagem.className = "produto-imagem";
    const img = document.createElement("img");
    img.src = urlArquivo(produto.imagens[0]?.caminho);
    img.alt = produto.nome;
    caixaImagem.append(img);

    const dados = document.createElement("div");
    dados.className = "produto-dados";
    const titulo = document.createElement("h2");
    titulo.textContent = produto.nome;
    const tamanho = document.createElement("p");
    tamanho.textContent = `Tamanho: ${produto.tamanho || "único"}`;
    const preco = document.createElement("strong");
    preco.textContent = formatarPreco(produto.preco);
    dados.append(titulo, tamanho, preco);

    linha.append(caixaImagem, dados);
    return linha;
}


function textoEndereco(e) {
    const complemento = e.complemento ? ` - ${e.complemento}` : "";
    return `${e.rua}, ${e.numero}${complemento}\n${e.bairro} - ${e.cidade}/${e.estado}\nCEP: ${e.cep}`;
}


async function carregarRevisao() {
    try {
        const [carrinho, endereco] = await Promise.all([
            apiFetch("/carrinho"),
            // 404 = ainda não cadastrou endereço (não é um erro da página)
            apiFetch("/endereco").catch((erro) => {
                if (erro.status === 404) return null;
                throw erro;
            }),
        ]);

        if (carrinho.itens.length === 0) {
            window.location.href = "carrinho.html"; // nada para revisar
            return;
        }

        // Endereço
        const paragrafoEndereco = document.getElementById("texto-endereco");
        const linkEndereco = document.getElementById("link-endereco");
        if (endereco) {
            paragrafoEndereco.textContent = textoEndereco(endereco);
            paragrafoEndereco.className = "";
            linkEndereco.textContent = "Alterar";
        } else {
            paragrafoEndereco.textContent = "Você ainda não cadastrou um endereço de entrega.";
            paragrafoEndereco.className = "sem-endereco";
            linkEndereco.textContent = "Cadastrar endereço";
        }

        // Itens disponíveis
        const disponiveis = carrinho.itens.filter((item) => item.disponivel).map((item) => item.produto);
        document.getElementById("itens-revisao").replaceChildren(...disponiveis.map(criarLinhaItem));
        const plural = carrinho.quantidade === 1 ? "peça" : "peças";
        document.getElementById("titulo-itens").textContent = `Itens (${carrinho.quantidade} ${plural})`;

        // Valores
        document.getElementById("rotulo-subtotal").textContent = `Subtotal (${carrinho.quantidade} ${plural})`;
        document.getElementById("valor-subtotal").textContent = formatarPreco(carrinho.subtotal);
        document.getElementById("valor-entrega").textContent = formatarPreco(carrinho.valor_entrega);
        document.getElementById("valor-total").textContent = formatarPreco(carrinho.total);
        totalExibido = carrinho.total;

        // Pode confirmar?
        esconderMensagem(caixaMensagemRevisao);
        if (!carrinho.pode_finalizar) {
            mostrarMensagem(caixaMensagemRevisao,
                "Uma ou mais peças do seu carrinho já foram vendidas. Volte ao carrinho e remova-as.");
        } else if (!endereco) {
            mostrarMensagem(caixaMensagemRevisao, "Cadastre um endereço de entrega para continuar.");
        }
        botaoConfirmar.disabled = !carrinho.pode_finalizar || !endereco;

        estadoRevisao.textContent = "";
        conteudoRevisao.hidden = false;
    } catch (erro) {
        estadoRevisao.textContent = "Não foi possível carregar o pedido. " + erro.message;
    }
}


botaoConfirmar.addEventListener("click", async () => {
    botaoConfirmar.disabled = true; // evita dois pedidos com clique duplo
    botaoConfirmar.textContent = "Confirmando...";
    esconderMensagem(caixaMensagemRevisao);

    try {
        // Enviamos só o total que a pessoa VIU, para o servidor conferir.
        // Os valores de verdade são recalculados lá, com os preços do banco.
        const pedido = await apiFetch("/pedidos", {
            method: "POST",
            body: { total_confirmado: totalExibido },
        });
        window.location.href = `pedido.html?id=${pedido.id}&novo=1`;
    } catch (erro) {
        // Ex.: "A peça X acabou de ser vendida para outra pessoa."
        botaoConfirmar.textContent = "Confirmar pedido";
        await carregarRevisao(); // mostra a situação atualizada...
        mostrarMensagem(caixaMensagemRevisao, erro.message); // ...com o motivo do erro
    }
});


carregarRevisao();
