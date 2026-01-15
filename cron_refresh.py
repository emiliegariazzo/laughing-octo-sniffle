"""
Script pour rafraîchir automatiquement les données
À exécuter via un Cron Job sur Render (service séparé)
"""

import logging
from collect_to_db import main as collect_main

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("🔄 Démarrage du rafraîchissement automatique des données")
    
    try:
        collect_main()
        logger.info("✅ Rafraîchissement terminé avec succès")
    except Exception as e:
        logger.error(f"❌ Erreur lors du rafraîchissement : {e}")
        raise
