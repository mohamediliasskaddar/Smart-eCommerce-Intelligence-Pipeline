Étape 1 : Scraping de données – Agents A2A 
Objectif : Extraire automatiquement les données produits depuis des plateformes 
Shopify/WooCommerce. 
Concepts: 
  Agent A2A (Agent-to-Agent) : composant logiciel autonome, chargé de se 
connecter à un site, de lire ses pages et d’en extraire des données spécifiques. 
  Scraping : technique d’automatisation de lecture de contenu HTML à partir de 
sites web. 
  Crawling : navigation systématique sur plusieurs pages d’un site. 
Outils :  
● requests, BeautifulSoup: pour le scraping statique. 
● Selenium ou Playwright: pour gérer JavaScript et les actions dynamiques. 
● Scrapy: pour des projets de scraping structurés. 
● Shopify : données disponibles via Storefront API 
● WooCommerce : accès via REST API WooCommerce 
Données extraites : 
● Titre,  prix,  disponibilité,  note moyenne, description, vendeur, catégorie, 
géographie, trafic… 
Étape 2 : Analyse et sélection des Top-K produits 
Objectif : Identifier les produits les plus attractifs selon des critères définis (ex : 
note, prix, ventes, disponibilité). 
Concepts :  
● Top-K selection : sélectionner les K meilleurs éléments selon un score. 
1 
● Scoring : attribuer un score synthétique à chaque produit en fonction de 
plusieurs attributs. 
● Classement  des shops avec leurs produits phare et géographie 
● Normalisation / pondération : pour combiner plusieurs métriques (note, 
ventes, prix, etc.) 
● … 
● … 
Outils :  
● pandas, numpy pour la préparation des données 
● scikit-learn pour le clustering ou la régression 
● xgboost, lightgbm pour la prédiction du succès potentiel 
● Algorithmes : RandomForest, KMeans, DBScan, algorithms régles 
d’association, PCA pour la visualization … 