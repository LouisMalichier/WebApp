import streamlit as st
from datetime import date
import pandas as pd
import json
import plotly.express as px

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

JSON_PATH = "tasks.json"

# --- Session State Initialization ---
if "porteurs" not in st.session_state:
    st.session_state.porteurs = ["DSI", "DATA", "PO", "DS"]

if "tasks" not in st.session_state:
    try:
        with open(JSON_PATH, "r") as f:
            st.session_state.tasks = json.load(f)
            # Convertir les dates de string à date
            for page, tasks in st.session_state.tasks.items():
                for t in tasks:
                    t["date_debut"] = pd.to_datetime(t["date_debut"]).date()
                    t["date_echeance"] = pd.to_datetime(t["date_echeance"]).date()
                    for s in t.get("subtasks", []):
                        s["date_debut"] = pd.to_datetime(s["date_debut"]).date()
                        s["date_echeance"] = pd.to_datetime(s["date_echeance"]).date()
    except FileNotFoundError:
        st.session_state.tasks = {p: [] for p in pages.keys()}


# --- Helper Functions ---
def write_tasks():
    # Convertir les dates en string avant d'écrire
    to_save = {}
    for page, tasks in st.session_state.tasks.items():
        to_save[page] = []
        for t in tasks:
            t_copy = t.copy()
            t_copy["date_debut"] = t_copy["date_debut"].isoformat()
            t_copy["date_echeance"] = t_copy["date_echeance"].isoformat()
            subtasks = []
            for s in t_copy.get("subtasks", []):
                s_copy = s.copy()
                s_copy["date_debut"] = s_copy["date_debut"].isoformat()
                s_copy["date_echeance"] = s_copy["date_echeance"].isoformat()
                subtasks.append(s_copy)
            t_copy["subtasks"] = subtasks
            to_save[page].append(t_copy)
    with open(JSON_PATH, "w") as f:
        json.dump(to_save, f, indent=2)


def get_progress(page_name):
    tasks = st.session_state.tasks.get(page_name, [])
    if not tasks:
        return 0
    total = 0
    for t in tasks:
        if t.get("subtasks"):
            total += int(
                sum(s["avancement"] for s in t["subtasks"]) / len(t["subtasks"])
            )
        else:
            total += t.get("avancement", 0)
    return int(total / len(tasks))


def bloc_progression(page_name, icon, title, caption):
    st.image(icon, width=60)
    st.markdown(f"### {title}")
    st.caption(caption)
    prog = get_progress(page_name)
    st.write(f"Progression : {prog}%")
    st.progress(prog)


def render_progress(avancement, key):
    # Choix de la couleur selon la valeur
    if avancement < 10:
        color = "red"
    elif avancement < 33:
        color = "yellow"
    elif avancement < 50:
        color = "orange"
    elif avancement < 80:
        color = "blue"
    elif avancement < 100:
        color = "green"
    else:
        color = "darkgreen"

    # HTML pour une boîte alignée verticalement au centre
    st.markdown(f"**Avancement**")
    st.markdown(
        f"<span style='color:{color}; font-weight:bold'>{avancement}%</span>",
        unsafe_allow_html=True,
    )


def task_avancement(tache):
    if tache.get("subtasks"):
        return int(
            sum(s["avancement"] for s in tache["subtasks"]) / len(tache["subtasks"])
        )
    else:
        return tache.get("avancement", 0)


# --- Tâches et Sous-tâches ---
def render_task(tache, selection, idx):
    supprimer = False
    tache.setdefault("subtasks", [])
    tache.setdefault("porteur", st.session_state.porteurs[0])
    tache.setdefault("date_debut", date.today())
    tache.setdefault("date_echeance", date.today())

    # Calcul des infos pour le titre
    avancement = task_avancement(tache)
    porteur = tache.get("porteur", "")
    if tache.get("subtasks"):
        # Date de début la plus ancienne
        min_date = min(s["date_debut"] for s in tache["subtasks"])
        # Date d'échéance la plus lointaine
        max_date = max(s["date_echeance"] for s in tache["subtasks"])
    else:
        min_date = tache["date_debut"]
        max_date = tache["date_echeance"]

    # Texte résumé dans l'expander
    expander_label = f"{tache['nom']} | Avancement: {avancement}% | Porteur: {porteur} | Début: {min_date} | Échéance: {max_date}"

    with st.expander(expander_label):
        col1, col2, col3, col4, col5, col6 = st.columns([3, 3, 1, 1, 1, 1])
        # Nom
        with col1:
            tache["nom"] = st.text_input(
                "Tâche", tache["nom"], key=f"nom_{selection}_{idx}"
            )
        # Avancement
        with col2:
            col_input, col_chart = st.columns([2, 1])
            with col_input:
                if not tache["subtasks"]:
                    tache["avancement"] = st.number_input(
                        "",
                        min_value=0,
                        max_value=100,
                        value=tache.get("avancement", 0),
                        step=1,
                        key=f"av_{selection}_{idx}",
                    )
                else:
                    tache["avancement"] = task_avancement(tache)
            with col_chart:
                render_progress(
                    tache["avancement"], key=f"progress_task_{selection}_{idx}"
                )
        # Porteur
        with col3:
            current_porteur = tache["porteur"]
            choix = st.selectbox(
                "Porteur",
                options=st.session_state.porteurs + ["Autre"],
                index=(
                    st.session_state.porteurs.index(current_porteur)
                    if current_porteur in st.session_state.porteurs
                    else 0
                ),
                key=f"porteur_select_{selection}_{idx}",
            )
            tache["porteur"] = (
                st.text_input(
                    f"Nouveau porteur {idx}",
                    value=current_porteur,
                    key=f"porteur_input_{selection}_{idx}",
                )
                if choix == "Autre"
                else choix
            )
            if tache["porteur"] not in st.session_state.porteurs:
                st.session_state.porteurs.append(tache["porteur"])
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
        # Sous-tâches
        st.markdown("#### Sous-tâches")
        for sub_idx, sub in enumerate(tache["subtasks"]):
            render_subtask(tache, sub, selection, idx, sub_idx)
        # Ajouter une sous-tâche
        with st.expander("Ajouter une sous-tâche"):
            add_subtask(tache, selection, idx)
    return not supprimer


def render_subtask(tache, sub, selection, idx, sub_idx):
    sub.setdefault("porteur", st.session_state.porteurs[0])
    sub.setdefault("date_debut", date.today())
    sub.setdefault("date_echeance", date.today())
    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
    with col1:
        sub["nom"] = st.text_input(
            "Sous-tâche", sub["nom"], key=f"sub_nom_{selection}_{idx}_{sub_idx}"
        )
    with col2:
        col_input, col_chart = st.columns([1, 2])
        with col_input:
            sub["avancement"] = st.number_input(
                "",
                min_value=0,
                max_value=100,
                value=sub.get("avancement", 0),
                step=1,
                key=f"sub_av_{selection}_{idx}_{sub_idx}",
            )
        with col_chart:
            render_progress(
                sub["avancement"], key=f"progress_subtask_{selection}_{idx}_{sub_idx}"
            )
    with col3:
        choix = st.selectbox(
            "Porteur",
            options=st.session_state.porteurs + ["Autre"],
            index=(
                st.session_state.porteurs.index(sub["porteur"])
                if sub["porteur"] in st.session_state.porteurs
                else 0
            ),
            key=f"sub_porteur_select_{selection}_{idx}_{sub_idx}",
        )
        sub["porteur"] = (
            st.text_input(
                f"Nouveau porteur sous-tâche {idx}-{sub_idx}",
                value=sub["porteur"],
                key=f"sub_porteur_input_{selection}_{idx}_{sub_idx}",
            )
            if choix == "Autre"
            else choix
        )
        if sub["porteur"] not in st.session_state.porteurs:
            st.session_state.porteurs.append(sub["porteur"])
    with col4:
        sub["date_debut"] = st.date_input(
            "Date de début",
            sub["date_debut"],
            key=f"sub_date_debut_{selection}_{idx}_{sub_idx}",
        )
    with col5:
        sub["date_echeance"] = st.date_input(
            "Date d'échéance",
            sub["date_echeance"],
            key=f"sub_date_echeance_{selection}_{idx}_{sub_idx}",
        )
    if st.button("Supprimer sous-tâche", key=f"del_sub_{selection}_{idx}_{sub_idx}"):
        sub["_delete"] = True
    tache["subtasks"] = [s for s in tache["subtasks"] if "_delete" not in s]


def add_subtask(tache, selection, idx):
    name = st.text_input(f"Nom nouvelle sous-tâche {idx}", key=f"new_sub_nom_{idx}")
    av = st.number_input(
        "Avancement",
        min_value=0,
        max_value=100,
        value=0,
        step=1,
        key=f"new_sub_av_{idx}",
    )
    choix = st.selectbox(
        "Porteur",
        options=st.session_state.porteurs + ["Autre"],
        key=f"new_sub_porteur_select_{idx}",
    )
    porteur = st.text_input(f"Saisir porteur {idx}") if choix == "Autre" else choix
    if porteur not in st.session_state.porteurs:
        st.session_state.porteurs.append(porteur)
    date_debut = st.date_input(
        "Date de début", value=date.today(), key=f"new_sub_date_debut_{idx}"
    )
    date_echeance = st.date_input(
        "Date d'échéance", value=date.today(), key=f"new_sub_date_echeance_{idx}"
    )
    if st.button("Ajouter sous-tâche", key=f"add_sub_btn_{idx}") and name:
        tache["subtasks"].append(
            {
                "nom": name,
                "avancement": av,
                "porteur": porteur,
                "date_debut": date_debut,
                "date_echeance": date_echeance,
            }
        )


# --- Sidebar ---
st.sidebar.title("Navigation")
selection = st.sidebar.radio("Aller à", list(pages.keys()))

# --- Page principale ---
st.title(selection)
st.write(pages[selection])

if selection != "Transformation AGILE":
    avg_progress = get_progress(selection)
    st.write(f"Progression : {avg_progress}%")
    st.progress(avg_progress)

    with st.expander("Ajouter une tâche"):
        nom = st.text_input("Nom de la tâche")
        av = st.number_input("Avancement (%)", 0, 100, 0)
        choix = st.selectbox("Porteur", options=st.session_state.porteurs + ["Autre"])
        porteur = st.text_input("Saisir porteur") if choix == "Autre" else choix
        if porteur not in st.session_state.porteurs:
            st.session_state.porteurs.append(porteur)
        dd = st.date_input("Date de début", value=date.today())
        de = st.date_input("Date d'échéance", value=date.today())
        if st.button("Ajouter la tâche") and nom:
            st.session_state.tasks[selection].insert(
                0,
                {
                    "nom": nom,
                    "avancement": av,
                    "porteur": porteur,
                    "date_debut": dd,
                    "date_echeance": de,
                    "subtasks": [],
                },
            )
            write_tasks()

    updated_tasks = []
    for idx, tache in enumerate(st.session_state.tasks[selection]):
        if render_task(tache, selection, idx):
            updated_tasks.append(tache)
    st.session_state.tasks[selection] = updated_tasks
    write_tasks()
else:
    st.markdown("<h3 style='text-align: center;'>🏛️ VISION</h3>", unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align: center;'><b>Purpose, strategy and priorities</b><br>Vision et objectifs prioritaires</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        bloc_progression(
            "Pilotage et budget",
            "icons/budget.png",
            "Budget & Mesure",
            "KPIs, OKRs, tableaux de bord",
        )
    with col2:
        bloc_progression(
            "Organisation et processus",
            "icons/org.png",
            "Organisation et processus",
            "Orgchart, méthodes de travail, standardisation",
        )

    col3, col4, col5 = st.columns(3)
    with col3:
        bloc_progression(
            "Enableurs technologiques",
            "icons/tech.png",
            "Enableur technologiques",
            "Data, outillage et plateforme",
        )
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
