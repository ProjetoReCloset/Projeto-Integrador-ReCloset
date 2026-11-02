/* perfil.js — usado em perfil.html (api.js já foi carregado no <head>) */

async function carregarPerfil() {
    try {
        // As duas requisições são feitas ao mesmo tempo (Promise.all)
        const [usuario, resumo] = await Promise.all([
            apiFetch("/usuarios/me"),
            apiFetch("/usuarios/me/resumo"),
        ]);

        // textContent (e não innerHTML) impede que um nome com <script>
        // seja executado como código na página.
        document.getElementById("perfil-nome").textContent = usuario.nome;
        // Não temos "nome de usuário" no cadastro: usamos o início do e-mail
        document.getElementById("perfil-usuario").textContent = "@" + usuario.email.split("@")[0];
        document.getElementById("perfil-descricao").textContent =
            usuario.descricao || "Adicione uma descrição em Editar perfil.";
        document.getElementById("perfil-foto").src = urlArquivo(usuario.foto);

        document.getElementById("total-produtos").textContent = resumo.produtos;
        document.getElementById("total-vendas").textContent = resumo.vendas;
        document.getElementById("total-favoritos").textContent = resumo.favoritos;
    } catch (erro) {
        document.getElementById("perfil-descricao").textContent = erro.message;
    }
}

document.getElementById("botao-sair").addEventListener("click", (evento) => {
    evento.preventDefault();
    sair();
});

carregarPerfil();
