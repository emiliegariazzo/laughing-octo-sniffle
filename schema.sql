-- Extensions nécessaires pour le calcul de distances géographiques
CREATE EXTENSION IF NOT EXISTS cube;
CREATE EXTENSION IF NOT EXISTS earthdistance;

-- Schéma PostgreSQL pour les activités culturelles parisiennes
CREATE TABLE IF NOT EXISTS activites (
    -- Identifiants
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(50) UNIQUE NOT NULL,
    
    -- Informations générales
    title TEXT NOT NULL,
    lead_text TEXT,
    url TEXT,
    url_event TEXT,
    
    -- Dates
    date_start TIMESTAMP WITH TIME ZONE,
    date_end TIMESTAMP WITH TIME ZONE,
    date_description TEXT,
    occurrences TEXT,
    
    -- Localisation
    lat DECIMAL(10, 8),
    lon DECIMAL(11, 8),
    address_name TEXT,
    address_street TEXT,
    address_zipcode VARCHAR(5),
    
    -- Prix
    price_type VARCHAR(50),
    price_min DECIMAL(10, 2),
    price_max DECIMAL(10, 2),
    price_avg DECIMAL(10, 2),
    
    -- Métadonnées
    access_type VARCHAR(50),
    event_indoor BOOLEAN DEFAULT true,
    event_pets_allowed BOOLEAN DEFAULT false,
    pmr BOOLEAN,
    
    -- Public
    age_min INTEGER,
    age_max INTEGER,
    enfants BOOLEAN DEFAULT false,
    jeunes BOOLEAN DEFAULT false,
    adultes BOOLEAN DEFAULT false,
    tout_petits BOOLEAN DEFAULT false,
    tout_public BOOLEAN DEFAULT false,
    
    -- Accessibilité
    deaf BOOLEAN,
    blind BOOLEAN,
    mental BOOLEAN,
    sign_language BOOLEAN,
    
    -- Catégories (en colonnes booléennes pour simplifier les requêtes)
    cat_concert BOOLEAN DEFAULT false,
    cat_exposition BOOLEAN DEFAULT false,
    cat_theatre BOOLEAN DEFAULT false,
    cat_atelier BOOLEAN DEFAULT false,
    cat_musee BOOLEAN DEFAULT false,
    cat_festival BOOLEAN DEFAULT false,
    cat_spectacle BOOLEAN DEFAULT false,
    cat_cinema BOOLEAN DEFAULT false,
    cat_danse BOOLEAN DEFAULT false,
    cat_conference BOOLEAN DEFAULT false,
    cat_visite BOOLEAN DEFAULT false,
    cat_autre BOOLEAN DEFAULT false,
    
    -- Métadonnées techniques
    rank DECIMAL(10, 2),
    weight DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour optimiser les requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_date_end ON activites(date_end);
CREATE INDEX IF NOT EXISTS idx_zipcode ON activites(address_zipcode);
CREATE INDEX IF NOT EXISTS idx_price_type ON activites(price_type);
CREATE INDEX IF NOT EXISTS idx_lat_lon ON activites(lat, lon);

-- Index pour les recherches géographiques
CREATE INDEX IF NOT EXISTS idx_geo ON activites USING gist(ll_to_earth(lat, lon));

-- Fonction pour mettre à jour automatiquement updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger pour mettre à jour automatiquement updated_at
CREATE TRIGGER update_activites_updated_at 
    BEFORE UPDATE ON activites 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Vue pour les activités du jour
CREATE OR REPLACE VIEW activites_aujourdhui AS
SELECT *
FROM activites
WHERE date_end >= CURRENT_DATE
  AND date_end < CURRENT_DATE + INTERVAL '1 day'
ORDER BY date_start;

-- Vue pour les activités futures
CREATE OR REPLACE VIEW activites_futures AS
SELECT *
FROM activites
WHERE date_end >= CURRENT_DATE
ORDER BY date_start;
