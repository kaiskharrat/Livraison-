import streamlit as st
import gspread
import pandas as pd
import requests
import time
import re
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURATION INITIALE ---
st.set_page_config(page_title="Dashboard Livraisons", layout="wide")

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
    # Utilisation des Secrets Streamlit pour la sécurité
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

# --- LOGIQUE INSTA-DELIVERY ---
def process_insta_data(data):
    rows = []
    for row in data:
        if not any(row): continue
        row = row + [""] * 20
        rows.append([
            row[0], row[4], row[12], f"{row[1]} {row[3]}", row[8], row[7], 1, "", 
            row[13], row[14] if row[13] == "1" else "", 1, 1, 2
        ])
    cols = ["Nom", "Tel", "CP", "Adresse", "Désign.", "Montant", "Colis", "Obs", "Echange", "Contenu", "Open", "Fragile", "Paiement"]
    return pd.DataFrame(rows, columns=cols)

def envoyer_insta(df):
    url = "https://app.insta-delivery.com/API/add"
    succes, echecs = 0, 0
    progress = st.progress(0)
    
    for i, row in df.iterrows():
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
        progress.progress((i + 1) / len(df))
    return succes, echecs

# --- LOGIQUE JETPACK ---
def process_jetpack_data(data):
    rows = []
    jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    for row in data:
        if not any(row): continue
        row = row + [""] * 10
        tel_clean = nettoyer_numero_tel(row[4])
        msg = str(row[5]).strip().lower() if str(row[5]).strip().lower() in jours else ""
        rows.append([row[7], row[0], row[3], row[3], row[1], tel_clean, "", row[8], 1, msg])
    cols = ["prix", "nom", "gouvernerat", "ville", "adresse", "tel", "tel2", "designation", "nb_article", "msg"]
    return pd.DataFrame(rows, columns=cols)

def envoyer_jetpack(df):
    url = "https://www.jetpack.tn/apis/shopp12-SFJKJSV348FK29HFSKDKDB438UJFDKJF394UTDJFDKDCVR56/v1/post.php"
    succes, echecs = 0, 0
    progress = st.progress(0)
    
    for i, row in df.iterrows():
        payload = row.to_dict()
        try:
            r = requests.post(url, data=payload, timeout=15)
            if r.status_code == 200: succes += 1
            else: echecs += 1
        except: echecs += 1
        progress.progress((i + 1) / len(df))
    return succes, echecs

# --- INTERFACE ---
st.title("🚀 Système Centralisé de Livraison")

tab1, tab2 = st.tabs(["📦 Insta-Delivery", "✈️ Jetpack"])

with tab1:
    if st.button("Charger données Insta"):
        client = get_gspread_client()
        data = client.open_by_key(SHEET_KEY).worksheet("insta").get_all_values()
        st.session_state['df_insta'] = process_insta_data(data)
    
    if 'df_insta' in st.session_state:
        st.write(st.session_state['df_insta'])
        if st.button("Confirmer l'envoi vers Insta-Delivery"):
            s, e = envoyer_insta(st.session_state['df_insta'])
            st.success(f"Terminé ! Succès: {s}, Échecs: {e}")

with tab2:
    if st.button("Charger données Jetpack"):
        client = get_gspread_client()
        data = client.open_by_key(SHEET_KEY).worksheet("jetpack").get_all_values()
        st.session_state['df_jetpack'] = process_jetpack_data(data)
    
    if 'df_jetpack' in st.session_state:
        st.write(st.session_state['df_jetpack'])
        if st.button("Confirmer l'envoi vers Jetpack"):
            s, e = envoyer_jetpack(st.session_state['df_jetpack'])
            st.success(f"Terminé ! Succès: {s}, Échecs: {e}")
