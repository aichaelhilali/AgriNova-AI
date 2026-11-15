"""Run with: python -m streamlit run app.py"""

import io
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from agrinova.analysis.water import WaterInputError, validate_eto, json_safe
from agrinova.analysis.eto import calculate_power_eto, EtoError
from agrinova.analysis.crop_water import computed_eto_for_crops, FAO_CROP_REFERENCE
from agrinova.data.power import PowerError, fetch_daily
from agrinova.rotation.compare import CONSTRAINTS, STATUSES, evaluate_rotation, assess_comparability
from agrinova.rotation.demo import DEMO_NAMES, DEMO_NOTICE, activate_demo, deactivate_demo, scenario_frame, annotate_demo
from agrinova.rotation.agronomy import identify_crop
from agrinova.ui.theme import CSS, style_climate_chart
from agrinova.ui.dashboard import (PAGES, TAB_LABELS, navigation_css, navigate_from_sidebar,
                                   navigate_from_tabs, overview, section_label, go_to_export, rotation_summary)

st.set_page_config(page_title="AgriNova AI · Beni Mellal", page_icon="🌱", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
with st.sidebar:
    st.markdown('<div class="sidebar-brand"><span>AN</span></div>', unsafe_allow_html=True)
    page = st.radio("Navigation", PAGES, key="dashboard_page", on_change=navigate_from_sidebar,
        label_visibility="collapsed")
st.markdown(navigation_css(page), unsafe_allow_html=True)
st.markdown('''<header class="hero">
<div class="brand-lockup"><div class="brand-icon" aria-hidden="true">
<svg viewBox="0 0 32 32" fill="none"><path d="M25 5C13 3 5 9 7 18c8 4 18-1 18-13Z" fill="#57A735"/><path d="M7 27C9 17 15 12 23 7M9 20l-1-7m6 2 7 1" stroke="#186105" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
</div><div><h1>AgriNova AI</h1><p>Des données NASA pour des rotations agricoles plus résilientes.</p></div></div>
<div class="brand-meta"><span class="location-pill">Intelligence agricole</span><span>NASA POWER · FAO-56</span></div>
</header>''', unsafe_allow_html=True)
toolbar_slot = st.container(key="dashboard_toolbar")
overview_slot = st.container(key="dashboard_overview")
settings_slot = st.container(key="dashboard_settings")
data_slot = st.container(key="dashboard_sources")
export_slot = st.container(key="dashboard_exports")
with export_slot:
    st.header("Données & exports")
    st.caption("Vos fichiers, leurs sources et leurs limites. Seules les données disponibles sont proposées au téléchargement.")
with data_slot:
    st.header("Données & sources")
    st.caption("Des résultats lisibles jusqu’aux données d’origine : point, période, méthode et limites.")
with settings_slot:
    st.header("Lieu & période d’analyse")
    st.caption("Choisissez le point et les dates réellement représentés par les données NASA POWER.")


@st.cache_data(ttl=21600, max_entries=16, show_spinner=False)
def load_climate(latitude, longitude, start, end, validation_version="power_v3_eto_inputs"):
    return fetch_daily(latitude, longitude, start, end)


today = datetime.now(timezone.utc).date()
year = today.year - 1
default_start, default_end = date(year, 1, 1), date(year, 12, 31)

with settings_slot:
    st.subheader("Point NASA POWER")
    st.caption("Lieu de départ : un point approximatif de Beni Mellal. Vous pouvez le modifier ci-dessous.")
    period_kind = st.selectbox("Cadre de l’analyse", ["Période personnalisée", "Saison agricole"])
    if period_kind == "Saison agricole":
        st.caption("Définissez les dates de votre saison, y compris à cheval sur deux années. Aucun calendrier de plantation local n’est présumé.")
    with st.form("climate_query"):
        with st.expander("Modifier le lieu · coordonnées GPS"):
            lat = st.number_input("Latitude (°)", min_value=-90.0, max_value=90.0, value=32.34, format="%.4f")
            lon = st.number_input("Longitude (°)", min_value=-180.0, max_value=180.0, value=-6.36, format="%.4f")
        st.caption("Choisissez le début et la fin de la période à consulter.")
        period_start_column, period_end_column = st.columns(2)
        with period_start_column:
            climate_start = st.date_input("Début de l’historique", None if period_kind == "Saison agricole" else default_start, min_value=date(1981, 1, 1), max_value=today - timedelta(days=1))
        with period_end_column:
            climate_end = st.date_input("Fin de l’historique", None if period_kind == "Saison agricole" else default_end, min_value=date(1981, 1, 1), max_value=today - timedelta(days=1))
        requested = st.form_submit_button("Charger les données NASA", type="primary")
    with st.expander("À propos des données météo"):
        st.caption("Source : NASA POWER. Données quotidiennes en UTC, conservées en mémoire jusqu’à 6 h pour éviter des téléchargements répétés. La date du téléchargement est disponible avec les données.")
        st.markdown("[Documentation NASA POWER](https://power.larc.nasa.gov/docs/services/api/temporal/daily/)")

if requested:
    # A failed request must not leave stale charts for a different point/period.
    st.session_state.pop("climate", None)
    st.session_state.pop("comparison", None)
    st.session_state.pop("climate_error", None)
    st.session_state.pop("nasa_eto_result", None)
    try:
        if climate_start is None or climate_end is None:
            raise PowerError("Renseignez le début et la fin de votre période ou saison agricole.")
        with st.spinner("Interrogation de NASA POWER…"):
            st.session_state.climate = load_climate(lat, lon, climate_start, climate_end, validation_version="power_v3_eto_inputs")
            st.session_state.climate_period_kind = period_kind
    except PowerError as exc:
        st.session_state.climate_error = str(exc)

climate = st.session_state.get("climate")
with settings_slot:
    if st.session_state.get("climate_error"):
        st.error("Chargement NASA indisponible : " + st.session_state.climate_error)
    elif climate is not None:
        st.success("Historique chargé. Consultez Climat pour les graphiques et Données et sources pour la provenance.")
if not st.session_state.get("rotation_agronomy_schema_v4", False):
    # A data-editor schema change resets its widget state. Keep previously
    # submitted tables as the new seed before adding the metadata columns.
    snapshot = st.session_state.get("manual_rotation_snapshot", {})
    if snapshot:
        st.session_state.manual_rotation_seed = {key: frame.copy(deep=True) for key, frame in snapshot.items()}
    st.session_state.scientific_metadata_schema_v2 = True
    st.session_state.crop_stage_schema_v3 = True
    st.session_state.rotation_agronomy_schema_v4 = True
if st.session_state.get("demo_mode", False):
    st.warning("Mode démonstration : les cultures sont des exemples fictifs. La référence A n’est pas la rotation réelle d’un agriculteur. Les données météo NASA restent réelles.")
with st.container(key="dashboard_workspace"):
    climate_tab, farm_tab, compare_tab = st.tabs(TAB_LABELS, key="workspace_tabs", on_change=navigate_from_tabs)

with climate_tab:
    st.header("Le climat de votre zone")
    if st.session_state.get("climate_error"):
        st.error("Les données météo n’ont pas pu être chargées. Vérifiez les dates et la connexion, puis réessayez.")
        with st.expander("Voir le détail de l’erreur"):
            st.write(st.session_state.climate_error)
        st.caption("Aucune donnée de remplacement n’a été générée.")
    if climate is None:
        st.markdown('''<section class="empty-state"><div class="empty-symbol" aria-hidden="true">☀</div>
<h3>Commencez par le climat de votre zone</h3><p>Choisissez un lieu et une période dans Paramètres, puis cliquez sur « Charger les données NASA ». Vous pouvez aussi préparer vos rotations sans connexion.</p></section>''', unsafe_allow_html=True)
    else:
        df = climate.daily
        p = climate.provenance
        point = p["requested_coordinates"]
        st.write(f"**Point chargé : {point['latitude']:.4f}°, {point['longitude']:.4f}° · {p['start']} → {p['end']} · UTC**")
        st.markdown('<span class="location-pill">Source · NASA POWER</span>', unsafe_allow_html=True)
        st.caption(f"Cadre chargé : {st.session_state.get('climate_period_kind', 'Période personnalisée')} · Les indicateurs portent sur ces dates exactes, pas nécessairement sur une année civile.")
        missing = df.isna().sum()
        with st.container(key="climate_metrics"):
            a, b, c = st.columns(3, gap="medium")
        mean_temp = df.T2M.mean()
        a.metric("Température moyenne", "Indisponible" if pd.isna(mean_temp) else f"{mean_temp:.1f} °C")
        b.metric("Total de pluie sur la période", f"{df.PRECTOTCORR.sum():.1f} mm" if missing.PRECTOTCORR == 0 else "Indisponible : lacunes")
        c.metric("Jours renseignés · température / pluie", f"{df.T2M.count()}/{len(df)} · {df.PRECTOTCORR.count()}/{len(df)}")
        st.caption("Les deux comptes indiquent les jours renseignés pour la température, puis pour la pluie. Le total de pluie reste indisponible s’il manque des jours.")
        if missing.any():
            st.warning("Des jours sont manquants. Les courbes ne sont pas interpolées ; aucun cumul incomplet n’est présenté comme un total complet.")
        climate_charts, climate_context = st.columns([2.4, 1], gap="large")
        with climate_context, st.container(border=True):
            section_label("01", "Contexte environnemental", "Historique du point et de la période chargés.")
            st.write(f"**Localisation** · {point['latitude']:.4f}°, {point['longitude']:.4f}°")
            st.write(f"**Période** · {p['start']} → {p['end']}")
            st.write("**Résolution temporelle** · quotidienne UTC")
            st.caption("Les valeurs concernent une maille, pas une mesure sur votre parcelle. Consultez Données et sources pour la résolution spatiale et la provenance.")
            st.write("**À retenir**")
            st.caption("Le cumul de pluie n’est pas une disponibilité d’irrigation. Aucun seuil d’aptitude des cultures n’est présumé.")
        temp_fig = go.Figure()
        for variable, label, color in [("T2M_MIN", "Minimum", "#57A735"), ("T2M_MAX", "Maximum", "#ADAF4D"), ("T2M", "Moyenne", "#186105")]:
            temp_fig.add_trace(go.Scatter(x=df.index, y=df[variable], name=label, mode="lines", connectgaps=False, line={"color": color, "width": 2.4}))
        temp_fig.update_layout(yaxis_title="°C", xaxis_title="Date (UTC)")
        style_climate_chart(temp_fig, "Température quotidienne à 2 m")
        with climate_charts:
            st.plotly_chart(temp_fig, width='stretch', theme=None, config={"responsive": True, "displaylogo": False})
        rain_fig = go.Figure(go.Bar(x=df.index, y=df.PRECTOTCORR, name="Précipitation corrigée", marker_color="#57A735"))
        rain_fig.update_layout(yaxis_title="mm/jour", xaxis_title="Date (UTC)")
        style_climate_chart(rain_fig, "Pluie par jour<br>mm/jour")
        with climate_charts:
            st.plotly_chart(rain_fig, width='stretch', theme=None, config={"responsive": True, "displaylogo": False})
        st.warning("Ces données décrivent une zone, pas une mesure sur votre parcelle. Le cumul de précipitations ne représente pas l’eau disponible pour l’irrigation. Les graphiques montrent le passé, pas une prévision.")
        with data_slot, st.expander("Comprendre les chiffres et leur source", expanded=True):
            st.write("La température moyenne utilise uniquement les jours renseignés (T2M). Le total de pluie additionne les valeurs quotidiennes (PRECTOTCORR) uniquement lorsque la période est complète. La pluie totale n’est pas la pluie efficace et ne suffit pas à calculer l’irrigation.")
            st.caption("Résolution météorologique source MERRA-2 : 0,5° latitude × 0,625° longitude ; rayonnement CERES SYN1deg : 1° × 1°. Ces mailles sont bien plus larges qu’une parcelle. Fréquence affichée : quotidienne UTC. Source et version : voir métadonnées ci-dessous.")
            st.markdown("[Sources et méthode météorologiques NASA POWER](https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/)")
            st.markdown(f"[Requête NASA exacte]({p['url']})")
            st.write(f"Téléchargement UTC : {p['retrieved_at_utc']}")
            st.dataframe(pd.DataFrame({"unité source": p["units"], "jours absents": missing}), width='stretch')
            st.json(p)
        with export_slot, st.container(border=True):
            section_label("01", "Climat & provenance", "Données quotidiennes NASA POWER et réponse originale.")
            st.download_button("Télécharger les données quotidiennes (CSV)", df.to_csv().encode("utf-8-sig"), "nasa_power_daily.csv", "text/csv")
            st.download_button("Télécharger la provenance (JSON)", json.dumps(p, ensure_ascii=False, indent=2), "nasa_power_provenance.json", "application/json")
            st.download_button("Télécharger la réponse NASA originale (JSON)", json.dumps(climate.raw_payload, ensure_ascii=False), "nasa_power_raw.json", "application/json")

with farm_tab:
    st.header("Mon exploitation" if page == "Exploitation" else "Mes stratégies culturales")
    st.caption("Une rotation est une suite de cultures sur la même parcelle. Pour essayer sans données personnelles, chargez les exemples fictifs.")
    st.button("Charger un scénario de démonstration", type="primary", on_click=activate_demo, args=(st.session_state,))
    demo_mode = st.session_state.get("demo_mode", False)
    if demo_mode:
        st.info("Exemples fictifs : Blé → Blé, Blé → Féverole, Blé → Pois chiche. Vous pouvez les modifier. Aucune date ni valeur de calcul n’est fournie.")
        st.button("Quitter le mode démonstration", on_click=deactivate_demo, args=(st.session_state,))
    else:
        st.write("Indiquez vos cultures dans l’ordre, puis deux autres suites de cultures à examiner. Laissez vides les informations que vous ne connaissez pas.")
    st.caption("Vous pouvez comparer vos choix sans calcul d’eau. Les paramètres techniques restent facultatifs.")
    with st.container(key="water_tools"), st.expander("Calcul de l’eau · données à fournir avec un conseiller"):
        st.write("Cette partie est facultative. Elle nécessite des données météo et des paramètres de culture documentés et déclarés applicables. Si vous ne les avez pas, passez directement aux rotations.")
        if st.button("Calculer l’ET₀ FAO-56 avec NASA POWER"):
            if climate is None:
                st.info("Chargez d’abord les données NASA du point et de la période choisis.")
            else:
                st.session_state.nasa_eto_result = calculate_power_eto(climate)
        computed_result = st.session_state.get("nasa_eto_result")
        use_computed_eto = False
        if computed_result is not None:
            st.write(f"ET₀ calculée disponible : {computed_result.provenance['available_days']}/{computed_result.provenance['expected_days']} jours · mm/jour.")
            st.caption("ET₀ dérivée des estimations NASA, pas une observation NASA ni une mesure de terrain. Humidité moyenne : équation FAO-56 19, moins souhaitable que les extrema RH. Albédo de référence 0,23 ; flux de chaleur du sol journalier nul. Aucune donnée météo manquante n’est inventée.")
            st.dataframe(computed_result.daily, width='stretch')
            st.json(computed_result.provenance)
            if not computed_result.complete:
                st.warning("ET₀ indisponible sur la période complète. Les jours concernés restent vides ; la colonne reason indique les entrées manquantes ou invalides. Aucun remplacement automatique.")
            with export_slot, st.container(border=True):
                section_label("02", "ET₀ calculée", "Série quotidienne, lacunes explicites et méthode de calcul.")
                st.download_button("Télécharger l’ET₀ calculée et ses lacunes (CSV)", computed_result.daily.to_csv().encode("utf-8-sig"), "agrinova_eto_fao56_daily.csv", "text/csv")
                st.download_button("Télécharger la méthode et la provenance ET₀ (JSON)", json.dumps(json_safe(computed_result.provenance), ensure_ascii=False, indent=2, allow_nan=False), "agrinova_eto_fao56_provenance.json", "application/json")
            requested_computed_eto = st.checkbox("Utiliser cette ET₀ calculée pour les rotations", disabled=not computed_result.complete)
            use_computed_eto = requested_computed_eto and computed_result.complete
            if not computed_result.complete:
                use_computed_eto = st.checkbox("Utiliser les jours ET₀ disponibles, avec contrôle de chaque saison", key="use_season_eto")
                st.caption("Une lacune hors saison ne bloque pas la culture. Chaque saison exige 100 % des jours ET₀ et des stades documentés ; aucun zéro ni interpolation ne remplace une lacune.")
        st.write("L’import externe reste disponible ci-dessous. Décochez l’utilisation de l’ET₀ calculée pour utiliser un fichier externe.")
        st.write("Pour calculer ETc, importez un CSV UTF-8 avec les colonnes `date` (AAAA-MM-JJ) et `eto_mm` (mm/jour). Il doit couvrir chaque jour cultural. Aucune ET₀ n’est déduite automatiquement de la température et de la pluie.")
        with export_slot, st.container(border=True):
            section_label("03", "Import externe", "Modèle de fichier vide ; aucune valeur préremplie.")
            st.download_button("Modèle CSV vide (sans valeurs)", "date,eto_mm\n", "eto_template.csv", "text/csv")
        eto_file = st.file_uploader("Série ET₀ journalière", type=["csv"])
        st.caption("Le modèle CSV vide et les téléchargements sont regroupés dans Export.")
        eto_source = st.text_input("Source ET₀, méthode, point, période et validateur", placeholder="Référence du document ou URL et identité/date de validation")
        eto_method = st.text_input("Méthode de calcul de l’ET₀", placeholder="Méthode documentée par le fournisseur ; non vérifiée automatiquement")
        eto_units = st.selectbox("Unité de la série ET₀", ["À renseigner", "mm/day"])
        eto_surface = st.selectbox("Surface de référence ET₀", ["À renseigner", "short_grass"])
        eto_time = st.selectbox("Standard temporel de la série ET₀", ["À renseigner", "UTC"])
        eto_lat = st.number_input("Latitude représentée par l’ET₀ (°)", min_value=-90.0, max_value=90.0, value=None, format="%.4f")
        eto_lon = st.number_input("Longitude représentée par l’ET₀ (°)", min_value=-180.0, max_value=180.0, value=None, format="%.4f")
        eto_validated = st.checkbox("Je confirme les références et l’applicabilité déclarées de cette ET₀")
        st.caption("Herbe courte : short_grass. Les dates du fichier définissent la période enregistrée. Ces contrôles ne certifient ni la méthode FAO-56 ni une validation agronomique indépendante.")
        eto = None
        if use_computed_eto and computed_result is not None:
            try:
                eto = computed_eto_for_crops(computed_result,
                    expected_location=climate.provenance["requested_coordinates"] if climate is not None else {"latitude": lat, "longitude": lon})
                st.caption("Méthode calculée et testée sur un cas FAO publié ; cela ne certifie ni les observations de la parcelle ni les références Kc.")
            except (WaterInputError, EtoError) as exc:
                st.error(str(exc))
        elif eto_file is not None:
            try:
                eto = validate_eto(pd.read_csv(io.BytesIO(eto_file.getvalue())), eto_source, eto_validated,
                    metadata={"calculation_method": eto_method, "units": eto_units, "reference_surface": eto_surface,
                              "time_standard": eto_time, "location": {"latitude": eto_lat, "longitude": eto_lon}},
                    expected_location=climate.provenance["requested_coordinates"] if climate is not None else {"latitude": lat, "longitude": lon})
                st.success(f"ET₀ acceptée selon votre déclaration : {len(eto)} jours. La source n’est pas certifiée automatiquement.")
                st.json(eto.attrs["agrinova_metadata"])
            except (WaterInputError, pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeError) as exc:
                st.error(str(exc))
    with st.form("farmer_form", border=False):
        st.caption("Après modification, validez avec « Comparer les trois rotations » avant de changer de section. Les informations enregistrées restent disponibles dans cette session.")
        priorities = st.multiselect("Vos priorités", ["Économie d’eau", "Réduction du risque", "Santé du sol", "Production", "Revenu", "Charge de travail"])
        with st.container(key="farm_profile"), st.expander("Ma parcelle et mes contraintes · facultatif", expanded=page == "Exploitation"):
            st.caption("Ajoutez ce que vous savez. Une information inconnue reste inconnue.")
            c1, c2 = st.columns(2)
            area = c1.number_input("Surface de la parcelle (ha) · facultative", min_value=0.01, value=None, step=0.1)
            soil = c2.text_input("Sol : caractéristiques connues et source", placeholder="Inconnu si aucune analyse disponible")
            irrigation = st.text_input("Irrigation : mode, disponibilités, calendrier et restrictions", placeholder="Décrivez ce qui est connu ; aucune disponibilité n’est supposée")
            notes = st.text_area("Contraintes et historique supplémentaires", placeholder="Antécédents, matériel, main-d’œuvre, marchés, etc.")
        with st.expander("Période de comparaison · modifier si nécessaire"):
            st.caption("Comparez les trois rotations sur la même période. Les dates de chaque culture se renseignent ci-dessous.")
            h1, h2 = st.columns(2)
            horizon_start = h1.date_input("Début de l’horizon commun", date.fromisoformat(climate.provenance["start"]) if climate is not None else default_start)
            horizon_end = h2.date_input("Fin de l’horizon commun", date.fromisoformat(climate.provenance["end"]) if climate is not None else default_end)
        rotations = []
        with st.container(key="rotation_grid"):
            scenario_columns = st.columns(3, gap="medium")
            for i, name in enumerate(DEMO_NAMES if demo_mode else ["Rotation actuelle", "Alternative 1", "Alternative 2"]):
                with scenario_columns[i]:
                    with st.container(border=True, key=f"rotation_card_{i}"):
                        badge = "RÉFÉRENCE FICTIVE" if demo_mode and i == 0 else ("EXEMPLE FICTIF" if demo_mode else ("VOTRE RÉFÉRENCE" if i == 0 else f"ALTERNATIVE {i}"))
                        badge_style = "demo" if demo_mode else ("reference" if i == 0 else "")
                        st.markdown(f'<span class="scenario-badge {badge_style}">{badge}</span>', unsafe_allow_html=True)
                        st.subheader((["Référence fictive", "Alternative 1 fictive", "Alternative 2 fictive"][i]) if demo_mode else name)
                        crop_summary = st.empty()
                        base = pd.DataFrame({"crop": pd.Series([""], dtype="str"),
                                             "start": pd.Series([None], dtype="datetime64[ns]"),
                                             "end": pd.Series([None], dtype="datetime64[ns]"),
                                             "kc": pd.Series([None], dtype="float64"), "kc_source": [""], "validated": [False]})
                        if demo_mode:
                            base = scenario_frame(i)
                        else:
                            base = st.session_state.get("manual_rotation_seed", {}).get(f"stages_{i}", base)
                        base = base.copy(deep=True)
                        for field in ("growth_stage", "regional_applicability", "kc_reference_surface", "crop_cycle"):
                            if field not in base:
                                base[field] = ""
                        for field in ("planting_date", "harvest_date"):
                            if field not in base:
                                base[field] = pd.Series(pd.NaT, index=base.index, dtype="datetime64[ns]")
                        editor_prefix = f"demo_{st.session_state['demo_revision']}_" if demo_mode else ""
                        if demo_mode:
                            base = st.session_state.get("dashboard_demo_seed", {}).get(f"{editor_prefix}stages_{i}", base).copy(deep=True)
                        with st.expander("Modifier les cultures et les dates"):
                            st.markdown('<div class="input-guide"><span>CULTURES</span><span>CALENDRIER</span><span>KC & RÉFÉRENCES</span></div>', unsafe_allow_html=True)
                            st.caption("Une ligne par culture ou stade, dans l’ordre de succession. Ajoutez une ligne en bas du tableau. Les colonnes Kc, référence et validation concernent uniquement le calcul d’eau : laissez-les vides si vous ne les connaissez pas.")
                            stages = st.data_editor(base, num_rows="dynamic", key=f"{editor_prefix}stages_{i}", hide_index=True, width='stretch',
                                column_config={"crop": st.column_config.TextColumn("Culture / stade", required=True),
                                               "start": st.column_config.DateColumn("Début", required=not demo_mode, format="YYYY-MM-DD"),
                                               "end": st.column_config.DateColumn("Fin", required=not demo_mode, format="YYYY-MM-DD"),
                                               "kc": st.column_config.NumberColumn("Kc · facultatif", min_value=0.0, format="%.3f"),
                                               "kc_source": st.column_config.TextColumn("Référence Kc : culture, stade, contexte"),
                                               "validated": st.column_config.CheckboxColumn("Applicabilité Kc déclarée"),
                                               "growth_stage": st.column_config.TextColumn("Stade de croissance"),
                                               "crop_cycle": st.column_config.TextColumn("Cycle cultural · facultatif", help="Même identifiant pour tous les stades d’une culture. Utilisez des identifiants distincts pour deux cycles successifs de blé, par exemple."),
                                               "planting_date": st.column_config.DateColumn("Semis connu · facultatif", format="YYYY-MM-DD"),
                                               "harvest_date": st.column_config.DateColumn("Récolte connue · facultative", format="YYYY-MM-DD"),
                                               "regional_applicability": st.column_config.TextColumn("Applicabilité régionale et justification"),
                                               "kc_reference_surface": st.column_config.SelectboxColumn("Surface de référence Kc", options=["short_grass"])})
                            st.caption("Les références et leur applicabilité sont déclarées par l’utilisateur ; aucune vérification indépendante n’est effectuée. Aucun coefficient n’est prérempli.")
                            st.caption("Blé, féverole et pois chiche : saisissez chaque stade avec ses dates, Kc, source et justification d’applicabilité. Le Kc reste constant sur l’intervalle saisi ; découpez les transitions selon votre référence. Aucun calendrier local ni ajustement climatique n’est présumé.")
                            st.markdown(f"[FAO-56, chapitre 6 : méthode, cultures du tableau 12 et limites de transfert]({FAO_CROP_REFERENCE})")
                            st.caption("Les dates de semis et récolte sont distinctes des limites des stades. Renseignez-les une fois par cycle si elles sont connues ; sans elles, aucune période de sol potentiellement sans couvert n’est déduite.")
                        crops_entered = [value.strip() for value in stages["crop"] if isinstance(value, str) and value.strip()]
                        crop_summary.info(" → ".join(crops_entered) if crops_entered else "Aucune culture renseignée. Ouvrez « Modifier les cultures et les dates » pour commencer.")
                        families = list(dict.fromkeys(identify_crop(crop)["family"] or "Inconnue" for crop in crops_entered))
                        st.caption("Familles : " + (" · ".join(families) if families else "à renseigner"))
                        st.caption("Calendrier et Kc : saisies facultatives, sans valeur présumée. Références déclaratives, sans validation locale indépendante.")
                        st.caption("Bénéfices, risques et lacunes : examinez les preuves dans Comparaison après enregistrement.")
                        checks_base = pd.DataFrame({"constraint": CONSTRAINTS, "status": ["Inconnu"] * len(CONSTRAINTS), "evidence": [""] * len(CONSTRAINTS)})
                        if not demo_mode:
                            checks_base = st.session_state.get("manual_rotation_seed", {}).get(f"checks_{i}", checks_base)
                        else:
                            checks_base = st.session_state.get("dashboard_demo_seed", {}).get(f"{editor_prefix}checks_{i}", checks_base)
                        with st.expander("Vérifier le sol, l’eau et les moyens disponibles"):
                            st.caption("Gardez « Inconnu » tant qu’un point n’a pas été vérifié. Si vous choisissez « Compatible » ou « Incompatible », indiquez pourquoi et avec quelle source.")
                            checks = st.data_editor(checks_base, key=f"{editor_prefix}checks_{i}", hide_index=True, width='stretch',
                                disabled=["constraint"], column_config={"constraint": "Contrainte",
                                    "status": st.column_config.SelectboxColumn("État déclaré", options=STATUSES, required=True),
                                    "evidence": st.column_config.TextColumn("Justification, source, validateur et date")})
                        if not demo_mode:
                            snapshot = st.session_state.setdefault("manual_rotation_snapshot", {})
                            snapshot[f"stages_{i}"] = stages.copy(deep=True)
                            snapshot[f"checks_{i}"] = checks.copy(deep=True)
                        else:
                            snapshot = st.session_state.setdefault("dashboard_demo_snapshot", {})
                            snapshot[f"{editor_prefix}stages_{i}"] = stages.copy(deep=True)
                            snapshot[f"{editor_prefix}checks_{i}"] = checks.copy(deep=True)
                        rotations.append((name, stages, checks))
        st.caption("Cliquez pour enregistrer vos saisies et voir les différences dans l’étape 3.")
        submitted = st.form_submit_button("Comparer les trois rotations", type="primary")
    if submitted:
        st.session_state.pop("comparison", None)
        if horizon_start > horizon_end or (horizon_end - horizon_start).days > 3660:
            st.error("Horizon invalide : début ≤ fin, durée maximale dix ans.")
        else:
            results = []
            for name, stages, checks in rotations:
                checks_map = {row["constraint"]: {"status": row["status"], "evidence": row["evidence"]} for row in checks.to_dict("records")}
                result = evaluate_rotation(name, stages.to_dict("records"), checks_map, horizon_start, horizon_end,
                    eto=eto, area_ha=area, climate=climate.daily if climate is not None else None,
                    climate_provenance=climate.provenance if climate is not None else None)
                if demo_mode:
                    result = annotate_demo(result, stages.to_dict("records"))
                results.append(result)
            st.session_state.comparison = {"results": results, "farm": {"surface_ha": area, "sol": soil,
                "irrigation": irrigation, "priorités": priorities, "notes": notes,
                "début": horizon_start.isoformat(), "fin": horizon_end.isoformat()},
                "eto_source": eto.attrs["agrinova_metadata"]["source"] if eto is not None else None,
                "eto_metadata": eto.attrs["agrinova_metadata"] if eto is not None else None,
                "eto_derivation": computed_result.provenance if use_computed_eto and eto is not None else None,
                "comparability": assess_comparability(results), "schema_version": "2",
                "mode": "demonstration" if demo_mode else "farmer_input",
                "rotation_origin": DEMO_NOTICE if demo_mode else "Rotations saisies par l’utilisateur",
                "climate_provenance": climate.provenance if climate is not None else None,
                "calculated_at_utc": datetime.now(timezone.utc).isoformat()}
            st.success("Vos saisies sont enregistrées. Ouvrez « Comparer les choix » pour consulter le résultat.")

with compare_tab:
    st.header("Vos choix, côte à côte")
    saved = st.session_state.get("comparison")
    if saved is None:
        st.markdown('''<section class="empty-state"><div class="empty-symbol" aria-hidden="true">⇄</div>
<h3>Vos trois rotations, une vue d’ensemble</h3><p>Dans « Préparer mes rotations », renseignez votre rotation et deux alternatives, ou chargez les exemples fictifs. Cliquez ensuite sur « Comparer les trois rotations » pour consulter les résultats, les risques et les informations à compléter.</p></section>''', unsafe_allow_html=True)
    else:
        results = saved["results"]
        comparability = saved.get("comparability", {"quantitative_comparison_allowed": False,
            "reasons": ["Ancien résultat : relancer la comparaison pour vérifier les nouvelles métadonnées et couvertures"]})
        totals_comparable = comparability["quantitative_comparison_allowed"]
        saved_demo = saved.get("mode") == "demonstration"
        if saved_demo:
            st.info("Vous comparez des exemples fictifs, pas des recommandations. Sans dates et références documentées, le calcul d’eau et l’analyse météo par culture restent indisponibles.")
        st.caption(f"Résultat enregistré le {saved['calculated_at_utc']} · Après une modification, cliquez de nouveau sur « Comparer les trois rotations ».")
        st.write("Priorités déclarées : " + (", ".join(saved["farm"]["priorités"]) or "non renseignées"))
        with st.container(key="comparison_grid"):
            summary_columns = st.columns(3, gap="medium")
            for number, result in enumerate(results):
                with summary_columns[number]:
                    rotation_summary(result, number, totals_comparable)
        section_label("01", "Résultats quantitatifs", "Périodes équivalentes et couverture complète avant toute comparaison de totaux.")
        table = []
        for r in results:
            table.append({"Stratégie": r["name"], "Cultures / stades": " → ".join(r["declared_crops"] if r.get("is_demo") else [s["crop"] for s in r["stages"]]),
                "État": r["status"], "ETc des stades saisis (mm)": r["water"]["etc_mm"] if r["water"] and totals_comparable else None,
                "Volume ETc (m³)": r["water"]["volume_m3"] if r["water"] and comparability.get("volume_comparison_allowed", False) else None,
                "Comparabilité": "Totaux ETc comparables" if totals_comparable else "Totaux non comparables",
                "Jours hors stades": r["uncovered_days"]})
        with st.container(border=True, key="comparison_results"):
            st.subheader("Résultats calculés et données disponibles")
            st.caption("Les valeurs d’eau, lorsqu’elles sont disponibles, viennent des calculs sur les données fournies. Une case vide ne signifie pas zéro. Aucun classement d’aptitude n’est calculé.")
            st.dataframe(pd.DataFrame(table), hide_index=True, width='stretch',
                column_order=["Stratégie", "Cultures / stades", "État", "Comparabilité"] + (["ETc des stades saisis (mm)", "Volume ETc (m³)", "Jours hors stades"] if totals_comparable else []),
                column_config={"Stratégie": "Rotation", "Cultures / stades": "Suite de cultures", "État": "Points à vérifier",
                    "ETc des stades saisis (mm)": st.column_config.NumberColumn("Eau des cultures (mm)", help="ETc calculée sur les stades renseignés, pas un besoin d’irrigation"),
                    "Volume ETc (m³)": st.column_config.NumberColumn("Volume correspondant (m³)"),
                    "Jours hors stades": st.column_config.NumberColumn("Jours non renseignés")})
            if not totals_comparable:
                st.warning("Les totaux ne peuvent pas être comparés comme des rotations complètes : " + "; ".join(comparability.get("reasons", [])))
            with st.expander("Périodes, couverture et états de validation"):
                def shown_period(period):
                    return "Non calculée" if not period else f"{period['start']} → {period['end']}"
                coverage_rows = []
                for result in results:
                    coverage, states = result.get("coverage", {}), result.get("statuses", {})
                    coverage_rows.append({"Rotation": result["name"],
                        "Période attendue": shown_period(coverage.get("expected_period")),
                        "Période calculée ETc": shown_period(coverage.get("calculated_period")),
                        "Jours attendus": coverage.get("expected_days"),
                        "Couverture cultures (%)": 100 * coverage.get("crop_coverage", 0),
                        "Couverture ETc (%)": 100 * coverage.get("etc_coverage", 0),
                        "Jours cultures manquants": coverage.get("crop_missing_days"),
                        "Jours ETc manquants": coverage.get("missing_etc_days"),
                        "Origine des informations": "Démonstration fictive" if result.get("is_demo") else "Déclarations utilisateur",
                        "Déclarations de contraintes complètes": states.get("farmer_declarations") == "recorded",
                        "Données complètes": states.get("data_complete", False),
                        "Calcul disponible": states.get("calculation_available", False),
                        "Validation agronomique": "Non réalisée", "Comparabilité": "Oui, ETc uniquement" if totals_comparable else "Non"})
                st.dataframe(pd.DataFrame(coverage_rows), hide_index=True, width='stretch')
                st.caption("La couverture est une proportion de jours, pas un score d’aptitude. Une déclaration de compatibilité ne prouve pas la faisabilité agronomique.")
            if not any(r["water"] for r in results):
                st.info("Calcul d’eau indisponible : il manque des dates ou des métadonnées complètes. Vous pouvez quand même examiner les cultures, les risques et les informations à compléter.")
            else:
                with st.expander("Voir les calculs d’eau jour par jour"):
                    for r in results:
                        if r["water"]:
                            st.write("**" + r["name"] + "**")
                            st.write(f"ETc sur les seuls stades renseignés : {r['water']['etc_mm']:.2f} mm. " + ("Total sur l’horizon complet." if r.get("coverage", {}).get("comparison_eligible") else "Total partiel : ne pas interpréter comme un total complet de rotation."))
                            st.caption("Calcul : ETc = Σ(Kc × ET₀), pas journalier ; volume = ETc × surface ha × 10. Pas de soustraction de pluie, pas de bilan du sol, pas d’irrigation estimée. Jours hors stades exclus.")
                            st.dataframe(pd.DataFrame(r["water"]["daily"]), hide_index=True, width='stretch')
            with st.expander("ETc par culture · saisons, stades et couverture"):
                for r in results:
                    st.write("**" + r["name"] + "**")
                    for crop in r.get("crop_results", []):
                        st.write(str(crop["crop"]))
                        if crop.get("coverage"):
                            st.json(crop["coverage"])
                        if crop["error"]:
                            st.warning(crop["error"])
                        if crop["water"]:
                            st.write(f"Cumul saisonnier ETc : {crop['water']['etc_mm']:.2f} mm · couverture complète de la saison saisie.")
                            st.dataframe(pd.DataFrame(crop["water"]["daily"]), hide_index=True, width='stretch')
                        st.dataframe(pd.DataFrame(crop["stages"]), hide_index=True, width='stretch')
                        st.caption(" ".join(crop["limitations"]))
                        st.markdown(f"[Méthode FAO-56, équation 58]({crop['method_reference']})")
        with export_slot, st.container(border=True):
            section_label("04", "Rotations & preuves", "Comparaison enregistrée, déclarations, références et limites.")
            st.download_button("Télécharger la comparaison et ses preuves (JSON)", json.dumps(json_safe(saved), ensure_ascii=False, indent=2, default=str, allow_nan=False), "agrinova_comparison.json", "application/json")
        if not saved_demo and any(not r["stages"] for r in results):
            st.warning("Trois stratégies complètes ne sont pas encore renseignées. Les cases vides restent indisponibles.")
        signatures = [tuple((str(s.get("crop") or "").casefold(), str(s["start"]), str(s["end"])) for s in (r["declared_stages"] if r.get("is_demo") else r["stages"])) for r in results]
        if all(signatures) and len(set(signatures)) < 3:
            st.warning("Certains calendriers sont identiques : renseignez des stratégies distinctes pour comparer trois rotations différentes.")
        st.warning("Il n’y a pas de meilleur choix automatique. Un besoin en eau plus faible ne suffit pas à prouver qu’une rotation convient à votre parcelle. Vérifiez les points importants avec un conseiller.")
        st.subheader("Considérations agricoles")
        st.caption("Ces explications qualitatives complètent les chiffres. Les avantages possibles restent à vérifier pour votre parcelle.")
        section_label("02", "Preuves & considérations agronomiques", "Déclarations, références documentaires et calculs restent des catégories distinctes.")
        st.write("**Ouvrez une rotation pour voir ses avantages possibles, ses risques et ce qu’il reste à vérifier.**")
        for r in results:
            with st.expander(r["name"]):
                st.write("**État des vérifications :** " + r["status"])
                st.write("**Pourquoi l’examiner :** " + r["purpose"])
                st.write("**Bénéfice potentiel de l’analyse :** " + r["benefit"])
                if r.get("agronomy"):
                    agronomy = r["agronomy"]
                    st.write("**Analyse agronomique qualitative · aucune recommandation automatique**")
                    identities = [{"Cycle": c["number"], "Culture": c["crop"], "Famille": c["family"] or "Inconnue",
                        "Légumineuse": "Inconnu" if c["legume"] is None else ("Oui" if c["legume"] else "Non"),
                        "Fixation d’azote": {"conditional_potential": "Potentiel conditionnel, non quantifié", "not_a_legume": "Non légumineuse", "unknown": "Inconnue"}[c["nitrogen_fixation"]["status"]]} for c in agronomy["cycles"]]
                    st.dataframe(pd.DataFrame(identities), hide_index=True, width='stretch')
                    for label, key in (("Éléments documentés", "evidence"), ("Bénéfices potentiels", "potential_benefits"), ("Risques à examiner", "risks")):
                        st.write("**" + label + "**")
                        for item in agronomy[key]:
                            st.write("• " + item["text"] + (" [" + ", ".join(item["reference_ids"]) + "]" if item["reference_ids"] else ""))
                    st.write("**Calendrier déclaré**")
                    st.write("Limites semis/récolte : " + {"invalid": "Invalides", "complete_declared": "Renseignées, sans validation locale", "unknown": "Inconnues ou incomplètes"}[agronomy["calendar"]["boundary_status"]])
                    periods = agronomy["calendar"]["potential_bare_soil_periods"]
                    if periods:
                        st.dataframe(pd.DataFrame([{"Début": p["start"], "Fin": p["end"], "Jours": p["days"],
                            "Après le cycle": p["after_cycle"], "Avant le cycle": p["before_cycle"],
                            "Couverture réelle du sol": "Inconnue"} for p in periods]), hide_index=True, width='stretch')
                        st.caption("Intercultures internes uniquement. Couvert, résidus et état réel du sol inconnus : aucune durée de sol nu mesurée.")
                    for reference in agronomy["references"]:
                        st.markdown(f"[{reference['id']} · {reference['title']}]({reference['url']})")
                        st.caption(reference["scope"])
                    st.write("**Informations manquantes et incertitudes**")
                    for item in r["missing_information"]:
                        st.write("• " + item)
                    st.write("**Disponibilité des calculs :** " + ("ETc disponible sur les stades saisis." if r["calculation_availability"]["etc"] else "ETc indisponible : " + str(r["calculation_availability"]["etc_reason"])))
                    for item in agronomy["limitations"]:
                        st.caption(item)
                if r.get("is_demo"):
                    context = r["agronomic_context"]
                    st.write("**Bénéfices agronomiques potentiels — non validés localement**")
                    for item in context["potential_benefits"]:
                        st.write("• " + item)
                    st.write("**Risques agronomiques et inconnues**")
                    for item in context["risks_and_unknowns"]:
                        st.write("• " + item)
                    for reference in context["references"]:
                        st.markdown(f"[{reference['title']}]({reference['url']})")
                        st.caption(reference["scope"])
                st.write("**Éléments de preuve**")
                for item in r["evidence"]:
                    st.write("• " + item)
                if not r["evidence"]:
                    st.write("Aucune compatibilité ni estimation hydrique établie.")
                if r["climate_evidence"]:
                    st.dataframe(pd.DataFrame(r["climate_evidence"]), hide_index=True, width='stretch')
                    st.caption("Contexte NASA historique sur les dates exactes saisies ; ce tableau ne prouve pas l’aptitude des cultures.")
                else:
                    st.caption("Preuves climatiques par culture indisponibles : renseignez des dates, chargez NASA POWER et recalculez la comparaison.")
                st.write("**Risques et informations manquantes**")
                for item in r["issues"] + r["risks"]:
                    st.write("• " + item)
                st.write("**Limites**")
                for item in r["limitations"]:
                    st.write("• " + item)
        with st.expander("Méthode de calcul de l’eau"):
            st.write("L’eau des cultures affichée est une estimation dans des conditions standard (ETc). Elle ne représente ni l’eau réellement consommée, ni la quantité à apporter par irrigation. Les calculs utilisent les données et paramètres documentés et déclarés applicables que vous fournissez. Ces contrôles ne constituent pas une validation agronomique indépendante.")
            st.markdown("[Méthode FAO-56 : ET₀, ETc et limites d’application](https://www.fao.org/4/X0490E/x0490e04.htm)")

with toolbar_slot:
    context, action = st.columns([5, 1], vertical_alignment="center")
    with context:
        if climate is not None:
            loaded_point = climate.provenance["requested_coordinates"]
            st.markdown(f'<div class="toolbar-context"><span class="location-pill">{loaded_point["latitude"]:.4f}° · {loaded_point["longitude"]:.4f}°</span><span>{climate.provenance["start"]} → {climate.provenance["end"]} · UTC</span><span class="toolbar-status">Historique chargé</span></div>', unsafe_allow_html=True)
        else:
            st.caption("Point de départ : Beni Mellal · Aucune donnée chargée · Configurez le lieu et la période dans Paramètres.")
    action.button("Exporter", on_click=go_to_export, width="stretch")
with overview_slot:
    overview(climate, st.session_state.get("nasa_eto_result"), st.session_state.get("comparison"),
        None if climate is None else ("Indisponible" if pd.isna(mean_temp) else f"{mean_temp:.1f} °C"),
        None if climate is None else (f"{df.PRECTOTCORR.sum():.1f} mm" if missing.PRECTOTCORR == 0 else "Lacunes"),
        None if climate is None else f"{df.T2M.count()}/{len(df)} · {df.PRECTOTCORR.count()}/{len(df)}")
with data_slot:
    st.subheader("Sources & portée scientifique")
    if climate is None:
        st.info("Chargez NASA POWER dans Paramètres pour consulter la provenance du point et de la période.")
    if st.session_state.get("nasa_eto_result") is not None:
        with st.expander("Méthode et provenance de l’ET₀ calculée"):
            st.json(st.session_state.nasa_eto_result.provenance)
    st.caption("Les références documentaires ne constituent pas une validation locale des données ou des rotations. Aucun modèle d’irrigation n’est intégré.")
st.caption("AgriNova AI · NASA Space Apps · Vos saisies restent dans cette session et ne sont pas enregistrées sur disque. Téléchargez vos résultats pour en garder une copie.")
