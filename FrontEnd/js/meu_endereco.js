/* meu_endereco.js — usado em meu_endereco.html
 *
 * A página tem 3 "modos", e só um aparece por vez:
 *   - card-endereco: mostra o endereço salvo
 *   - sem-endereco:  aviso + botão para cadastrar
 *   - form-endereco: formulário para cadastrar ou editar
 */

const cardEndereco = document.getElementById("card-endereco");
const semEndereco = document.getElementById("sem-endereco");
const formEndereco = document.getElementById("form-endereco");
const caixaMensagemEndereco = document.getElementById("mensagem-endereco");

let enderecoAtual = null; // guarda o endereço vindo da API (ou null)

// Veio da revisão do pedido? (meu_endereco.html?voltar=finalizar)
// Só aceitamos esse valor fixo: nunca redirecionamos para um endereço qualquer da URL.
const voltarParaCompra = new URLSearchParams(location.search).get("voltar") === "finalizar";


function mostrarModo(elemento) {
    [cardEndereco, semEndereco, formEndereco].forEach((el) => el.classList.add("escondido"));
    elemento.classList.remove("escondido");
}


function exibirEndereco(endereco) {
    const complemento = endereco.complemento ? ` - ${endereco.complemento}` : "";
    document.getElementById("linha-rua").textContent = `${endereco.rua}, ${endereco.numero}${complemento}`;
    document.getElementById("linha-cidade").textContent =
        `${endereco.bairro} - ${endereco.cidade}/${endereco.estado}`;
    document.getElementById("linha-cep").textContent = `CEP: ${endereco.cep}`;
    mostrarModo(cardEndereco);
}


async function carregarEndereco() {
    try {
        enderecoAtual = await apiFetch("/endereco");
        exibirEndereco(enderecoAtual);
    } catch (erro) {
        if (erro.status === 404) {
            enderecoAtual = null;
            mostrarModo(semEndereco); // ainda não tem endereço: não é um erro
        } else {
            mostrarMensagem(caixaMensagemEndereco, erro.message);
        }
    }
}


function abrirFormulario() {
    esconderMensagem(caixaMensagemEndereco);
    formEndereco.reset();
    if (enderecoAtual) {
        // Editando: preenche com os dados atuais
        for (const campo of ["cep", "rua", "numero", "complemento", "bairro", "cidade", "estado"]) {
            formEndereco[campo].value = enderecoAtual[campo] || "";
        }
    }
    mostrarModo(formEndereco);
    formEndereco.cep.focus();
}


/* Máscara do CEP: digita 15990000 e aparece 15990-000 */
formEndereco.cep.addEventListener("input", () => {
    const numeros = formEndereco.cep.value.replace(/\D/g, "").slice(0, 8);
    formEndereco.cep.value = numeros.length > 5 ? numeros.slice(0, 5) + "-" + numeros.slice(5) : numeros;
});


function validarEndereco(form) {
    if (form.cep.value.replace(/\D/g, "").length !== 8) {
        return "Informe um CEP com 8 dígitos.";
    }
    const obrigatorios = { rua: "a rua", numero: "o número", bairro: "o bairro", cidade: "a cidade" };
    for (const [campo, nome] of Object.entries(obrigatorios)) {
        if (!form[campo].value.trim()) {
            return `Informe ${nome}.`;
        }
    }
    if (!form.estado.value) {
        return "Selecione o estado.";
    }
    return null;
}


formEndereco.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    esconderMensagem(caixaMensagemEndereco);

    const erro = validarEndereco(formEndereco);
    if (erro) {
        mostrarMensagem(caixaMensagemEndereco, erro);
        return;
    }

    const botao = formEndereco.querySelector("button[type=submit]");
    botao.disabled = true;

    try {
        enderecoAtual = await apiFetch("/endereco", {
            method: "PUT",
            body: {
                cep: formEndereco.cep.value,
                rua: formEndereco.rua.value.trim(),
                numero: formEndereco.numero.value.trim(),
                complemento: formEndereco.complemento.value.trim(),
                bairro: formEndereco.bairro.value.trim(),
                cidade: formEndereco.cidade.value.trim(),
                estado: formEndereco.estado.value,
            },
        });
        if (voltarParaCompra) {
            window.location.href = "finalizar_compra.html"; // continua a compra
            return;
        }
        exibirEndereco(enderecoAtual);
        mostrarMensagem(caixaMensagemEndereco, "Endereço salvo com sucesso!", "sucesso");
    } catch (erroServidor) {
        mostrarMensagem(caixaMensagemEndereco, erroServidor.message);
    } finally {
        botao.disabled = false;
    }
});


document.getElementById("botao-excluir-endereco").addEventListener("click", async () => {
    if (!confirm("Deseja mesmo excluir seu endereço?")) {
        return;
    }
    try {
        await apiFetch("/endereco", { method: "DELETE" });
        enderecoAtual = null;
        mostrarModo(semEndereco);
        mostrarMensagem(caixaMensagemEndereco, "Endereço excluído.", "sucesso");
    } catch (erro) {
        mostrarMensagem(caixaMensagemEndereco, erro.message);
    }
});

document.getElementById("botao-editar-endereco").addEventListener("click", abrirFormulario);
document.getElementById("botao-novo-endereco").addEventListener("click", abrirFormulario);
document.getElementById("botao-cancelar").addEventListener("click", () => {
    esconderMensagem(caixaMensagemEndereco);
    mostrarModo(enderecoAtual ? cardEndereco : semEndereco);
});


// Na volta para a compra, a seta também leva para a revisão do pedido
if (voltarParaCompra) {
    document.querySelector(".botao-voltar").href = "finalizar_compra.html";
}

carregarEndereco().then(() => {
    // Veio da compra sem endereço: já abre o formulário
    if (voltarParaCompra && !enderecoAtual) {
        abrirFormulario();
    }
});
