// Effet parallaxe
window.addEventListener("scroll", function () {
  const scrolled = window.pageYOffset;
  const parallaxes = document.querySelectorAll(
    ".parallax-bg-projet, .parallax-bg-carte, .parallax-bg-contact"
  );
  parallaxes.forEach((el) => {
    el.style.transform = `translateY(${scrolled * 0.5}px)`;
  });
});

// Bouton retour en haut
const btnHaut = document.getElementById("button-top");

window.addEventListener("scroll", function () {
  if (window.pageYOffset > 300) {
    btnHaut.classList.add("visible");
  } else {
    btnHaut.classList.remove("visible");
  }
});

btnHaut.addEventListener("click", function () {
  window.scrollTo({
    top: 0,
    behavior: "smooth",
  });
});

// Menu déroulant
const logo = document.querySelector(".logo");
const menuDeroulant = document.getElementById("menuDeroulant");
const fermerMenu = document.querySelector(".fermer-menu");

if (logo && menuDeroulant) {
  let menuOuvert = false;

  logo.addEventListener("click", function (e) {
    e.preventDefault();

    if (menuOuvert) {
      menuDeroulant.classList.remove("ouvert");
      setTimeout(() => {
        menuDeroulant.style.display = "none";
      }, 300);
      menuOuvert = false;
    } else {
      menuDeroulant.style.display = "block";
      void menuDeroulant.offsetWidth;
      menuDeroulant.classList.add("ouvert");
      menuOuvert = true;
    }
  });

  fermerMenu.addEventListener("click", function () {
    menuDeroulant.classList.remove("ouvert");
    setTimeout(() => {
      menuDeroulant.style.display = "none";
    }, 300);
    menuOuvert = false;
  });

  menuDeroulant.addEventListener("click", function (e) {
    if (e.target === menuDeroulant) {
      menuDeroulant.classList.remove("ouvert");
      setTimeout(() => {
        menuDeroulant.style.display = "none";
      }, 300);
      menuOuvert = false;
    }
  });
}

// Carte interactive
let carte;
let marqueurs = [];

function initialiserCarte() {
  console.log("Initialisation de la carte...");

  // Créer la carte
  carte = L.map("map", {
    center: [48.8566, 2.3522],
    zoom: 12,
    scrollWheelZoom: false,
    zoomControl: true,
    dragging: true,
  });
  // Ajouter la couche OpenStreetMap
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap contributors",
  }).addTo(carte);

  // Charger les activités
  chargerActivites();
}

async function chargerActivites(dateSelectionnee, categorieSelectionnee) {
  // 1. Construction de l'URL
  let url = `/api/activites?`;

  if (dateSelectionnee) {
    url += `date=${dateSelectionnee}&`;
  }
  if (categorieSelectionnee && categorieSelectionnee !== "tous") {
    url += `category=${categorieSelectionnee}`;
  }
  // c'est ici que je fais ma requête : j'appelle l'URL de mon API en lui donnant les filtres
  try {
    // 2. Récupération des données
    const response = await fetch(url);
    const activites = await response.json();

    // 3. Affichage des marqueurs
    afficherMarqueurs(activites);
    console.log(`${activites.length} activités chargées`);

    // 4. MISE À JOUR DU TEXTE (C'est ici que ça se passe) 👇
    const elementStatut = document.getElementById("statut-activites");

    if (elementStatut) {
      if (activites.length === 0) {
        elementStatut.innerText =
          "Aucune activité trouvée pour cette recherche.";
      } else if (activites.length === 1) {
        elementStatut.innerText = "1 activité trouvée";
      } else {
        elementStatut.innerText = `${activites.length} activités trouvées !`;
      }
    }
  } catch (error) {
    console.error("Erreur chargement:", error);
    // Afficher l'erreur à l'utilisateur
    const elementStatut = document.getElementById("statut-activites");
    if (elementStatut) {
      elementStatut.innerText = "Erreur de chargement des données.";
      elementStatut.style.color = "red"; // Petit feedback visuel en cas d'erreur
    }
  }
}

function afficherMarqueurs(activites) {
  // Supprimer les anciens marqueurs
  if (marqueurs.length > 0) {
    marqueurs.forEach((marqueur) => carte.removeLayer(marqueur));
    marqueurs = [];
  }

  // Ajouter les nouveaux marqueurs
  activites.forEach((activite) => {
    const couleur = "var(--rose-fonce)";

    const marqueur = L.circleMarker(activite.position, {
      radius: 8,
      fillColor: couleur,
      color: "#fff",
      weight: 2,
      fillOpacity: 0.8,
    }).addTo(carte);

    // Popup avec informations
    marqueur.bindPopup(`
      <div style="min-width: 200px;">
        <h3 style="margin: 0 0 10px 0; color: #333;">${activite.nom}</h3>
        <p style="margin: 5px 0;"><strong>📍 ${activite.lieu}</strong></p>
        <p style="margin: 5px 0;">💰 ${activite.prix}</p>
        <p style="margin: 5px 0;">${activite.description}</p>
        ${
          activite.url !== "#"
            ? `<a href="${activite.url}" target="_blank" style="color: var(--bleu-fonce);">Plus d'informations</a>`
            : ""
        }
      </div>
    `);

    marqueurs.push(marqueur);
  });

  // Ajuster la vue si on a des marqueurs
  if (activites.length > 0) {
    const groupe = new L.featureGroup(marqueurs);
    carte.fitBounds(groupe.getBounds().pad(0.1));
  }
}

// Démarrer la carte quand la page est prête
document.addEventListener("DOMContentLoaded", function () {
  if (document.getElementById("map")) {
    console.log("Carte détectée, initialisation...");
    initialiserCarte();
  }
});
