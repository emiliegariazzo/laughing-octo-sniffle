import os
from flask import Flask, render_template, jsonify, request, send_from_directory
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration de la base de données
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        logger.error(f"Erreur de connexion DB: {e}")
        return None

# --- NOUVELLE FONCTION DE RECHERCHE FILTRÉE ---
def get_filtered_activities(filters):
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        
        # Requête de base : on prend tout ce qui n'est pas fini
        query = """
            SELECT *
            FROM activites
            WHERE 1=1
        """
        params = []

        # 1. Filtre par date
        # Si une date est fournie, on cherche les événements actifs à cette date
        target_date = filters.get('date')
        if target_date:
            query += " AND date_start <= %s AND date_end >= %s"
            # L'événement a commencé avant ou le jour même ET finit après ou le jour même
            params.append(target_date)
            params.append(target_date)
        else:
            # Par défaut : événements futurs ou en cours (aujourd'hui)
            query += " AND date_end >= CURRENT_DATE"

        # 2. Filtre par Catégorie
        category = filters.get('category')
        if category and category != 'all':
            # On map le nom du filtre vers la colonne booléenne de la DB
            cat_map = {
                'concert': 'cat_concert',
                'expo': 'cat_exposition',
                'theatre': 'cat_theatre',
                'musee': 'cat_musee',
                'spectacle': 'cat_spectacle',
                'cinema': 'cat_cinema',
                'danse': 'cat_danse',
                'enfant': 'enfants', # Note: 'enfants' est une colonne audience, pas cat_
                'gratuit': 'price_type' # Cas spécial
            }
            
            if category == 'gratuit':
                query += " AND (price_type = 'gratuit' OR price_type = 'gratuit sous conditions')"
            elif category in cat_map:
                col_name = cat_map[category]
                query += f" AND {col_name} = TRUE"

        # 3. Filtre par arrondissement
        zipcode = filters.get('zipcode')
        if zipcode:
            query += " AND address_zipcode = %s"
            params.append(zipcode)

        # Tri par date de début
        query += " ORDER BY date_start ASC LIMIT 5000"

        cur.execute(query, tuple(params))
        results = cur.fetchall()
        
        # Formatage pour le frontend
        activites = []
        for row in results:
            coords = [48.8566, 2.3522]
            if row['lat'] and row['lon']:
                coords = [float(row['lat']), float(row['lon'])]
            
            # Reconstruction des catégories pour l'affichage
            categories_display = []
            if row['cat_concert']: categories_display.append('Concert')
            if row['cat_exposition']: categories_display.append('Exposition')
            if row['cat_theatre']: categories_display.append('Théâtre')
            if row['cat_musee']: categories_display.append('Musée')
            if row['cat_spectacle']: categories_display.append('Spectacle')
            if row['cat_cinema']: categories_display.append('Cinéma')
            if row['cat_danse']: categories_display.append('Danse')

            # Gestion du prix
            if row['price_type'] and 'gratuit' in row['price_type'].lower():
                prix_display = 'Gratuit'
            elif row['price_min']:
                prix_display = f"{row['price_min']}€"
            else:
                prix_display = "Non spécifié"

            activite = {
                'id': row['event_id'],
                'nom': row['title'],
                'description': row['lead_text'],
                'position': coords,
                'lieu': row['address_name'],
                'date': row['date_start'].isoformat() if row['date_start'] else '',
                'date_fin': row['date_end'].isoformat() if row['date_end'] else '',
                'prix': prix_display,
                'url': row['url_event'] or row['url'],
                # 'image': row.get('cover_url')
                'categories': categories_display
            }
            activites.append(activite)
            
        return activites

    except Exception as e:
        logger.error(f"Erreur SQL : {e}")
        return []
    finally:
        conn.close()

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('EG_web_carte.html')

@app.route('/projet')
def projet():
    return render_template('EG_web_projet.html')

@app.route('/contact')
def contact():
    return render_template('EG_web_contact.html')

@app.route('/api/activites')
def api_activites():
    """
    API Principale appellée par le JS.
    Accepte des paramètres URL : ?date=2026-01-05&category=concert
    """
    filters = {
        'date': request.args.get('date'), # Format attendu YYYY-MM-DD
        'category': request.args.get('category'),
        'zipcode': request.args.get('zipcode') # ajouter les filtres possibles
    }
    
    data = get_filtered_activities(filters)
    return jsonify(data)

# Route statique pour servir les fichiers JS/CSS si besoin
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    # Vérification DB au démarrage
    if not DATABASE_URL:
        print("⚠️  DATABASE_URL manquante. Assurez-vous d'avoir sourcé le .env ou lancé via Docker.")
    
    app.run(debug=True, host='0.0.0.0', port=5000)