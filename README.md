# maintenance-tools

Outils de terrain pour la maintenance industrielle — électromécanicien.

## Atelier Diagnostic — `index.html`

Application universelle qui construit des **prompts de diagnostic de terrain de haute qualité**
à partir de ce que tu observes réellement devant la machine.

Le principe : ce qui fait la qualité d'une réponse, ce n'est pas la formulation de la question,
c'est la **densité d'informations exploitables** qu'elle contient. L'appli force cette densité,
la mesure, et signale ce qui manque avant que tu envoies.

### Ouvrir

Fichier unique, sans dépendance, sans réseau : ouvre `index.html` dans n'importe quel navigateur
(PC, tablette, téléphone). Sur téléphone, « Ajouter à l'écran d'accueil » suffit à l'avoir sous la main
dans l'atelier, y compris hors connexion.

### Ce que ça fait

**8 objectifs** — la structure et le format de réponse demandé changent complètement selon le besoin :

| Objectif | Usage |
|---|---|
| Diagnostic rapide | Machine à l'arrêt, trouver et redémarrer |
| Panne intermittente | Défaut fuyant : méthode pour le piéger, plan de surveillance |
| Lecture de schéma | Tracer un circuit, renvois de folios, équation de commande |
| Code automate / robot | Analyser, corriger ou écrire du programme |
| Procédure d'intervention | Gamme pas à pas, consignation, critères d'acceptation |
| Rapport d'intervention | Compte-rendu prêt pour la GMAO |
| Pièce de rechange | Identification, compatibilité, équivalences |
| Comprendre le principe | Montée en compétence sur la technologie |

**11 domaines techniques** — chacun charge son vocabulaire, ses champs et sa checklist :
variateur / servo, automate, réseau et bus de terrain, sécurité fonctionnelle, électrique / puissance,
capteur / actionneur, mécanique et fluides, robot, IHM / logiciel machine, qualité / réglage, transversal.

**Checklist de mesures guidée** — pour chaque domaine, les points à relever (tension bus DC, isolement,
terminaison de bus, bornes du relais de sécurité, jeu au comparateur…). Tu coches, tu notes la valeur :
elle part dans le prompt en tant que **fait établi**, avec la consigne explicite de ne pas te la redemander.

**Score de qualité /100** — pondéré par ce qui change vraiment une réponse (symptôme détaillé 20,
relevés 16, codes 15…). Les manques s'affichent en pastilles cliquables qui te renvoient à la bonne section.

**Contraintes terrain** — outillage réellement disponible, pièces, temps, accès, documentation :
les propositions restent exécutables ici et maintenant.

**Règles de réponse** — valeurs chiffrées et bornes exigées, séparation fait / déduction / hypothèse,
questions au lieu de suppositions, rappel du risque et de la consignation avant chaque test,
pas de remplacement de composant sans test discriminant.

### Utilisation

1. Choisis l'objectif et le domaine.
2. Remplis en remontant le score : symptôme, codes, relevés d'abord.
3. `Aperçu` pour relire, `Copier` (ou `Ctrl/⌘ + Entrée`) pour coller dans Claude.
4. Joins ensuite tes photos (schéma, afficheur, plaque moteur) directement dans la conversation.

Bouton `Exemple rempli` : un cas complet noté 100/100 pour voir le niveau de détail visé.

### Données

Tout reste sur l'appareil (`localStorage`) : brouillons nommés, 20 derniers prompts générés,
sauvegarde automatique du formulaire en cours, machines déjà saisies. Aucun envoi, aucun compte.

## `diagnostic-template.html`

Première version, formulaire court à copier-coller. Conservée pour les cas où l'on veut aller au plus simple.

---

> L'application prépare une demande d'analyse. Elle ne remplace ni le schéma constructeur,
> ni la procédure, ni la consignation. Le diagnostic et l'intervention restent sous la
> responsabilité de l'intervenant.
