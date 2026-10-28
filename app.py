"""Assistente de Gestão Híbrida.

Produto aplicado da dissertação "Otimização da Gestão de Projetos de Inovação
Industrial: um estudo de caso no Programa Smart Factory da CNI" (UFABC).
O modelo de linguagem é configurado apenas por instruções e pela base de
conhecimento do arquivo base_conhecimento.md; não há treinamento nem ajuste fino.
"""

from pathlib import Path

import streamlit as st
from google import genai
from google.genai import types

MODELO_PADRAO = "gemini-3.8-flash"
LIMITE_MENSAGENS = 20  # por sessão, para proteger a cota da chave de API

st.set_page_config(page_title="Assistente de Gestão Híbrida", page_icon="🛠️", layout="wide")

INSTRUCOES = (Path(__file__).parent / "base_conhecimento.md").read_text(encoding="utf-8")

EXEMPLOS = {
    "Cenário A": dict(
        trl=6, meta=8, prazo=12, restante=11, abordagem="Preditiva", escopo="Detalhado e fechado",
        validacao="Só ao final", aprovacao="4 instâncias de aprovação, cerca de 45 dias por fase",
        remanejamento="Não permitido", parceiras=1, validadoras=20,
        dificuldade="Exemplo (cenário derivado do Projeto A): o escopo levou mais de quatro meses para ser "
        "aprovado e a equipe só deve testar a solução nas empresas no final. Todo pedido de mudança passa por "
        "várias aprovações. As parcerias são apenas com empresas da região.",
    ),
    "Cenário B": dict(
        trl=6, meta=8, prazo=12, restante=7, abordagem="Híbrida", escopo="Em blocos funcionais",
        validacao="Contínuas, ao longo da execução",
        aprovacao="Decisões técnicas na equipe; mudanças de arquitetura passam por 3 níveis institucionais (cerca de 2 semanas)",
        remanejamento="Só com nova aprovação formal", parceiras=1, validadoras=20,
        dificuldade="Exemplo (cenário derivado do Projeto B): o projeto usa sprints e valida incrementos com as "
        "empresas, mas a compra de sensores atrasou por aprovações internas. As validadoras dizem que não sabem "
        "em que etapa o projeto está nem como os dados que enviaram foram usados.",
    ),
    "Cenário C": dict(
        trl=6, meta=8, prazo=12, restante=6, abordagem="Preditiva", escopo="Detalhado e fechado",
        validacao="Ainda não previstas", aprovacao="Várias instâncias, cerca de 50 dias por fase",
        remanejamento="Só com nova aprovação formal", parceiras=1, validadoras=20,
        dificuldade="Exemplo (cenário derivado do Projeto C): o projeto começou preditivo e já está na metade do "
        "prazo. A equipe gasta muito tempo ajustando relatórios para aprovação e quer adotar práticas ágeis a "
        "partir de agora. O orçamento não permite remanejar recursos entre fases.",
    ),
}

OPCOES = {
    "abordagem": ["Preditiva", "Ágil", "Híbrida", "Indefinida"],
    "escopo": ["Detalhado e fechado", "Em blocos funcionais", "Indefinido"],
    "validacao": ["Contínuas, ao longo da execução", "Só ao final", "Ainda não previstas"],
    "remanejamento": ["Permitido com limite definido", "Só com nova aprovação formal", "Não permitido", "Não sei"],
}

# ---------- estado da sessão ----------
if "historico" not in st.session_state:
    st.session_state.historico = []  # lista de {"role": "user"|"model", "text": str}


def carregar_exemplo(nome):
    for chave, valor in EXEMPLOS[nome].items():
        st.session_state["f_" + chave] = valor


if "f_trl" not in st.session_state:
    carregar_exemplo("Cenário A")


def nova_consulta():
    st.session_state.historico = []


@st.cache_resource
def cliente():
    return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])


def responder(historico):
    """Envia a conversa ao Gemini e devolve o texto em fluxo contínuo."""
    conteudo = [
        types.Content(role=m["role"], parts=[types.Part(text=m["text"])]) for m in historico[-12:]
    ]
    fluxo = cliente().models.generate_content_stream(
        model=st.secrets.get("GEMINI_MODEL", MODELO_PADRAO),
        contents=conteudo,
        config=types.GenerateContentConfig(system_instruction=INSTRUCOES, temperature=0.3),
    )
    for parte in fluxo:
        if parte.text:
            yield parte.text


def enviar(texto):
    if len(st.session_state.historico) >= LIMITE_MENSAGENS * 2:
        st.warning("Esta sessão atingiu o limite de mensagens. Clique em Nova consulta para recomeçar.")
        return
    st.session_state.historico.append({"role": "user", "text": texto})
    with st.chat_message("user"):
        st.markdown(texto)
    with st.chat_message("assistant"):
        try:
            resposta = st.write_stream(responder(st.session_state.historico))
        except Exception:
            st.session_state.historico.pop()
            st.error("Não foi possível obter a resposta agora. Aguarde alguns instantes e tente de novo.")
            return
    st.session_state.historico.append({"role": "model", "text": resposta})


# ---------- cabeçalho ----------
st.caption("Programa Smart Factory · Projetos de PD&I · TRL 6 a 8")
st.title("Assistente de Gestão Híbrida")
st.write(
    "Apoio à decisão para gestores de projetos de PD&I em programas de fomento. As recomendações seguem o "
    "modelo híbrido, as diretrizes D1 a D7 e as evidências de três projetos analisados na dissertação de "
    "mestrado (UFABC, 2026)."
)
st.info(
    "Versão experimental. As evidências vêm de três casos de uma única ICT e indicam associações, não "
    "garantias de resultado. A decisão final é sempre do gestor. Não informe nomes de pessoas ou empresas."
)

# ---------- ficha do projeto (barra lateral) ----------
with st.sidebar:
    st.header("Ficha do projeto")
    st.write("Preencha com a situação atual ou carregue um exemplo.")
    c1, c2, c3 = st.columns(3)
    for col, nome in zip((c1, c2, c3), EXEMPLOS):
        col.button(nome.replace("Cenário ", "Ex. "), on_click=carregar_exemplo, args=(nome,), use_container_width=True)

    with st.form("ficha_form"):
        a, b = st.columns(2)
        trl = a.number_input("TRL atual", 1, 9, key="f_trl")
        meta = b.number_input("Meta de TRL", 1, 9, key="f_meta")
        a, b = st.columns(2)
        prazo = a.number_input("Prazo total (meses)", 1, 60, key="f_prazo")
        restante = b.number_input("Prazo restante (meses)", 0, 60, key="f_restante")
        abordagem = st.selectbox("Abordagem atual", OPCOES["abordagem"], key="f_abordagem")
        escopo = st.selectbox("Situação do escopo", OPCOES["escopo"], key="f_escopo")
        validacao = st.selectbox("Validações com empresas", OPCOES["validacao"], key="f_validacao")
        aprovacao = st.text_input("Fluxo de aprovação (instâncias e tempo típico)", key="f_aprovacao")
        remanejamento = st.selectbox("Remanejamento de orçamento no fomento", OPCOES["remanejamento"], key="f_remanejamento")
        a, b = st.columns(2)
        parceiras = a.number_input("Empresas parceiras", 0, 200, key="f_parceiras")
        validadoras = b.number_input("Empresas validadoras", 0, 500, key="f_validadoras")
        dificuldade = st.text_area("Principal dificuldade hoje", key="f_dificuldade")
        gerar = st.form_submit_button("Gerar diagnóstico", type="primary", use_container_width=True)

    st.button("Nova consulta", on_click=nova_consulta, use_container_width=True)

# ---------- conversa ----------
pendente = None
if gerar:
    pendente = "\n".join([
        "Ficha do projeto:",
        f"- TRL atual: {trl}; meta de TRL: {meta}",
        f"- Prazo total: {prazo} meses; prazo restante: {restante} meses",
        f"- Abordagem atual: {abordagem}",
        f"- Situação do escopo: {escopo}",
        f"- Validações com empresas: {validacao}",
        f"- Fluxo de aprovação: {aprovacao or 'não informado'}",
        f"- Remanejamento de orçamento no fomento: {remanejamento}",
        f"- Empresas parceiras: {parceiras}; empresas validadoras: {validadoras}",
        f"- Principal dificuldade: {dificuldade or 'não informada'}",
        "",
        "Elabore o diagnóstico inicial deste projeto.",
    ])
    st.session_state.historico = []

if not st.session_state.historico and not pendente:
    st.markdown(
        "**Como funciona**\n\n"
        "1. Preencha a ficha do projeto na barra lateral ou carregue um exemplo.\n"
        "2. Clique em **Gerar diagnóstico**: o assistente situa o projeto no modelo, aponta riscos e recomenda "
        "ações com a diretriz e a evidência de cada uma.\n"
        "3. Continue a conversa com dúvidas pontuais ou cole o resumo de um ciclo de validação para síntese."
    )

for m in st.session_state.historico:
    with st.chat_message("user" if m["role"] == "user" else "assistant"):
        st.markdown(m["text"])

if pendente:
    enviar(pendente)

pergunta = st.chat_input(
    "Faça uma pergunta ou cole o resumo de um ciclo de validação",
    disabled=not st.session_state.historico and not pendente,
)
if pergunta:
    enviar(pergunta)

st.divider()
st.caption(
    "Produto aplicado da dissertação “Otimização da Gestão de Projetos de Inovação Industrial: um estudo de "
    "caso no Programa Smart Factory da CNI”, Programa de Pós-Graduação em Engenharia e Gestão da Inovação, "
    "Universidade Federal do ABC. Configurado por instruções e base de conhecimento; sem treinamento ou "
    "ajuste fino do modelo de linguagem."
)
