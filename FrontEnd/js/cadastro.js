/* cadastro.js — usado em cadastro.html */

const formCadastro = document.querySelector(".cadastro-form");
const caixaMensagemCadastro = document.getElementById("mensagem-cadastro");

/*
 * Validação no navegador: avisa o usuário na hora, sem esperar o servidor.
 * O backend valida tudo de novo, porque o navegador pode ser manipulado.
 */
function validarCadastro(form) {
    if (form.nome.value.trim().length < 2) {
        return "Informe seu nome completo.";
    }
    if (!form.email.checkValidity()) {
        return "Informe um e-mail válido.";
    }
    if (!form.querySelector("input[name=sexo]:checked")) {
        return "Selecione uma opção em Sexo.";
    }
    if (form.senha.value.length < 8) {
        return "A senha deve ter pelo menos 8 caracteres.";
    }
    if (form.senha.value !== form["confirmar-senha"].value) {
        return "As senhas não são iguais.";
    }
    return null; // sem erros
}

formCadastro.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    esconderMensagem(caixaMensagemCadastro);

    const erro = validarCadastro(formCadastro);
    if (erro) {
        mostrarMensagem(caixaMensagemCadastro, erro);
        return;
    }

    const botao = formCadastro.querySelector("button[type=submit]");
    botao.disabled = true;

    const email = formCadastro.email.value.trim();
    const senha = formCadastro.senha.value;

    try {
        await apiFetch("/auth/cadastro", {
            method: "POST",
            body: {
                nome: formCadastro.nome.value.trim(),
                email: email,
                senha: senha,
                sexo: formCadastro.querySelector("input[name=sexo]:checked").value,
            },
        });

        // Conta criada: já fazemos o login para a pessoa não digitar de novo
        const dadosLogin = new URLSearchParams({ username: email, password: senha });
        const resposta = await apiFetch("/auth/login", { method: "POST", body: dadosLogin });
        salvarToken(resposta.access_token);
        window.location.href = "home.html";
    } catch (erroServidor) {
        mostrarMensagem(caixaMensagemCadastro, erroServidor.message);
        botao.disabled = false;
    }
});
