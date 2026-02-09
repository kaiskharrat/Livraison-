import streamlit as st
import gspread
import pandas as pd
import requests
import time
import re
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURATION INITIALE ---
st.set_page_config(page_title="Dashboard Livraisons", layout="wide", page_icon="🚚")

SHEET_KEY = "1VyiPxyS6Y2xXACja2ah0U7ttNDs-J-5kCxH_yKnaS_c"

# --- FONCTIONS UTILES ---
def nettoyer_numero_tel(numero):
    if pd.isna(numero) or numero == "":
        return ""
    chiffres = re.sub(r'\D', '', str(numero))
    if len(chiffres) > 8 and chiffres.startswith('216'):
        chiffres = chiffres[3:]
    if len(chiffres) >= 8:
        return chiffres[-8:]
    return ""

def get_gspread_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

# --- LOGIQUE DE TRAITEMENT ---
def process_insta_data(data):
    rows = []
    # On vérifie si la première ligne est une entête. Si oui, on commence à la ligne 1.
    # Si les données commencent direct à la ligne 0, on change data[1:] par data[0:]
    for row in data: 
        if not any(row) or row[0] == "Nom destinataire": # Ignore les lignes vides ou l'entête
            continue
        row = row + [""] * 20
        rows.append([
            row[0], row[4], row[12], f"{row[1]} {row[3]}", row[8], row[7], 1, "", 
            row[13], row[14] if row[13] == "1" else "", 1, 1, 2
        ])
    cols = ["Nom", "Tel", "CP", "Adresse", "Désign.", "Montant", "Colis", "Obs", "Echange", "Contenu", "Open", "Fragile", "Paiement"]
    return pd.DataFrame(rows, columns=cols)

def process_jetpack_data(data):
    rows = []
    jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    for row in data:
        if not any(row) or row[0] == "Nom":
            continue
        row = row + [""] * 10
        tel_clean = nettoyer_numero_tel(row[4])
        msg = str(row[5]).strip().lower() if str(row[5]).strip().lower() in jours else ""
        rows.append([row[7], row[0], row[3], row[3], row[1], tel_clean, "", row[8], 1, msg])
    cols = ["prix", "nom", "gouvernerat", "ville", "adresse", "tel", "tel2", "designation", "nb_article", "msg"]
    return pd.DataFrame(rows, columns=cols)

# --- INTERFACE ---
st.title("🚀 Système Centralisé de Livraison")

tab1, tab2 = st.tabs(["📦 Insta-Delivery", "✈️ Jetpack"])

# --- ONGLET INSTA-DELIVERY ---
with tab1:
    if st.button("🔄 Charger données Insta"):
        with st.spinner("Récupération des données..."):
            try:
                client = get_gspread_client()
                # Correction ici pour bien récupérer TOUTES les valeurs
                data = client.open_by_key(SHEET_KEY).worksheet("insta").get_all_values()
                df = process_insta_data(data)
                if not df.empty:
                    st.session_state['df_insta'] = df
                    st.success(f"✅ {len(df)} lignes récupérées !")
                else:
                    st.warning("⚠️ Aucune donnée trouvée dans la feuille 'insta'. Vérifiez que vos données ne sont pas sur la ligne d'entête.")
            except Exception as e:
                st.error(f"Erreur de connexion : {e}")
    
    if 'df_insta' in st.session_state:
        st.dataframe(st.session_state['df_insta'], use_container_width=True)
        
        if st.button("🚀 Confirmer l'envoi vers Insta-Delivery"):
            url = "https://app.insta-delivery.com/API/add"
            succes, echecs = 0, 0
            status_text = st.empty()
            progress_bar = st.progress(0)
            
            df = st.session_state['df_insta']
            for i, row in df.iterrows():
                status_text.text(f"Envoi {i+1}/{len(df)} : {row['Nom']}")
                payload = {
                    "login": "shop-p5", "password": "81490", "reference": f"GS_{i+1}",
                    "nom": row["Nom"], "tel": str(row["Tel"]), "code": str(row["CP"]),
                    "adresse": row["Adresse"], "designation": row["Désign."],
                    "montant_reception": str(row["Montant"]), "modalite": int(row["Paiement"]),
                    "contenuEchange": row["Contenu"], "nombre_piece": int(row["Colis"]),
                    "open_parcel": int(row["Open"]), "fragile": int(row["Fragile"])
                }
                try:
                    r = requests.post(url, json=payload, timeout=15)
                    if r.status_code == 200: succes += 1
                    else: echecs += 1
                except: echecs += 1
                progress_bar.progress((i + 1) / len(df))
            
            st.balloons()
            st.success(f"Terminé ! Succès: {succes} | Échecs: {echecs}")

# --- ONGLET JETPACK ---
with tab2:
    if st.button("🔄 Charger données Jetpack"):
        with st.spinner("Récupération..."):
            try:
                client = get_gspread_client()
                data = client.open_by_key(SHEET_KEY).worksheet("jetpack").get_all_values()
                df = process_jetpack_data(data)
                if not df.empty:
                    st.session_state['df_jetpack'] = df
                    st.success(f"✅ {len(df)} lignes récupérées !")
                else:
                    st.warning("⚠️ Aucune donnée trouvée dans 'jetpack'.")
            except Exception as e:
                st.error(f"Erreur : {e}")
    
    if 'df_jetpack' in st.session_state:
        st.dataframe(st.session_state['df_jetpack'], use_container_width=True)
        
        if st.button("🚀 Confirmer l'envoi vers Jetpack"):
            url = "https://www.jetpack.tn/apis/shopp12-SFJKJSV348FK29HFSKDKDB438UJFDKJF394UTDJFDKDCVR56/v1/post.php"
            succes, echecs = 0, 0
            status_text = st.empty()
            progress_bar = st.progress(0)
            
            df = st.session_state['df_jetpack']
            for i, row in df.iterrows():
                status_text.text(f"Envoi {i+1}/{len(df)} : {row['nom']}")
                payload = row.to_dict()
                try:
                    r = requests.post(url, data=payload, timeout=15)
                    if r.status_code == 200: succes += 1
                    else: echecs += 1
                except: echecs += 1
                progress_bar.progress((i + 1) / len(df))
            
            st.balloons()
            st.success(f"Terminé ! Succès: {succes} | Échecs: {echecs}")
