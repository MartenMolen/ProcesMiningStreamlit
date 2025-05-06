import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import networkx as nx
from io import BytesIO
from openai import OpenAI

# Configuratie
st.set_page_config(page_title="Productieproces Visualisatie", layout="wide")
st.title("🔄 Interactieve Process Mining App")
st.markdown("Analyseer productieprocessen op basis van statusovergangen.")

# Bestand uploaden
uploaded_file = st.file_uploader("Upload een Excel-bestand", type=[".xlsx"])

@st.cache_data
def load_data(file):
    return pd.read_excel(file)

if uploaded_file:
    df = load_data(uploaded_file)

    # Filters
    with st.sidebar:
        st.header("🔍 Filters")
        producties = df["DepartmentName"].dropna().unique().tolist()
        afdelingen = st.multiselect("Afdelingen", producties, default=producties)
        categorieen = df["Product category"].dropna().unique().tolist()
        categorie_filter = st.multiselect("Productcategorieën", categorieen, default=categorieen)

    filtered_df = df[(df["DepartmentName"].isin(afdelingen)) &
                     (df["Product category"].isin(categorie_filter))]

    # Procesedges maken
    filtered_df = filtered_df.dropna(subset=["Previous status Name", "Status measuring to name"])
    transitions = filtered_df.groupby(["Previous status Name", "Status measuring to name"]).size().reset_index(name="Aantal")

    # Visualisatie bouwen
    st.subheader("📈 Procesdiagram")
    G = nx.DiGraph()
    for _, row in transitions.iterrows():
        G.add_edge(row["Previous status Name"], row["Status measuring to name"], weight=row["Aantal"])

    pos = nx.spring_layout(G, k=0.8, seed=42)
    edge_trace = []
    for edge in G.edges(data=True):
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        trace = go.Scatter(x=[x0, x1, None], y=[y0, y1, None],
                           line=dict(width=0.5 + edge[2]['weight']*0.1, color='#888'),
                           hoverinfo='text', mode='lines',
                           text=f"{edge[0]} → {edge[1]}: {edge[2]['weight']}")
        edge_trace.append(trace)

    node_trace = go.Scatter(x=[], y=[], text=[], mode='markers+text',
                            textposition="bottom center",
                            marker=dict(size=10, color='#00aaff'))

    for node in G.nodes():
        x, y = pos[node]
        node_trace['x'] += (x,)
        node_trace['y'] += (y,)
        node_trace['text'] += (node,)

    fig = go.Figure(data=edge_trace + [node_trace],
                    layout=go.Layout(
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20, l=5, r=5, t=40),
                        xaxis=dict(showgrid=False, zeroline=False),
                        yaxis=dict(showgrid=False, zeroline=False)))

    st.plotly_chart(fig, use_container_width=True)

    # Prompt interface
    st.subheader("💬 Stel een vraag over je data")
    vraag = st.text_input("Typ hier je vraag (bijv. 'Welke status wordt het vaakst overgeslagen?')")

    if vraag:
        try:
            import openai
            openai.api_key = st.secrets["OPENAI_API_KEY"] if "OPENAI_API_KEY" in st.secrets else "sk-...beperkt"
            df_sample = filtered_df.head(500).to_csv(index=False)
            prompt = f"""
Jij bent een Nederlandstalige data-analist. Je bekijkt data van een productieproces. De gebruiker heeft deze data geüpload:
{df_sample}

Analyseer de volgende vraag: {vraag}
Geef een kort en duidelijk antwoord in het Nederlands.
"""
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            antwoord = completion.choices[0].message['content']
            st.success(antwoord)
        except Exception as e:
            st.error(f"Fout bij analyseren van vraag: {e}")
else:
    st.info("📁 Upload een Excel-bestand om te beginnen.")
