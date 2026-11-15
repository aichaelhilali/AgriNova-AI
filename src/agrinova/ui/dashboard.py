"""Presentation-only dashboard components and navigation callbacks."""

from html import escape
from copy import deepcopy

import streamlit as st

PAGES = ("Vue d’ensemble", "Climat", "Exploitation", "Rotations", "Comparaison", "Données et sources", "Paramètres", "Export")
TAB_LABELS = ("Voir le climat", "Préparer mes rotations", "Comparer les choix")
TAB_PAGES = dict(zip(TAB_LABELS, ("Climat", "Rotations", "Comparaison")))


def _preserve_editors():
    """Rebase submitted tables before navigation reruns, without replaying deltas."""
    state = st.session_state
    if state.get("demo_mode", False):
        revision = state.get("demo_revision", 0)
        prefix = f"demo_{revision}_"
        snapshot = {key: frame.copy(deep=True) for key, frame in state.get("dashboard_demo_snapshot", {}).items()
                    if key.startswith(prefix)}
        state.dashboard_demo_seed = deepcopy(snapshot)
    else:
        snapshot = state.get("manual_rotation_snapshot", {})
        state.manual_rotation_seed = deepcopy(snapshot)
    for key in snapshot:
        state.pop(key, None)


def navigate_from_sidebar():
    _preserve_editors()
    selected = st.session_state.dashboard_page
    if selected == "Exploitation":
        st.session_state.workspace_tabs = TAB_LABELS[1]
    for tab, page in TAB_PAGES.items():
        if page == selected:
            st.session_state.workspace_tabs = tab


def navigate_from_tabs():
    _preserve_editors()
    st.session_state.dashboard_page = TAB_PAGES[st.session_state.workspace_tabs]


def go_to_export():
    _preserve_editors()
    st.session_state.dashboard_page = "Export"


def navigation_css(page):
    """Keep forms mounted across views; hide whole presentation containers only."""
    shown = {"Vue d’ensemble": "dashboard_overview", "Export": "dashboard_exports", "Données et sources": "dashboard_sources", "Paramètres": "dashboard_settings"}.get(page, "dashboard_workspace")
    containers = ("dashboard_overview", "dashboard_exports", "dashboard_workspace", "dashboard_sources", "dashboard_settings")
    css = "".join(f".stApp .st-key-{name} {{display: none;}}" for name in containers if name != shown)
    if page == "Exploitation":
        css += ".stApp .st-key-rotation_grid, .stApp .st-key-water_tools {display:none;}"
    return "<style>" + css + "</style>"


def section_label(number, title, detail):
    st.markdown(f'<div class="section-heading"><span class="section-index">{escape(number)}</span>'
        f'<div><span class="section-eyebrow">{escape(title)}</span><p>{escape(detail)}</p></div></div>', unsafe_allow_html=True)


def rotation_summary(result, number, comparable):
    """A compact view of existing comparison results, without new scoring."""
    source = "EXEMPLE FICTIF" if result.get("is_demo") else "DÉCLARATION UTILISATEUR"
    crops = result.get("declared_crops") if result.get("is_demo") else [s.get("crop") for s in result.get("declared_stages", [])]
    sequence = " → ".join(c for c in (crops or []) if isinstance(c, str) and c.strip()) or "Cultures à renseigner"
    water, coverage = result.get("water"), result.get("coverage", {})
    total = f"{water['etc_mm']:.2f} mm" if water is not None and comparable else "Non comparable sur l’horizon"
    label = "RÉFÉRENCE" if number == 0 else f"ALTERNATIVE {number}"
    st.markdown(f'<article class="comparison-summary"><div class="scenario-badge">{label}</div>'
        f'<h3>{escape(sequence)}</h3><div class="comparison-origin">{source}</div>'
        f'<p>{escape(result["status"])}</p><div class="comparison-total"><span>ETc · horizon commun</span><strong>{escape(total)}</strong></div>'
        f'<div class="comparison-coverage">Couverture ETc : {coverage.get("etc_days", 0)}/{coverage.get("expected_days", 0)} jours</div>'
        '<p class="comparison-caution">Faisabilité agronomique non validée. ETc ≠ irrigation.</p></article>', unsafe_allow_html=True)


def _overview_main(climate, eto_result, comparison, mean_temperature=None, rainfall=None, coverage=None):
    """Render existing metric results; never estimate missing values."""
    loaded = climate is not None
    p = climate.provenance if loaded else None
    status = "Historique chargé" if loaded else "En attente de données"
    st.markdown('''<section class="overview-hero">
<div class="hero-copy"><div class="hero-eyebrow">AGRICULTURAL INTELLIGENCE / VUE D’ENSEMBLE</div>
<h2>Comprendre votre climat.<br>Éclairer vos rotations.</h2>
<p>Une lecture claire des données, des choix possibles et de ce qu’il reste à vérifier sur votre parcelle.</p>
<div class="hero-tags"><span>NASA POWER</span><span>FAO-56</span><span>Décisions expliquées</span></div></div>
<svg class="field-art" viewBox="0 0 360 280" fill="none" aria-hidden="true">
<ellipse cx="190" cy="252" rx="160" ry="16" fill="#E8E8E8"/>
<path d="M15 169L210 78L352 151L155 249Z" fill="#C1D7A6"/>
<path d="M15 169L155 249V260L15 180Z" fill="#545D49"/>
<path d="M155 249L352 151V162L155 260Z" fill="#186105"/>
<path d="M49 165L234 78M80 180L265 93M111 195L296 108M142 210L327 123M173 225L349 142" stroke="#57A735" stroke-width="12"/>
<path d="M104 122C104 86 108 69 115 48M108 86C84 85 77 65 83 51C105 52 119 69 108 86ZM115 64C113 40 131 25 148 29C148 47 131 65 115 64Z" fill="#186105"/>
<path d="M260 178C260 147 269 119 280 99M271 129C248 127 240 111 245 98C264 99 279 114 271 129ZM280 108C277 86 295 70 310 74C310 92 296 108 280 108Z" fill="#186105"/>
</svg><span class="illustration-label">ILLUSTRATION · PAS UNE CARTE PARCELLAIRE</span></section>''', unsafe_allow_html=True)
    eto_status = "Non calculée" if eto_result is None else f"{eto_result.provenance['available_days']}/{eto_result.provenance['expected_days']} jours"
    cards = [("01", "Température moyenne", mean_temperature or "—", "T2M · jours disponibles"),
        ("02", "Précipitations", rainfall or "—", "Cumul complet uniquement · mm"),
        ("03", "Couverture des données", coverage or "—", "Température / pluie · jours"),
        ("04", "Disponibilité ET₀", eto_status, "FAO-56 · calcul à lancer dans Rotations")]
    st.markdown('<div class="overview-kpis">' + "".join(
        f'<article class="overview-kpi"><div class="kpi-top"><span>{escape(label)}</span><span class="kpi-icon">{number}</span></div>'
        f'<strong>{escape(value)}</strong><p>{escape(note)}</p></article>' for number, label, value, note in cards) + '</div>', unsafe_allow_html=True)
    left, right = st.columns([1.65, 1], gap="large")
    with left, st.container(border=True, key="overview_context"):
        section_label("01", "Votre périmètre d’analyse", "Le contexte reste visible. Les limites aussi.")
        if loaded:
            point = p["requested_coordinates"]
            location = f"{point['latitude']:.4f}° · {point['longitude']:.4f}°"
            period = f"{p['start']} → {p['end']}"
        else:
            location, period = "Point à charger dans Paramètres", "Aucune période chargée"
        st.markdown(f'<dl class="context-list"><div><dt>Localisation du point</dt><dd>{escape(location)}</dd></div>'
            f'<div><dt>Période analysée</dt><dd>{escape(period)}</dd></div>'
            f'<div><dt>Statut des données</dt><dd><span class="data-status">{status}</span></dd></div></dl>', unsafe_allow_html=True)
        st.caption("Historique quotidien UTC · estimations à l’échelle d’une maille, sans mesure ni validation locale de la parcelle.")
    with right, st.container(border=True, key="overview_workflow"):
        section_label("02", "Votre espace de travail", "Un parcours simple, des résultats traçables.")
        saved = comparison is not None
        workflow = [("Climat", "Données chargées" if loaded else "Choisissez le lieu et la période"),
            ("Rotations", "Saisies enregistrées" if saved else "Renseignez votre référence et deux alternatives"),
            ("Comparaison", "Résultat disponible" if saved else "Preuves, risques et informations à compléter"),
            ("Export", "CSV et JSON selon les données disponibles")]
        st.markdown('<div class="workflow-list">' + "".join(f'<div><span class="workflow-dot"></span><div><strong>{escape(label)}</strong><p>{escape(note)}</p></div></div>' for label, note in workflow) + '</div>', unsafe_allow_html=True)
    st.markdown('<div class="science-strip"><strong>La donnée éclaire le choix. Elle ne le décide pas.</strong><span>Pas de score arbitraire · pas de classement automatique · ETc ≠ besoin d’irrigation</span></div>', unsafe_allow_html=True)


def overview(climate, eto_result, comparison, mean_temperature=None, rainfall=None, coverage=None):
    main, insights = st.columns([2.4, 1], gap="large")
    with main:
        _overview_main(climate, eto_result, comparison, mean_temperature, rainfall, coverage)
    with insights:
        with st.container(border=True, key="overview_quality"):
            section_label("01", "Qualité des données", "Couverture quotidienne NASA POWER")
            if climate is not None:
                for variable, label in (("T2M", "Température"), ("PRECTOTCORR", "Précipitations")):
                    count, expected = int(climate.daily[variable].count()), len(climate.daily)
                    fraction = count / expected if expected else 0
                    st.markdown(f'<div class="coverage-heading"><span>{label}</span><strong>{count}/{expected} jours</strong></div>'
                        f'<div class="coverage-track" role="meter" aria-label="{label} : jours valides" aria-valuenow="{count}" aria-valuemin="0" aria-valuemax="{expected}"><span style="width:{fraction * 100:.3f}%"></span></div>', unsafe_allow_html=True)
            else:
                st.write("Aucune série chargée. Aucun indicateur n’est estimé.")
            st.caption("La couverture n’est pas un score d’aptitude. Les lacunes restent explicites.")
        with st.container(border=True, key="overview_evidence"):
            st.markdown('<div class="evidence-badge">AGRINOVA · PREUVES & ÉCLAIRAGES</div>', unsafe_allow_html=True)
            st.subheader("Ce que les données montrent")
            st.write("Les indicateurs décrivent la période historique du point chargé." if climate is not None else "Chargez les données pour examiner le climat de votre zone.")
            st.markdown("**Ce que le calcul permet**")
            if eto_result is None:
                st.write("ET₀ non calculée. Le calcul documenté est disponible dans Rotations après chargement NASA.")
            else:
                st.write(f"ET₀ : {eto_result.provenance['available_days']}/{eto_result.provenance['expected_days']} jours calculables.")
            if comparison is not None:
                comparable = comparison.get("comparability", {}).get("quantitative_comparison_allowed", False)
                st.write("Les totaux ETc partagent les conditions de comparaison vérifiées." if comparable else "Les totaux ETc ne sont pas comparables comme rotations complètes.")
            st.markdown("**Ce qui reste incertain**")
            st.write("Conditions réelles de la parcelle, applicabilité locale des Kc et faisabilité agronomique.")
            st.caption("À examiner avec un conseiller local. ETc ne représente pas un besoin d’irrigation.")
        with st.container(border=True, key="overview_scope"):
            section_label("02", "Méthode & limites", "Un contexte, pas un diagnostic de terrain.")
            st.write("Estimations quotidiennes UTC à l’échelle d’une maille. Aucun rendement, revenu ou gain d’irrigation prédit.")
