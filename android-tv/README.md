# Android TV : allègement réversible et accueil Nature Home

Outil à lancer **depuis un ordi branché sur le même Wi-Fi que la télé**. Il faut Python 3.7+ et `adb` (Android SDK Platform-Tools).

## 0. Préparer la télé

1. Paramètres > Système > À propos : cliquer 7 fois sur « Build » (« Version du système » selon la marque).
2. Paramètres > Système > Options pour les développeurs : activer « Débogage USB » et, s'il existe, « Débogage réseau » / « Débogage sans fil ».

## 1. Trouver et connecter

```sh
python3 tvtool.py discover                 # balaye le réseau local (port 5555 + mDNS)
python3 tvtool.py connect 192.168.1.50     # accepter « Autoriser le débogage ? » sur la télé
# Android 11+ en « Débogage sans fil » seulement :
python3 tvtool.py pair 192.168.1.50:37123 123456   # puis connect sur le port affiché
```

## 2. Sauvegarder (obligatoire, sinon rien n'est modifiable)

```sh
python3 tvtool.py backup
```

Le dossier `backups/<marque>-<modèle>-<date>/` contient :
- la liste des paquets (actifs, désactivés, système, tiers) ;
- les réglages `global`, `secure`, `system` ;
- l'accueil par défaut ;
- les propriétés système ;
- la capture `screens/00-avant.png`.

## 3. Alléger

```sh
python3 tvtool.py audit        # liste seulement, ne touche à rien
python3 tvtool.py debloat      # interactif
```

- **Pub / télémétrie** : la liste est affichée en bloc, avec Oui par défaut ; tu peux aussi choisir paquet par paquet.
- **Fonctions et applis que tu pourrais utiliser** : une question par élément, avec Non par défaut. C'est le cas de l'Assistant (micro de la télécommande), de Chromecast, du mode Ambiant, des Chaînes en direct, de YouTube, de Netflix, etc.
- **Paquets fabricant au nom évocateur** : une question pour chacun, avec Non par défaut. Ces paquets sont désactivés un par un, avec un contrôle après chaque désactivation et un retour arrière automatique si l'interface système tombe.
- **Animations** : option pour passer leur échelle à 0,5.

Ce que l'outil garantit :
- **Rien n'est désinstallé.** Les paquets sont désactivés avec `pm disable-user --user 0`, ce qui reste réversible.
- **Paquets protégés.** Certains paquets ne sont jamais proposés : `systemui`, Réglages, services Google Play, Play Store, clavier, entrées TV/HDMI/tuner, Wi-Fi/Bluetooth, mises à jour, couches matérielles MediaTek/Amlogic/Realtek, etc.
- **Contrôle après chaque série.** L'outil relit l'état sur la télé, vérifie que l'interface système tourne et prend une capture d'écran.

## 4. Installer Nature Home

```sh
python3 tvtool.py launcher                       # télécharge l'APK de la release « naturehome-latest »
python3 tvtool.py launcher --apk NatureHome.apk  # ou APK local (artefact de l'onglet Actions)
```

Étapes :
1. Installation de l'APK, puis vérification qu'il s'affiche bien au premier plan.
2. Choix des applis du dock.
3. Définition comme écran d'accueil, puis test réel de la touche Accueil. Sur Google TV, l'accueil d'origine garde souvent la touche Accueil. L'outil propose alors de le **désactiver** (réversible) et refait le test. En cas d'échec, l'accueil d'origine est réactivé.

Sur la télé :
- OK : ouvre l'appli.
- Appui long sur OK, ou touche Menu : déplacer ou retirer la tuile.
- « Toutes les applis » : en ajouter au dock.
- La tuile « Réglages » reste toujours disponible.

```sh
python3 tvtool.py dock                     # rechoisir le dock
python3 tvtool.py dock --set com.netflix.ninja,com.google.android.youtube.tv
```

## 5. Fonds d'écran nature

```sh
python3 tvtool.py wallpapers --fetch 30 --interval 120   # 30 photos Wikimedia Commons, rotation 2 min
python3 tvtool.py wallpapers --folder ~/Images/Nature    # ou tes propres photos
```

- Sans photo, Nature Home affiche ses propres paysages générés : aube alpine, forêt boréale, aurore, désert, lac glaciaire.
- L'outil vérifie dans le journal de l'appli qu'elle lit bien les photos envoyées. Sinon, il bascule vers `/sdcard/Pictures/NatureHome`.

## 6. Captures et restauration

```sh
python3 tvtool.py screenshot nom           # capture dans backups/…/screens/
python3 tvtool.py restore                  # remet tout comme dans la sauvegarde, puis compare
sh backups/<dossier>/restore.sh            # même chose sans Python (restore.bat sous Windows)
```

`restore.sh` et `restore.bat` sont régénérés après chaque modification. Ils font, dans l'ordre :
1. réactivation des paquets ;
2. remise de l'accueil d'origine ;
3. remise des réglages d'animation ;
4. retrait de Nature Home.

## Le launcher

`launcher/` est écrit en Java pur, sans AndroidX : l'APK reste petit et démarre vite.
- Il est compilé par `.github/workflows/naturehome.yml`.
- La clé de signature `naturehome.keystore` est volontairement versionnée et non secrète, pour que `adb install -r` mette à jour l'appli sans la désinstaller.
- Réglages par adb : `am start -n ca.maison.naturehome/.ConfigActivity --es dock "a,b" --ei interval 120 --ez next true`. Cette activité est protégée par la permission `DUMP`, que seul le shell adb détient.

## Limites connues

- `catalog.json` est établi de mémoire, **sans doc constructeur consultée** ; l'outil ne propose que ce qui est réellement installé.
- Pas de liste nominative des paquets pub propres à chaque fabricant (TCL, Sony, Philips, Hisense…) : ils sont repérés par leur nom. Leur fonction est une **hypothèse** jusqu'à vérification à l'écran.
- `cmd package set-home-activity` et `query-activities` n'existent pas sur les très vieilles versions d'Android TV. L'outil le signale.
- Une mise à jour système peut réactiver des paquets désactivés : relancer `debloat` après une mise à jour.
