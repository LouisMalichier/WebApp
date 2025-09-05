import streamlit as st
from datetime import date
import psycopg2
import uuid
import json
import plotly.express as px


# --- Connexion PostgreSQL ---
def get_connection():
    return psycopg2.connect(
        "postgresql://webappbdd_v2_user:gPOCiOFQnJ09tgLI6dJ46v1mZ6e9AVWv@dpg-d2t9143uibrs73eih1d0-a/webappbdd_v2",
        sslmode="require",
    )


# --- Création de la table ---
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
            date_echeance DATE NOT NULL,
            subtasks JSONB DEFAULT '[]'
        );
    """
    )
    conn.commit()
    cur.close()
    conn.close()


init_db()

# --- Pages ---
pages = {
    "Transformation AGILE": "La méthode agile permet d'aller plus vite et plus loin",
    "Organisation et processus": "Orgchart, méthodes de travail, standardisation",
    "Enableur technologiques": "Data, outillage et plateforme",
    "Budget & Mesure": "KPIs, OKRs, tableaux de bord",
    "Leadership et talents": "Compétences, staffing, coaching",
    "Culture et communication": "Valeurs, rituels, reconnaissance",
}


# --- Lire les tâches depuis PostgreSQL ---
def read_tasks_pg():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, page, nom, avancement, pilote, date_debut, date_echeance, subtasks FROM tasks;"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    tasks_dict = {page: [] for page in pages.keys()}
    for r in rows:
        subtasks = json.loads(r[7]) if r[7] else []
        # Conversion des dates
        for s in subtasks:
            s["date_debut"] = s.get("date_debut", date.today())
            s["date_echeance"] = s.get("date_echeance", date.today())
        tasks_dict[r[1]].append(
            {
                "id": str(r[0]),
                "page": r[1],
                "nom": r[2],
                "avancement": r[3],
                "pilote": r[4],
                "date_debut": r[5],
                "date_echeance": r[6],
                "subtasks": subtasks,
            }
        )
    return tasks_dict


# --- Écrire les tâches dans PostgreSQL ---
def write_tasks_pg(tasks_dict):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks;")  # On réécrit tout
    for page, tasks in tasks_dict.items():
        for t in tasks:
            if "id" not in t:
                t["id"] = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO tasks (id, page, nom, avancement, pilote, date_debut, date_echeance, subtasks)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    t["id"],
                    page,
                    t["nom"],
                    t.get("avancement", 0),
                    t["pilote"],
                    t["date_debut"],
                    t["date_echeance"],
                    json.dumps(t.get("subtasks", [])),
                ),
            )
    conn.commit()
    cur.close()
    conn.close()


# --- Session State ---
if "pilotes" not in st.session_state:
    st.session_state.pilotes = ["DSI", "DATA", "PO", "DS"]
if "tasks" not in st.session_state:
    st.session_state.tasks = read_tasks_pg()


# --- Fonctions Helper ---
def task_avancement(tache):
    if tache.get("subtasks"):
        return int(
            sum(s["avancement"] for s in tache["subtasks"]) / len(tache["subtasks"])
        )
    return tache.get("avancement", 0)


def get_progress(page_name):
    tasks = st.session_state.tasks.get(page_name, [])
    if not tasks:
        return 0
    total = sum(task_avancement(t) for t in tasks)
    return int(total / len(tasks))


def bloc_progression(page_name, icon, title, caption):
    st.image(icon, width=60)
    st.markdown(f"### {title}")
    st.caption(caption)
    prog = get_progress(page_name)
    st.write(f"Progression : {prog}%")
    st.progress(prog)


def render_progress(avancement, key):
    fig = px.pie(values=[avancement, 100 - avancement], hole=0.6)
    fig.update_traces(marker_colors=["#4CAF50", "#E0E0E0"], textinfo="none")
    fig.update_layout(
        margin=dict(t=0, b=0, l=0, r=0), width=50, height=50, showlegend=False
    )
    st.plotly_chart(fig, key=key)


# --- Gestion Tâches et Sous-tâches ---
def render_task(tache, selection, idx):
    supprimer = False
    tache.setdefault("subtasks", [])
    tache.setdefault("pilote", st.session_state.pilotes[0])
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
        # Pilote
        with col3:
            current = tache["pilote"]
            choix = st.selectbox(
                "Pilote",
                options=st.session_state.pilotes + ["Autre"],
                index=(
                    st.session_state.pilotes.index(current)
                    if current in st.session_state.pilotes
                    else 0
                ),
                key=f"pilote_select_{selection}_{idx}",
            )
            tache["pilote"] = (
                st.text_input(
                    f"Nouveau pilote {idx}",
                    value=current,
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

        # Sous-tâches
        st.markdown("#### Sous-tâches")
        for sub_idx, sub in enumerate(tache["subtasks"]):
            render_subtask(tache, sub, selection, idx, sub_idx)

        # Ajouter sous-tâche
        with st.expander("Ajouter une sous-tâche"):
            add_subtask(tache, selection, idx)
    return not supprimer


def render_subtask(tache, sub, selection, idx, sub_idx):
    sub.setdefault("pilote", st.session_state.pilotes[0])
    sub.setdefault("date_debut", date.today())
    sub.setdefault("date_echeance", date.today())
    col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 1])
    with col1:
        sub["nom"] = st.text_input(
            "Sous-tâche", sub["nom"], key=f"sub_nom_{selection}_{idx}_{sub_idx}"
        )
    with col2:
        col_input, col_chart = st.columns([2, 1])
        with col_input:
            sub["avancement"] = st.number_input(
                "",
                0,
                100,
                sub.get("avancement", 0),
                step=1,
                key=f"sub_av_{selection}_{idx}_{sub_idx}",
            )
        with col_chart:
            render_progress(
                sub["avancement"], key=f"progress_subtask_{selection}_{idx}_{sub_idx}"
            )
    with col3:
        choix = st.selectbox(
            "Pilote",
            options=st.session_state.pilotes + ["Autre"],
            index=(
                st.session_state.pilotes.index(sub["pilote"])
                if sub["pilote"] in st.session_state.pilotes
                else 0
            ),
            key=f"sub_pilote_select_{selection}_{idx}_{sub_idx}",
        )
        sub["pilote"] = (
            st.text_input(
                f"Nouveau pilote {idx}-{sub_idx}",
                value=sub["pilote"],
                key=f"sub_pilote_input_{selection}_{idx}_{sub_idx}",
            )
            if choix == "Autre"
            else choix
        )
        if sub["pilote"] not in st.session_state.pilotes:
            st.session_state.pilotes.append(sub["pilote"])
    with col4:
        sub["date_debut"] = st.date_input(
            "Date début",
            sub["date_debut"],
            key=f"sub_date_debut_{selection}_{idx}_{sub_idx}",
        )
    with col5:
        sub["date_echeance"] = st.date_input(
            "Date échéance",
            sub["date_echeance"],
            key=f"sub_date_echeance_{selection}_{idx}_{sub_idx}",
        )
    if st.button("Supprimer sous-tâche", key=f"del_sub_{selection}_{idx}_{sub_idx}"):
        sub["_delete"] = True
    tache["subtasks"] = [s for s in tache["subtasks"] if "_delete" not in s]


def add_subtask(tache, selection, idx):
    name = st.text_input(f"Nom nouvelle sous-tâche {idx}", key=f"new_sub_nom_{idx}")
    av = st.number_input("Avancement", 0, 100, 0, step=1, key=f"new_sub_av_{idx}")
    choix = st.selectbox(
        "Pilote",
        options=st.session_state.pilotes + ["Autre"],
        key=f"new_sub_pilote_select_{idx}",
    )
    porteur = st.text_input(f"Saisir pilote {idx}") if choix == "Autre" else choix
    if porteur not in st.session_state.pilotes:
        st.session_state.pilotes.append(porteur)
    dd = st.date_input("Date début", value=date.today(), key=f"new_sub_dd_{idx}")
    de = st.date_input("Date échéance", value=date.today(), key=f"new_sub_de_{idx}")
    if st.button("Ajouter sous-tâche", key=f"add_sub_btn_{idx}") and name:
        tache["subtasks"].append(
            {
                "nom": name,
                "avancement": av,
                "pilote": porteur,
                "date_debut": dd,
                "date_echeance": de,
            }
        )


# --- Streamlit Interface ---
st.sidebar.title("Navigation")
selection = st.sidebar.radio("Aller à", list(pages.keys()))

st.title(selection)
st.write(pages[selection])

if selection != "Transformation AGILE":
    avg_progress = get_progress(selection)
    st.write(f"Progression : {avg_progress}%")
    st.progress(avg_progress)

    with st.expander("Ajouter une tâche"):
        nom_tache = st.text_input("Nom de la tâche")
        avancement = st.number_input("Avancement (%)", 0, 100, 0)
        pilote_choix = st.selectbox(
            "Pilote", options=st.session_state.pilotes + ["Autre"]
        )
        pilote_input = (
            st.text_input("Saisir un nouveau pilote")
            if pilote_choix == "Autre"
            else pilote_choix
        )
        dd = st.date_input("Date début", value=date.today())
        de = st.date_input("Date échéance", value=date.today())
        if st.button("Ajouter tâche") and nom_tache:
            if pilote_input not in st.session_state.pilotes:
                st.session_state.pilotes.append(pilote_input)
            st.session_state.tasks[selection].insert(
                0,
                {
                    "nom": nom_tache,
                    "avancement": avancement,
                    "pilote": pilote_input,
                    "date_debut": dd,
                    "date_echeance": de,
                    "subtasks": [],
                },
            )
            write_tasks_pg(st.session_state.tasks)

    updated_tasks = []
    for idx, tache in enumerate(st.session_state.tasks[selection]):
        if render_task(tache, selection, idx):
            updated_tasks.append(tache)
    st.session_state.tasks[selection] = updated_tasks
    write_tasks_pg(st.session_state.tasks)

else:
    st.markdown("<h3 style='text-align: center;'>🏛️ VISION</h3>", unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align: center;'><b>Purpose, strategy and priorities</b><br>Vision et objectifs prioritaires</p>",
        unsafe_allow_html=True,
    )
    st.divider()
    col1, col2, col3 = st.columns(3)
    bloc_progression(
        "Organisation et processus",
        "icons/org.png",
        "Organisation et processus",
        "Orgchart, méthodes de travail, standardisation",
    )
    bloc_progression(
        "Enableur technologiques",
        "icons/tech.png",
        "Enableur technologiques",
        "Data, outillage et plateforme",
    )
    bloc_progression(
        "Budget & Mesure",
        "icons/budget.png",
        "Budget & Mesure",
        "KPIs, OKRs, tableaux de bord",
    )
    col4, col5 = st.columns(2)
    bloc_progression(
        "Leadership et talents",
        "icons/leader.png",
        "Leadership et talents",
        "Compétences, staffing, coaching",
    )
    bloc_progression(
        "Culture et communication",
        "icons/culture.png",
        "Culture et communication",
        "Valeurs, rituels, reconnaissance",
    )
    st.divider()
    st.markdown("### 🚀 EXECUTION DE LA TRANSFORMATION")
    all_tasks = [
        task_avancement(t)
        for p, tasks in st.session_state.tasks.items()
        if p != "Transformation AGILE"
        for t in tasks
    ]
    avg_progress = int(sum(all_tasks) / len(all_tasks)) if all_tasks else 0
    st.subheader(f"Avancement global : {avg_progress}%")
    st.progress(avg_progress)
