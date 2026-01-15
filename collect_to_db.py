import os
import requests
import pandas as pd
from datetime import datetime
import time
import re
import psycopg2
from psycopg2.extras import execute_values
from geopy.geocoders import Nominatim
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration de la connexion PostgreSQL
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    """Crée une connexion à la base de données PostgreSQL"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"Erreur de connexion à la base de données: {e}")
        raise

def collect_data_from_api():
    """Collecte les données depuis l'API Paris Data"""
    dataset = "que-faire-a-paris-"
    rows_per_page = 1000
    start = 0
    all_records = []
    
    logger.info("Début du téléchargement...")
    
    while True:
        try:
            url = "https://opendata.paris.fr/api/records/1.0/search/"
            params = {
                "dataset": dataset,
                "rows": rows_per_page,
                "start": start,
                "sort": "date_start",
            }
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f"Erreur réseau ou serveur : {e}")
            time.sleep(5)
            continue
        
        records = data.get("records", [])
        if not records:
            break
        
        all_records.extend(records)
        logger.info(f"📥 {len(records)} événements récupérés, total : {len(all_records)}")
        start += rows_per_page
        time.sleep(0.2)
    
    events = [r["fields"] for r in all_records]
    df = pd.DataFrame(events)
    logger.info(f"Collecte terminée : {len(df)} événements")
    return df

def clean_zipcode(z):
    """Nettoie et valide les codes postaux parisiens"""
    if pd.isna(z):
        return None
    
    z = str(z).strip().replace(" ", "")
    digits = re.sub(r'\D', '', z)
    
    if re.match(r'^7\d0\d{2}$', digits):
        digits = '75' + digits[-3:]
    
    if digits.startswith('75') and len(digits) == 4:
        digits = digits + '0'
    
    if len(digits) != 5:
        return None
    
    try:
        num = int(digits[-2:])
        if digits.startswith('75') and 1 <= num <= 20:
            return digits
        else:
            return None
    except:
        return None

def reverse_geocode_zip(coord_list):
    """Récupère le code postal depuis les coordonnées"""
    if not coord_list or len(coord_list) != 2:
        return None
    lat, lon = coord_list
    try:
        geolocator = Nominatim(user_agent="paris_cultural_activities")
        location = geolocator.reverse((lat, lon), exactly_one=True, timeout=10)
        if location and 'postcode' in location.raw['address']:
            return location.raw['address']['postcode']
        else:
            return None
    except:
        return None

def extract_age_range(text):
    """Extrait les âges min/max depuis le texte d'audience"""
    if pd.isna(text):
        return (None, None)
    min_match = re.search(r"A partir de (\d+)", text)
    max_match = re.search(r"Jusqu(?:'| à) (\d+)", text)
    min_age = int(min_match.group(1)) if min_match else None
    max_age = int(max_match.group(1)) if max_match else None
    return (min_age, max_age)

def extract_audience_categories(text):
    """Extrait les catégories d'audience"""
    categories = {
        'enfants': False,
        'jeunes': False,
        'adultes': False,
        'tout_petits': False,
        'tout_public': False
    }
    if pd.isna(text):
        return categories
    text_lower = text.lower()
    if 'enfants' in text_lower: categories['enfants'] = True
    if 'jeunes' in text_lower: categories['jeunes'] = True
    if 'adultes' in text_lower: categories['adultes'] = True
    if 'tout-petits' in text_lower: categories['tout_petits'] = True
    if 'tout public' in text_lower: categories['tout_public'] = True
    return categories

def parse_price_detail(text):
    """Parse les détails de prix pour extraire min/max"""
    if pd.isna(text):
        return (None, None)
    
    clean_text = re.sub(r'<[^>]+>', '', text)
    prices = re.findall(r'(\d+(?:[.,]\d+)?)\s*(?:€|EUR)', clean_text)
    prices = [float(p.replace(',', '.')) for p in prices]
    
    if len(prices) == 0:
        return (None, None)
    
    return (min(prices), max(prices))

def clean_data(df):
    """Nettoie et transforme les données"""
    logger.info("Nettoyage des données...")
    
    # Conversion des dates
    df["date_end"] = pd.to_datetime(df.get("date_end"), errors="coerce").dt.tz_localize(None)
    df["date_start"] = pd.to_datetime(df.get("date_start"), errors="coerce").dt.tz_localize(None)
    
    # Filtrer les événements futurs et actuels
    today = pd.Timestamp(datetime.today().date())
    df = df[df["date_end"] >= today]
    
    # Filtrer Paris uniquement
    df = df[df['address_city'].str.startswith("Paris", na=False)]
    
    # URL événement
    df['url_event'] = df['contact_url'].combine_first(df['access_link'])
    
    # Extraire lat/lon
    def extract_coords(lat_lon):
        # On vérifie d'abord si c'est une liste (cas normal de l'API)
        if isinstance(lat_lon, list):
            if len(lat_lon) == 2:
                return lat_lon[0], lat_lon[1]
            return None, None
        # Ensuite on vérifie si c'est nul/NaN (cas où l'info manque)
        if pd.isna(lat_lon):
            return None, None
        return None, None
    
    df[['lat', 'lon']] = df['lat_lon'].apply(lambda x: pd.Series(extract_coords(x)))
    
    # Nettoyage du code postal
    df['address_zipcode'] = df['address_zipcode'].apply(clean_zipcode)
    mask_missing = df['address_zipcode'].isna()
    df.loc[mask_missing, 'address_zipcode'] = df.loc[mask_missing, 'lat_lon'].apply(reverse_geocode_zip)
    
    # Catégories de sorties (dummies)
    if 'qfap_tags' in df.columns:
        tags = df['qfap_tags'].fillna('').str.split(';')
        df['cat_concert'] = tags.apply(lambda x: 'Concert' in x)
        df['cat_exposition'] = tags.apply(lambda x: 'Exposition' in x)
        df['cat_theatre'] = tags.apply(lambda x: any('Théâtre' in tag or 'Theatre' in tag for tag in x))
        df['cat_atelier'] = tags.apply(lambda x: 'Atelier' in x)
        df['cat_musee'] = tags.apply(lambda x: any('Musée' in tag or 'Musee' in tag for tag in x))
        df['cat_festival'] = tags.apply(lambda x: 'Festival' in x)
        df['cat_spectacle'] = tags.apply(lambda x: 'Spectacle' in x)
        df['cat_cinema'] = tags.apply(lambda x: any('Cinéma' in tag or 'Cinema' in tag for tag in x))
        df['cat_danse'] = tags.apply(lambda x: 'Danse' in x)
        df['cat_conference'] = tags.apply(lambda x: any('Conférence' in tag or 'Conference' in tag for tag in x))
        df['cat_visite'] = tags.apply(lambda x: 'Visite' in x)
        df['cat_autre'] = ~(df['cat_concert'] | df['cat_exposition'] | df['cat_theatre'] | 
                           df['cat_atelier'] | df['cat_musee'] | df['cat_festival'] | 
                           df['cat_spectacle'] | df['cat_cinema'] | df['cat_danse'] | 
                           df['cat_conference'] | df['cat_visite'])
    
    # Audience
    df[['age_min', 'age_max']] = df['audience'].apply(lambda x: pd.Series(extract_age_range(x)))
    audience_cats = df['audience'].apply(extract_audience_categories)
    for key in ['enfants', 'jeunes', 'adultes', 'tout_petits', 'tout_public']:
        df[key] = audience_cats.apply(lambda x: x[key])
    
    # Prix
    df[['price_min', 'price_max']] = df['price_detail'].apply(lambda x: pd.Series(parse_price_detail(x)))
    df['price_avg'] = df.apply(lambda row: (row['price_min'] + row['price_max']) / 2
                                if pd.notna(row['price_min']) and pd.notna(row['price_max']) 
                                else None, axis=1)
    
    # Booléens
    df['event_indoor'] = df.get('event_indoor', 1).fillna(1).astype(bool)
    df['event_pets_allowed'] = df.get('event_pets_allowed', 0).fillna(0).astype(bool)
    df['pmr'] = df.get('pmr').astype(bool) if 'pmr' in df.columns else False
    df['deaf'] = df.get('deaf').astype(bool) if 'deaf' in df.columns else False
    df['blind'] = df.get('blind').astype(bool) if 'blind' in df.columns else False
    df['mental'] = df.get('mental').astype(bool) if 'mental' in df.columns else False
    df['sign_language'] = df.get('sign_language').astype(bool) if 'sign_language' in df.columns else False
    
    logger.info(f"Nettoyage terminé : {len(df)} événements conservés")
    return df

def insert_into_db(df):
    """Insère les données nettoyées dans PostgreSQL"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Supprimer les anciens événements passés
        cur.execute("DELETE FROM activites WHERE date_end < CURRENT_DATE")
        logger.info(f"Événements passés supprimés : {cur.rowcount}")
        
        # Préparer les données pour l'insertion
        columns = [
            'event_id', 'title', 'lead_text', 'url', 'url_event',
            'date_start', 'date_end', 'date_description', 'occurrences',
            'lat', 'lon', 'address_name', 'address_street', 'address_zipcode',
            'price_type', 'price_min', 'price_max', 'price_avg',
            'access_type', 'event_indoor', 'event_pets_allowed', 'pmr',
            'age_min', 'age_max', 'enfants', 'jeunes', 'adultes', 'tout_petits', 'tout_public',
            'deaf', 'blind', 'mental', 'sign_language',
            'cat_concert', 'cat_exposition', 'cat_theatre', 'cat_atelier', 'cat_musee',
            'cat_festival', 'cat_spectacle', 'cat_cinema', 'cat_danse', 'cat_conference',
            'cat_visite', 'cat_autre',
            'rank', 'weight'
        ]
        
        # Créer la liste de valeurs
        values = []
        for _, row in df.iterrows():
            value_tuple = tuple([
                row.get(col) if pd.notna(row.get(col)) else None 
                for col in columns
            ])
            values.append(value_tuple)
        
        # Insertion avec ON CONFLICT pour gérer les doublons
        insert_query = f"""
            INSERT INTO activites ({', '.join(columns)})
            VALUES %s
            ON CONFLICT (event_id) DO UPDATE SET
                title = EXCLUDED.title,
                date_end = EXCLUDED.date_end,
                updated_at = CURRENT_TIMESTAMP
        """
        
        execute_values(cur, insert_query, values)
        conn.commit()
        
        logger.info(f"✅ {len(values)} événements insérés/mis à jour dans la base de données")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Erreur lors de l'insertion : {e}")
        raise
    finally:
        cur.close()
        conn.close()

def main():
    """Fonction principale"""
    try:
        # Collecter les données
        df = collect_data_from_api()
        
        # Nettoyer les données
        df_clean = clean_data(df)
        
        # Insérer dans la base de données
        insert_into_db(df_clean)
        
        logger.info("✅ Pipeline terminée avec succès!")
        
    except Exception as e:
        logger.error(f"❌ Erreur dans la pipeline : {e}")
        raise

if __name__ == "__main__":
    main()
