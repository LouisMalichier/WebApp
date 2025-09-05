import streamlit as st
from datetime import date
import pandas as pd
import firebase_admin
from firebase_admin import credentials, db
import uuid
import psycopg2
import os


def get_connection():
    return psycopg2.connect(
        "postgresql://webappbdd_v2_user:gPOCiOFQnJ09tgLI6dJ46v1mZ6e9AVWv@dpg-d2t9143uibrs73eih1d0-a/webappbdd_v2",
        sslmode="require",
    )


# Création de la table si elle n’existe pas
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


st.set_page_config(page_title="Transformation Agile", layout="wide")

# --- Pages ---
pages = {
    "Transformation AGILE": "La méthode agile permet d'aller plus vite et plus loin",
    "Organisation et processus": "Orgchart, méthodes de travail, standardisation",
    "Enableur technologiques": "Data, outillage et plateforme",
    "Budget & Mesure": "KPIs, OKRs, tableaux de bord",
    "Leadership et talents": "Compétences, staffing, coaching",
    "Culture et communication": "Valeurs, rituels, reconnaissance",
}


# --- Fonctions pour PG ---
def read_tasks_pg(pages=pages):
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
            }
        )
    return tasks_dict


def write_tasks_pg(tasks_dict):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks;")  # simple : on réécrit tout
    for page, tasks in tasks_dict.items():
        for t in tasks:
            if "id" not in t:
                t["id"] = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO tasks (id, page, nom, avancement, pilote, date_debut, date_echeance)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
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


init_db()

# --- Session state ---
if "pilotes" not in st.session_state:
    st.session_state.pilotes = ["DSI", "DATA", "PO", "DS"]
if "tasks" not in st.session_state:
    st.session_state.tasks = read_tasks_pg()


# --- Fonctions ---
def get_progress(page_name):
    tasks = st.session_state.tasks.get(page_name, [])
    return int(sum(t["avancement"] for t in tasks) / len(tasks)) if tasks else 0


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

# --- Page sélectionnée ---
st.title(selection)
st.write(pages[selection])

# --- Pages de gestion de tâches ---
if selection != "Transformation AGILE":
    avg_progress = get_progress(selection)
    st.write(f"Progression : {avg_progress}%")
    st.progress(avg_progress)

    with st.expander("Ajouter une tâche"):
        nom_tache = st.text_input("Nom de la tâche")
        avancement = st.slider("Avancement (%)", 0, 100, 0)
        pilote_choix = st.selectbox(
            "Pilote associé", options=st.session_state.pilotes + ["Autre"]
        )
        pilote_input = (
            st.text_input("Saisir un nouveau pilote")
            if pilote_choix == "Autre"
            else pilote_choix
        )
        date_debut_tache = st.date_input("Date de début", value=date.today())
        date_echeance_tache = st.date_input(
            "Date d'échéance prévue", value=date.today()
        )

        if st.button("Ajouter la tâche"):
            if nom_tache:
                if pilote_input not in st.session_state.pilotes:
                    st.session_state.pilotes.append(pilote_input)
                st.session_state.tasks[selection].insert(
                    0,
                    {
                        "nom": nom_tache,
                        "avancement": avancement,
                        "pilote": pilote_input,
                        "date_debut": date_debut_tache,
                        "date_echeance": date_echeance_tache,
                    },
                )
                write_tasks_pg(st.session_state.tasks)
            else:
                st.warning("Veuillez entrer un nom de tâche.")

    st.subheader("Liste des tâches")
    updated_tasks = []
    for idx, tache in enumerate(st.session_state.tasks[selection]):
        col1, col2, col3, col4, col5, col6 = st.columns([3, 2, 1, 1, 1, 1])
        supprimer = False
        tache.setdefault("date_debut", date.today())
        tache.setdefault("date_echeance", date.today())
        tache.setdefault("pilote", st.session_state.pilotes[0])

        with col1:
            tache["nom"] = st.text_input(
                "Tâche", tache["nom"], key=f"nom_{selection}_{idx}"
            )
        with col2:
            tache["avancement"] = st.slider(
                "Avancement", 0, 100, tache["avancement"], key=f"av_{selection}_{idx}"
            )
        with col3:
            current_pilote = tache["pilote"]
            pilote_choix = st.selectbox(
                "Pilote",
                options=st.session_state.pilotes + ["Autre"],
                index=(
                    st.session_state.pilotes.index(current_pilote)
                    if current_pilote in st.session_state.pilotes
                    else 0
                ),
                key=f"pilote_select_{selection}_{idx}",
            )
            new_pilote = (
                st.text_input(
                    f"Nouveau pilote {idx+1}",
                    value=current_pilote,
                    key=f"pilote_input_{selection}_{idx}",
                )
                if pilote_choix == "Autre"
                else pilote_choix
            )
            tache["pilote"] = new_pilote
            if new_pilote not in st.session_state.pilotes:
                st.session_state.pilotes.append(new_pilote)
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
        with col6:
            st.write("")
            st.write("")
            if st.button("Supprimer", key=f"del_{selection}_{idx}"):
                supprimer = True
            if not supprimer:
                updated_tasks.append(tache)
    st.session_state.tasks[selection] = updated_tasks
    write_tasks_pg(st.session_state.tasks)  # Mise à jour Firebase


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
