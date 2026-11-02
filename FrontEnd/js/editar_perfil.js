/* editar_perfil.js — usado em editar_perfil.html */

const formEditar = document.querySelector(".form-editar");
const caixaMensagemEditar = document.getElementById("mensagem-editar");
const campoFoto = document.getElementById("foto");
const previewFoto = document.getElementById("foto-preview");

const TIPOS_IMAGEM = ["image/jpeg", "image/png", "image/webp"];
const TAMANHO_MAX_MB = 5;


/* O banco guarda só os dígitos (16999991234); na tela mostramos (16) 99999-1234 */
function formatarTelefone(digitos) {
    if (!digitos) {
        return "";
    }
    const ddd = digitos.slice(0, 2);
    const resto = digitos.slice(2);
    const corte = resto.length === 9 ? 5 : 4; // celular tem 9 dígitos, fixo tem 8
    return `(${ddd}) ${resto.slice(0, corte)}-${resto.slice(corte)}`;
}


/* 1. Preenche o formulário com os dados atuais */
async function carregarDados() {
    try {
        const usuario = await apiFetch("/usuarios/me");
        formEditar.nome.value = usuario.nome;
        formEditar.email.value = usuario.email;
        formEditar.sexo.value = usuario.sexo;
        formEditar.telefone.value = formatarTelefone(usuario.telefone);
        formEditar.descricao.value = usuario.descricao || "";
        previewFoto.src = urlArquivo(usuario.foto);
    } catch (erro) {
        mostrarMensagem(caixaMensagemEditar, erro.message);
    }
}


/* 2. Ao escolher uma foto: confere e mostra uma prévia (ainda não envia) */
campoFoto.addEventListener("change", () => {
    esconderMensagem(caixaMensagemEditar);
    const arquivo = campoFoto.files[0];
    if (!arquivo) {
        return;
    }
    // Esta conferência é só para avisar rápido. O servidor confere de novo,
    // lendo o conteúdo do arquivo (o tipo informado pelo navegador pode mentir).
    if (!TIPOS_IMAGEM.includes(arquivo.type)) {
        mostrarMensagem(caixaMensagemEditar, "Escolha uma imagem JPG, PNG ou WEBP.");
        campoFoto.value = "";
        return;
    }
    if (arquivo.size > TAMANHO_MAX_MB * 1024 * 1024) {
        mostrarMensagem(caixaMensagemEditar, `A imagem deve ter no máximo ${TAMANHO_MAX_MB} MB.`);
        campoFoto.value = "";
        return;
    }
    // Cria um endereço temporário para mostrar o arquivo local na tela
    previewFoto.src = URL.createObjectURL(arquivo);
});


function validarEdicao(form) {
    if (form.nome.value.trim().length < 2) {
        return "Informe seu nome completo.";
    }
    if (!form.email.checkValidity() || !form.email.value.trim()) {
        return "Informe um e-mail válido.";
    }
    const digitosTelefone = form.telefone.value.replace(/\D/g, "");
    if (digitosTelefone && digitosTelefone.length !== 10 && digitosTelefone.length !== 11) {
        return "Telefone: informe DDD + número (10 ou 11 dígitos).";
    }
    return null;
}


/* 3. Salvar: primeiro os dados, depois a foto (se uma nova foi escolhida) */
formEditar.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    esconderMensagem(caixaMensagemEditar);

    const erro = validarEdicao(formEditar);
    if (erro) {
        mostrarMensagem(caixaMensagemEditar, erro);
        return;
    }

    const botao = formEditar.querySelector("button[type=submit]");
    botao.disabled = true;

    try {
        await apiFetch("/usuarios/me", {
            method: "PATCH",
            body: {
                nome: formEditar.nome.value.trim(),
                email: formEditar.email.value.trim(),
                sexo: formEditar.sexo.value,
                telefone: formEditar.telefone.value.trim(),
                descricao: formEditar.descricao.value.trim(),
            },
        });

        if (campoFoto.files[0]) {
            // Arquivos vão como FormData (multipart), não como JSON
            const dadosFoto = new FormData();
            dadosFoto.append("foto", campoFoto.files[0]);
            const usuario = await apiFetch("/usuarios/me/foto", { method: "POST", body: dadosFoto });
            previewFoto.src = urlArquivo(usuario.foto);
            campoFoto.value = "";
        }

        mostrarMensagem(caixaMensagemEditar, "Alterações salvas com sucesso!", "sucesso");
    } catch (erroServidor) {
        mostrarMensagem(caixaMensagemEditar, erroServidor.message);
    } finally {
        botao.disabled = false;
    }
});


carregarDados();
