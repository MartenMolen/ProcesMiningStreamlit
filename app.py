import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import openai

st.set_page_config(page_title="Procesvisualisatie", layout="wide")
st.title("📊 Procesvisualisatie op basis van productiegegevens")

# Uploadbestand
uploaded_file = st.file_uploader("Upload een Excel-bestand", type=[".xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # Verwijder rijen met ontbrekende statussen
    df = df.dropna(subset=["Previous Status Name", "Status Measuring To Name"])

    # Filters
    with st.sidebar:
        st.header("🔍 Filters")
        product_filter = st.multiselect("Product", options=sorted(df["Product Name"].dropna().unique()))
        category_filter = st.multiselect("Categorie", options=sorted(df["Product Category"].dropna().unique()))
        department_filter = st.multiselect("Afdeling", options=sorted(df["Department Name"].dropna().unique()))

    # Pas filters toe
    if product_filter:
        df = df[df["Product Name"].isin(product_filter)]
    if category_filter:
        df = df[df["Product Category"].isin(category_filter)]
    if department_filter:
        df = df[df["Department Name"].isin(department_filter)]

    # Groepeer transities
    transition_counts = (
        df.groupby(["Previous Status Name", "Status Measuring To Name"])
          .size()
          .reset_index(name="Aantal")
    )

    # Maak unieke lijst van alle statussen
    all_statuses = pd.unique(transition_counts[["Previous Status Name", "Status Measuring To Name"]].values.ravel())
    status_index = {status: i for i, status in enumerate(all_statuses)}

    # Vertaal naar indices voor Sankey
    sources = transition_counts["Previous Status Name"].map(status_index)
    targets = transition_counts["Status Measuring To Name"].map(status_index)
    values = transition_counts["Aantal"]

    # Sankey diagram bouwen
    fig = go.Figure(data=[
        go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=list(status_index.keys()),
                color="blue"
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values
            )
        )
    ])

    fig.update_layout(title_text="Productieproces (Sankey-diagram)", font_size=12)
    st.plotly_chart(fig, use_container_width=True)

    # Promptveld
    st.markdown("### 🤖 Stel een vraag over het proces")
    prompt = st.text_input("Vraag (bijv. 'Welke stappen zijn het vaakst doorlopen?')")

    if prompt:
        openai.api_key = st.secrets.get("OPENAI_API_KEY", "sk-...beperkt")
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Je bent een data-analist die procesdata uitlegt."},
                {"role": "user", "content": f"Analyseer het volgende proces: {transition_counts.to_string(index=False)}. Vraag: {prompt}"}
            ]
        )
        antwoord = response.choices[0].message.content
        st.markdown("#### 💡 Antwoord")
        st.write(antwoord)
else:
    st.info("📁 Upload een Excel-bestand om te beginnen.")
