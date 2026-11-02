/* vender.js — usado em vender.html
 *
 * A mesma tela serve para dois casos:
 *   vender.html        -> cadastrar uma peça nova
 *   vender.html?id=7   -> editar o anúncio 7
 */

const formVenda = document.getElementById("form-venda");
const caixaMensagemVenda = document.getElementById("mensagem-venda");
const campoImagens = document.getElementById("imagem");
const areaPreviews = document.getElementById("previews-fotos");
const botaoPublicar = document.getElementById("botao-publicar");

const MAX_FOTOS = 5;
const TAMANHO_MAX_MB = 5;
const TIPOS_ACEITOS = ["image/jpeg", "image/png", "image/webp"];

// Lê o "?id=7" do endereço da página (null quando é um anúncio novo)
const idEdicao = new URLSearchParams(location.search).get("id");

let fotosSalvas = []; // fotos que já estão no servidor (só na edição): [{id, caminho}]
let fotosNovas = [];  // arquivos escolhidos agora, ainda não enviados: [File]


/* ---------- Miniaturas ---------- */

function criarMiniatura(src, aoRemover) {
    const caixa = document.createElement("div");
    caixa.className = "preview-foto";

    const img = document.createElement("img");
    img.src = src;
    img.alt = "Foto da peça";

    const botao = document.createElement("button");
    botao.type = "button";
    botao.className = "remover-foto";
    botao.textContent = "×";
    botao.setAttribute("aria-label", "Remover foto");
    botao.addEventListener("click", aoRemover);

    caixa.append(img, botao);
    return caixa;
}

function desenharMiniaturas() {
    areaPreviews.replaceChildren(); // limpa

    fotosSalvas.forEach((foto) => {
        areaPreviews.append(criarMiniatura(urlArquivo(foto.caminho), () => removerFotoSalva(foto)));
    });
    fotosNovas.forEach((arquivo, indice) => {
        // URL.createObjectURL mostra o arquivo do computador sem enviá-lo
        areaPreviews.append(criarMiniatura(URL.createObjectURL(arquivo), () => {
            fotosNovas.splice(indice, 1);
            desenharMiniaturas();
        }));
    });

    const total = fotosSalvas.length + fotosNovas.length;
    document.getElementById("dica-fotos").textContent =
        `${total} de ${MAX_FOTOS} fotos (JPG, PNG ou WEBP, até ${TAMANHO_MAX_MB} MB cada).`;
}


/* ---------- Escolher fotos ---------- */

campoImagens.addEventListener("change", () => {
    esconderMensagem(caixaMensagemVenda);

    for (const arquivo of campoImagens.files) {
        if (fotosSalvas.length + fotosNovas.length >= MAX_FOTOS) {
            mostrarMensagem(caixaMensagemVenda, `Cada anúncio pode ter no máximo ${MAX_FOTOS} fotos.`);
            break;
        }
        // Conferência rápida no navegador; o servidor confere o conteúdo de verdade
        if (!TIPOS_ACEITOS.includes(arquivo.type)) {
            mostrarMensagem(caixaMensagemVenda, `"${arquivo.name}" não é JPG, PNG ou WEBP.`);
            continue;
        }
        if (arquivo.size > TAMANHO_MAX_MB * 1024 * 1024) {
            mostrarMensagem(caixaMensagemVenda, `"${arquivo.name}" passa de ${TAMANHO_MAX_MB} MB.`);
            continue;
        }
        fotosNovas.push(arquivo);
    }

    campoImagens.value = ""; // permite escolher o mesmo arquivo de novo depois
    desenharMiniaturas();
});


async function removerFotoSalva(foto) {
    // Na edição, a foto já está no servidor: removemos lá na hora
    if (fotosSalvas.length + fotosNovas.length === 1) {
        mostrarMensagem(caixaMensagemVenda, "O anúncio precisa ter pelo menos uma foto.");
        return;
    }
    try {
        const produto = await apiFetch(`/produtos/${idEdicao}/imagens/${foto.id}`, { method: "DELETE" });
        fotosSalvas = produto.imagens;
        desenharMiniaturas();
    } catch (erro) {
        mostrarMensagem(caixaMensagemVenda, erro.message);
    }
}


/* ---------- Preço ---------- */

/* Aceita "45", "45,9", "45,90", "R$ 1.234,56" e devolve "45.90" (ou null se inválido) */
function lerPreco(texto) {
    let limpo = texto.replace(/R\$|\s/g, "");
    if (limpo.includes(",")) {
        limpo = limpo.replace(/\./g, "").replace(",", "."); // formato brasileiro
    }
    if (!/^\d+(\.\d{1,2})?$/.test(limpo) || Number(limpo) <= 0) {
        return null;
    }
    return Number(limpo).toFixed(2);
}


/* ---------- Validação e envio ---------- */

function validarVenda(form) {
    if (fotosSalvas.length + fotosNovas.length === 0) {
        return "Adicione pelo menos uma foto da peça.";
    }
    if (form.nome.value.trim().length < 3) {
        return "Informe o título da peça (mínimo 3 letras).";
    }
    if (!form.categoria.value) {
        return "Selecione a categoria.";
    }
    if (form.descricao.value.trim().length < 10) {
        return "Descreva a peça e seu estado de conservação (mínimo 10 letras).";
    }
    if (lerPreco(form.preco.value) === null) {
        return "Informe um preço válido. Ex.: 45,90";
    }
    return null;
}

function dadosDoFormulario() {
    return {
        nome: formVenda.nome.value.trim(),
        descricao: formVenda.descricao.value.trim(),
        tamanho: formVenda.tamanho.value.trim(),
        categoria: formVenda.categoria.value,
        preco: lerPreco(formVenda.preco.value),
    };
}

formVenda.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    esconderMensagem(caixaMensagemVenda);

    const erro = validarVenda(formVenda);
    if (erro) {
        mostrarMensagem(caixaMensagemVenda, erro);
        return;
    }

    botaoPublicar.disabled = true;
    const dados = dadosDoFormulario();

    try {
        if (idEdicao) {
            // Edição: textos vão como JSON; as fotos novas, numa segunda requisição
            await apiFetch(`/produtos/${idEdicao}`, { method: "PUT", body: dados });
            if (fotosNovas.length > 0) {
                const envio = new FormData();
                fotosNovas.forEach((arquivo) => envio.append("imagens", arquivo));
                await apiFetch(`/produtos/${idEdicao}/imagens`, { method: "POST", body: envio });
            }
            window.location.href = "meus_anuncios.html?aviso=editado";
        } else {
            // Cadastro: textos e fotos juntos num único FormData (multipart)
            const envio = new FormData();
            for (const [campo, valor] of Object.entries(dados)) {
                envio.append(campo, valor);
            }
            fotosNovas.forEach((arquivo) => envio.append("imagens", arquivo));
            await apiFetch("/produtos", { method: "POST", body: envio });
            window.location.href = "meus_anuncios.html?aviso=criado";
        }
    } catch (erroServidor) {
        mostrarMensagem(caixaMensagemVenda, erroServidor.message);
        botaoPublicar.disabled = false;
    }
});


/* ---------- Modo edição ---------- */

async function carregarParaEdicao() {
    document.getElementById("titulo-formulario").textContent = "Editar anúncio";
    document.title = "ReCloset - Editar anúncio";
    botaoPublicar.textContent = "Salvar alterações";

    try {
        const [produto, eu] = await Promise.all([
            apiFetch(`/produtos/${idEdicao}`),
            apiFetch("/usuarios/me"),
        ]);

        // O servidor também bloqueia, mas assim avisamos antes de a pessoa digitar
        if (produto.vendedor.id !== eu.id) {
            throw new Error("Este anúncio não é seu.");
        }
        if (produto.status === "vendido") {
            throw new Error("Esta peça já foi vendida e não pode mais ser alterada.");
        }

        formVenda.nome.value = produto.nome;
        formVenda.tamanho.value = produto.tamanho || "";
        formVenda.categoria.value = produto.categoria.slug;
        formVenda.descricao.value = produto.descricao;
        formVenda.preco.value = Number(produto.preco).toFixed(2).replace(".", ",");
        fotosSalvas = produto.imagens;
        desenharMiniaturas();
    } catch (erro) {
        mostrarMensagem(caixaMensagemVenda, erro.message);
        botaoPublicar.disabled = true;
    }
}

if (idEdicao) {
    carregarParaEdicao();
}
