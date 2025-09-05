import streamlit as st
from datetime import date
import pandas as pd
import matplotlib.pyplot as plt
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

CSV_PATH = "tasks.csv"

# --- Session State Initialization ---
if "porteurs" not in st.session_state:
    st.session_state.porteurs = ["DSI", "DATA", "PO", "DS"]
if "tasks" not in st.session_state:
    try:
        df = pd.read_csv(CSV_PATH)
        st.session_state.tasks = {
            p: df[df["page"] == p].to_dict(orient="records") for p in pages.keys()
        }
        for page_tasks in st.session_state.tasks.values():
            for t in page_tasks:
                t.setdefault("subtasks", [])
                t["date_debut"] = pd.to_datetime(t["date_debut"]).date()
                t["date_echeance"] = pd.to_datetime(t["date_echeance"]).date()
    except FileNotFoundError:
        st.session_state.tasks = {p: [] for p in pages.keys()}


# --- Helper Functions ---
def write_tasks():
    all_tasks = []
    for page, tasks in st.session_state.tasks.items():
        for t in tasks:
            all_tasks.append(
                {
                    "page": page,
                    "nom": t["nom"],
                    "avancement": t["avancement"],
                    "porteur": t["porteur"],
                    "date_debut": t["date_debut"],
                    "date_echeance": t["date_echeance"],
                }
            )
    pd.DataFrame(all_tasks).to_csv(CSV_PATH, index=False)


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


def render_progress(avancement):
    fig = px.pie(values=[avancement, 100 - avancement], hole=0.6)
    fig.update_traces(marker_colors=["#4CAF50", "#E0E0E0"], textinfo="none")
    fig.update_layout(
        margin=dict(t=0, b=0, l=0, r=0), width=50, height=50, showlegend=False
    )
    st.plotly_chart(fig)


def task_avancement(tache):
    return (
        int(
            sum(sub["avancement"] for sub in tache["subtasks"]) / len(tache["subtasks"])
        )
        if tache["subtasks"]
        else tache.get("avancement", 0)
    )


def render_task(tache, selection, idx):
    supprimer = False
    tache.setdefault("subtasks", [])
    tache.setdefault("porteur", st.session_state.porteurs[0])
    tache.setdefault("date_debut", date.today())
    tache.setdefault("date_echeance", date.today())

    with st.expander(tache["nom"]):
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
                tache["avancement"] = task_avancement(tache)
                if not tache["subtasks"]:
                    tache["avancement"] = st.number_input(
                        "",
                        min_value=0,
                        max_value=100,
                        value=tache.get("avancement", 0),
                        step=1,
                        key=f"av_{selection}_{idx}",
                    )
            with col_chart:
                render_progress(tache["avancement"])

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

    col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 1])
    supprimer_sub = False

    with col1:
        sub["nom"] = st.text_input(
            "Sous-tâche", sub["nom"], key=f"sub_nom_{selection}_{idx}_{sub_idx}"
        )
    with col2:
        col_input, col_chart = st.columns([2, 1])
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
            render_progress(sub["avancement"])
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
    avg_progress = (
        int(
            sum(t.get("avancement", 0) for t in st.session_state.tasks[selection])
            / len(st.session_state.tasks[selection])
        )
        if st.session_state.tasks[selection]
        else 0
    )
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
