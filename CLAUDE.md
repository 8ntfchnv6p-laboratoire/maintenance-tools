# CLAUDE.md

Consignes pour les assistants IA (Claude Code et autres) travaillant dans ce
dépôt.

## Ce qu'est ce dépôt

`maintenance-tools` est une petite boîte à outils pour le **diagnostic terrain
en maintenance industrielle**. Les utilisateurs visés sont des
électromécaniciens/techniciens de terrain qui utilisent Claude pour dépanner des
machines — automates (PLC), variateurs de fréquence (*variateurs*/VFD), relais
de sécurité et réseaux de terrain industriels (fieldbus) — directement à l'atelier.

Le domaine est **francophone (fr-CA)** : les machines référencées sont des lignes
de travail du bois (HOMAG, Holzma, Biesse, SCM), les variateurs sont des
KEB / Lenze / IndraDrive, et tout le texte destiné à l'utilisateur est en
**français**. Conserve cette langue et ce vocabulaire dans tout contenu visible
que tu ajoutes ou modifies.

## Structure du dépôt

Le dépôt est volontairement minuscule et plat — pas de système de build, pas de
dépendances, pas de gestionnaire de paquets.

```
.
├── README.md                  # Titre stub sur une seule ligne
└── diagnostic-template.html   # L'outil réel (autonome, ~650 lignes)
```

### `diagnostic-template.html`

Une **page HTML unique et autonome** — aucun bundle JS/CSS externe, aucune étape
de build. On l'ouvre directement dans un navigateur (`file://`) et elle
fonctionne. C'est un **constructeur de prompt structuré** : le technicien
remplit un formulaire décrivant une panne machine, et la page assemble un prompt
de diagnostic Markdown bien formé à coller dans Claude.

Structure du fichier (tout est en inline) :
- **Bloc `<style>`** — un thème sombre « terminal/instrument » piloté par des
  variables CSS dans `:root` (`--bg`, `--surface`, `--accent: #f59e0b` ambre,
  police mono JetBrains Mono, police sans IBM Plex Sans). Les polices sont
  chargées depuis Google Fonts via `@import`.
- **Sections du formulaire** — numérotées `①`–`⑦`, chacune une carte `.section` :
  1. Identification (machine, section, axe/organe, variateur/PLC, mode contrôle)
  2. Symptôme (+ fréquence, depuis quand)
  3. Codes erreur
  4. Contexte
  5. Déjà vérifié (marqué *critique* — plus c'est rempli, moins Claude redemande)
  6. Sections optionnelles à bascule : **Réseau bus**, **Après intervention**,
     **Photos / Captures**
  7. Ce que j'attends (par défaut : top-3 causes classées, points de mesure,
     E/S & bits de diagnostic, procédure de correction)
- **Bloc `<script>`** — JS vanille pur, sans framework. Fonctions clés :
  - `buildPrompt()` — lit chaque champ par son `id` et concatène une chaîne de
    prompt Markdown. **C'est le cœur de l'outil.**
  - `copyPrompt()` — copie le prompt assemblé dans le presse-papiers (avec un
    repli `document.execCommand('copy')` pour les contextes non sécurisés).
  - `saveLocal()` / `loadLocal()` — sauvegardent un brouillon dans
    `localStorage` sous la clé `diag-draft`.
  - `clearAll()` / `toggleVariant()` — réinitialisent et affichent/masquent les
    sections optionnelles.

Une **bannière de sécurité LOTO** (🔒 *Consignation · Vérification absence
d'énergie · Cadenas personnel*) se trouve en haut de la page. Elle reflète une
convention de sécurité transversale au domaine : ne jamais retirer ni minimiser
les rappels de consignation (lock-out/tag-out).

## Conventions clés

- **Zéro build, zéro dépendance.** Tout tient dans un seul fichier HTML.
  N'introduis pas de bundler, de framework, de `package.json` ou de dépendance
  npm sauf demande explicite — cela casserait le modèle « on ouvre le fichier et
  ça marche ».
- **Garder l'autonomie.** Tout nouveau comportement va dans les blocs inline
  `<style>` / `<script>` existants. La seule ressource externe acceptée est
  Google Fonts.
- **Contrat champ ↔ constructeur.** Chaque contrôle du formulaire a un `id`
  stable. Si tu ajoutes un champ, tu dois (a) lui donner un `id`, (b) le lire
  dans `buildPrompt()`, et (c) ajouter cet `id` au tableau de `getFormData()`
  pour que la sauvegarde/chargement du brouillon continue de fonctionner. Ces
  trois endroits doivent rester synchronisés.
- **Français, fr-CA.** Tous les libellés, placeholders, boutons et le texte de
  prompt généré sont en français. Les dates utilisent
  `toLocaleDateString('fr-CA')`. Respecte cela.
- **Thème via variables CSS.** Réutilise les propriétés personnalisées de
  `:root` pour les couleurs plutôt que de coder les valeurs hexadécimales en
  dur, afin de garder un rendu instrument cohérent.
- **La sécurité d'abord.** Préserve la bannière LOTO et tout cadre de sécurité
  dans les prompts générés.

## Flux de développement

- **Lancer / prévisualiser :** ouvrir `diagnostic-template.html` dans n'importe
  quel navigateur. Aucun serveur requis. Pour vérifier les changements JS,
  utiliser la console des outils de développement du navigateur.
- **Tests :** il n'y a pas de suite de tests automatisée. Vérifier manuellement :
  remplir les champs → *Copier le prompt* → confirmer que le Markdown assemblé
  est bien formé ; basculer les sections optionnelles ; sauvegarder puis
  recharger un brouillon pour confirmer l'aller-retour `localStorage`.
- **Aucun CI / linter** n'est configuré. Garder le HTML valide et le JS sans
  framework.

## Conventions Git & branches

- Branche par défaut : `main`.
- Travailler sur une branche de fonctionnalité, committer avec des messages
  clairs et descriptifs, et pousser avec `git push -u origin <branche>`.
- **Ne pas** ouvrir de pull request sauf demande explicite.

## Skills Claude associés

Cet environnement fournit des skills de domaine qui s'accordent avec cet outil —
p. ex. des skills de diagnostic terrain pour les relais de sécurité
Allen-Bradley Guardmaster (MSR138DP, MSR210P, GSR 440R), le dépannage fieldbus
(Profinet/Profibus/Modbus/EtherNet-IP, EtherCAT/CANopen/IO-Link), le Texte
Structuré CODESYS/TwinCAT, le KRL KUKA, les lignes de placage HOMAG et la lecture
de schémas électriques. La structure de prompt de `diagnostic-template.html`
(identification → symptôme → codes → contexte → déjà vérifié → attente) reflète
ce que ces skills attendent en entrée. Pour aider un utilisateur sur une panne
terrain, préfère invoquer le skill pertinent et recueillir les mêmes champs que
ce template collecte.
