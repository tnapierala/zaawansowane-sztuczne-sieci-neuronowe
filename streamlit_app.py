import streamlit as st
from openai import APIError, OpenAI, RateLimitError
import os
import PyPDF2

st.set_page_config(layout="wide", page_title="OpenRouter chatbot app")
st.title("OpenRouter chatbot app")

# Najpierw próbujemy odczytać sekrety Streamlit, potem zmienne środowiskowe.
api_key = st.secrets.get("API_KEY", os.getenv("API_KEY", ""))
base_url = st.secrets.get("BASE_URL", os.getenv("BASE_URL", ""))

available_models = [
    "gemini-3.1-pro-preview",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
]
selected_model = st.sidebar.selectbox(
    "Model",
    options=available_models,
    index=0,
)

# PDF Upload Section
st.sidebar.markdown("---")
st.sidebar.subheader("📄 Wczytaj PDF")
uploaded_pdf = st.sidebar.file_uploader("Wybierz plik PDF", type="pdf")

pdf_text = None
if uploaded_pdf is not None:
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_pdf)
        pdf_text = ""
        for page in pdf_reader.pages:
            pdf_text += page.extract_text()
        
        st.sidebar.success(f"✓ Wczytano PDF ({len(pdf_reader.pages)} stron)")
        
        if st.sidebar.button("➕ Dodaj do konwersacji", key="add_pdf_button"):
            if "messages" not in st.session_state:
                st.session_state["messages"] = []
            
            pdf_message = f"Wczytałem dokument PDF. Treść dokumentu:\n\n{pdf_text}"
            st.session_state.messages.append({"role": "user", "content": pdf_message})
            st.rerun()
    except Exception as e:
        st.sidebar.error(f"Błąd przy odczytywaniu PDF: {e}")

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?."}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input():
    if not api_key:
        st.info("Invalid API key.")
        st.stop()
    client = OpenAI(api_key=api_key, base_url=base_url)
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    models_to_try = [selected_model]
    if selected_model == "gemini-3.1-pro-preview":
        models_to_try.append("gemini-3-flash-preview")
        models_to_try.append("gemini-2.5-flash")

    response = None
    used_model = None
    last_rate_limit_error = None

    for model_name in models_to_try:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=st.session_state.messages,
            )
            used_model = model_name
            break
        except RateLimitError as exc:
            last_rate_limit_error = exc
            continue
        except APIError as exc:
            st.error(f"API error: {exc}")
            st.stop()

    if response is None:
        st.error(
            "Limit zapytań został przekroczony dla wybranego modelu. "
            "Odczekaj chwilę, zwiększ plan lub zmień model."
        )
        if last_rate_limit_error:
            with st.expander("Szczegóły błędu"):
                st.text(str(last_rate_limit_error))
        st.stop()

    if used_model and used_model != selected_model:
        st.info(f"Automatycznie użyto modelu zapasowego: {used_model}")

    msg = response.choices[0].message.content
    st.session_state.messages.append({"role": "assistant", "content": msg})
    st.chat_message("assistant").write(msg)