import streamlit as st
from datetime import date
import pandas as pd
import plotly.express as px
import psycopg2
import uuid


# --- Connexion PostgreSQL ---
def get_connection():
    return psycopg2.connect(
        "postgresql://webappbdd_v2_user:gPOCiOFQnJ09tgLI6dJ46v1mZ6e9AVWv@dpg-d2t9143uibrs73eih1d0-a/webappbdd_v2",
        sslmode="require",
    )


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id UUID PRIMARY KEY,
            page TEXT NOT NULL,
            nom TEXT NOT NULL,
            avancement INT NOT NULL,
            pilote TEXT NOT NULL,
            date_debut DATE NOT NULL,
            date_echeance DATE NOT NULL
        );
    """
    )
    conn.commit()
    cur.close()
    conn.close()


def read_tasks_pg(pages):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, page, nom, avancement, pilote, date_debut, date_echeance FROM tasks;"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    tasks_dict = {page: [] for page in pages.keys()}
    for r in rows:
        tasks_dict[r[1]].append(
            {
                "id": str(r[0]),
                "page": r[1],
                "nom": r[2],
                "avancement": r[3],
                "pilote": r[4],
                "date_debut": r[5],
                "date_echeance": r[6],
                "subtasks": [],
            }
        )
    return tasks_dict


def write_tasks_pg(tasks_dict):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks;")
    for page, tasks in tasks_dict.items():
        for t in tasks:
            if "id" not in t:
                t["id"] = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO tasks (id, page, nom, avancement, pilote, date_debut, date_echeance)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
                (
                    t["id"],
                    page,
                    t["nom"],
                    t["avancement"],
                    t["pilote"],
                    t["date_debut"],
                    t["date_echeance"],
                ),
            )
    conn.commit()
    cur.close()
    conn.close()


# --- Pages ---
pages = {
    "Transformation AGILE": "La méthode agile permet d'aller plus vite et plus loin",
    "Organisation et processus": "Orgchart, méthodes de travail, standardisation",
    "Enableur technologiques": "Data, outillage et plateforme",
    "Budget & Mesure": "KPIs, OKRs, tableaux de bord",
    "Leadership et talents": "Compétences, staffing, coaching",
    "Culture et communication": "Valeurs, rituels, reconnaissance",
}

# --- Initialisation ---
st.set_page_config(page_title="Transformation Agile", layout="wide")
init_db()

if "pilotes" not in st.session_state:
    st.session_state.pilotes = ["DSI", "DATA", "PO", "DS"]
if "tasks" not in st.session_state:
    st.session_state.tasks = read_tasks_pg(pages)


# --- Helpers ---
def get_progress(page_name):
    tasks = st.session_state.tasks.get(page_name, [])
    return int(sum(t["avancement"] for t in tasks) / len(tasks)) if tasks else 0


def render_progress(avancement, key):
    fig = px.pie(values=[avancement, 100 - avancement], hole=0.6)
    fig.update_traces(marker_colors=["#4CAF50", "#E0E0E0"], textinfo="none")
    fig.update_layout(
        margin=dict(t=0, b=0, l=0, r=0), width=50, height=50, showlegend=False
    )
    st.plotly_chart(fig, use_container_width=False, key=key)


def bloc_progression(page_name, icon, title, caption):
    st.image(icon, width=60)
    st.markdown(f"### {title}")
    st.caption(caption)
    prog = get_progress(page_name)
    st.write(f"Progression : {prog}%")
    st.progress(prog)


# --- Sidebar ---
st.sidebar.title("Navigation")
selection = st.sidebar.radio("Aller à", list(pages.keys()))

# --- Page principale ---
st.title(selection)
st.write(pages[selection])

if selection != "Transformation AGILE":

    st.write(f"Progression : {get_progress(selection)}%")
    st.progress(get_progress(selection))

    with st.expander("Ajouter une tâche"):
        nom = st.text_input("Nom de la tâche")
        av = st.slider("Avancement (%)", 0, 100, 0)
        pilote_choix = st.selectbox(
            "Pilote associé", st.session_state.pilotes + ["Autre"]
        )
        pilote = (
            st.text_input("Saisir un pilote")
            if pilote_choix == "Autre"
            else pilote_choix
        )
        dd = st.date_input("Date de début", value=date.today())
        de = st.date_input("Date d'échéance", value=date.today())
        if st.button("Ajouter la tâche") and nom:
            if pilote not in st.session_state.pilotes:
                st.session_state.pilotes.append(pilote)
            st.session_state.tasks[selection].insert(
                0,
                {
                    "nom": nom,
                    "avancement": av,
                    "pilote": pilote,
                    "date_debut": dd,
                    "date_echeance": de,
                    "subtasks": [],
                    "_new": True,
                },
            )
            write_tasks_pg(st.session_state.tasks)

    st.subheader("Liste des tâches")
    updated_tasks = []
    for idx, tache in enumerate(st.session_state.tasks[selection]):
        supprimer = False
        tache.setdefault("subtasks", [])
        tache.setdefault("pilote", st.session_state.pilotes[0])
        tache.setdefault("date_debut", date.today())
        tache.setdefault("date_echeance", date.today())

        # Pie + Nom dans expander
        with st.expander(f"{tache['nom']} ({tache['avancement']}%)"):
            col1, col2, col3, col4, col5, col6 = st.columns([3, 2, 1, 1, 1, 1])

            # Nom (bloqué après création)
            with col1:
                tache["nom"] = st.text_input(
                    "Tâche",
                    tache["nom"],
                    disabled=not tache.get("_new", False),
                    key=f"nom_{selection}_{idx}",
                )
                tache.pop("_new", None)

            # Avancement
            with col2:
                tache["avancement"] = st.slider(
                    "Avancement",
                    0,
                    100,
                    tache["avancement"],
                    key=f"av_{selection}_{idx}",
                )
                render_progress(tache["avancement"], key=f"pie_{selection}_{idx}")

            # Pilote
            with col3:
                current_pilote = tache["pilote"]
                choix = st.selectbox(
                    "Pilote",
                    options=st.session_state.pilotes + ["Autre"],
                    index=(
                        st.session_state.pilotes.index(current_pilote)
                        if current_pilote in st.session_state.pilotes
                        else 0
                    ),
                    key=f"pilote_select_{selection}_{idx}",
                )
                tache["pilote"] = (
                    st.text_input(
                        f"Nouveau pilote {idx+1}",
                        value=current_pilote,
                        key=f"pilote_input_{selection}_{idx}",
                    )
                    if choix == "Autre"
                    else choix
                )
                if tache["pilote"] not in st.session_state.pilotes:
                    st.session_state.pilotes.append(tache["pilote"])

            # Dates
            with col4:
                tache["date_debut"] = st.date_input(
                    "Date de début",
                    tache["date_debut"],
                    key=f"date_debut_{selection}_{idx}",
                )
            with col5:
                tache["date_echeance"] = st.date_input(
                    "Date d'échéance",
                    tache["date_echeance"],
                    key=f"date_echeance_{selection}_{idx}",
                )

            # Supprimer
            with col6:
                if st.button("Supprimer", key=f"del_{selection}_{idx}"):
                    supprimer = True

        if not supprimer:
            updated_tasks.append(tache)

    st.session_state.tasks[selection] = updated_tasks
    write_tasks_pg(st.session_state.tasks)

# --- Page Transformation AGILE ---
else:
    st.markdown("<h3 style='text-align: center;'>🏛️ VISION</h3>", unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align: center;'><b>Purpose, strategy and priorities</b><br>Vision et objectifs prioritaires</p>",
        unsafe_allow_html=True,
    )
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        bloc_progression(
            "Organisation et processus",
            "icons/org.png",
            "Organisation et processus",
            "Orgchart, méthodes de travail, standardisation",
        )
    with col2:
        bloc_progression(
            "Enableur technologiques",
            "icons/tech.png",
            "Enableur technologiques",
            "Data, outillage et plateforme",
        )
    with col3:
        bloc_progression(
            "Budget & Mesure",
            "icons/budget.png",
            "Budget & Mesure",
            "KPIs, OKRs, tableaux de bord",
        )
    col4, col5 = st.columns(2)
    with col4:
        bloc_progression(
            "Leadership et talents",
            "icons/leader.png",
            "Leadership et talents",
            "Compétences, staffing, coaching",
        )
    with col5:
        bloc_progression(
            "Culture et communication",
            "icons/culture.png",
            "Culture et communication",
            "Valeurs, rituels, reconnaissance",
        )
    st.divider()
    st.markdown("### 🚀 EXECUTION DE LA TRANSFORMATION")
    all_tasks = [
        t["avancement"]
        for p, tasks in st.session_state.tasks.items()
        if p != "Transformation AGILE"
        for t in tasks
    ]
    avg_progress = int(sum(all_tasks) / (len(pages) - 1)) if all_tasks else 0
    st.subheader(f"Avancement global : {avg_progress}%")
    st.progress(avg_progress)
