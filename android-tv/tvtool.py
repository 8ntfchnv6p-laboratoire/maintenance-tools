#!/usr/bin/env python3
"""
tvtool.py — Allègement réversible d'une Android TV par ADB + installation de Nature Home.

Principes :
  * Rien n'est désinstallé : les paquets sont désactivés (pm disable-user), réactivables.
  * Aucune modification sans sauvegarde préalable de l'état de la télé.
  * Chaque modification est journalisée ; restore.sh / restore.bat sont régénérés à chaque fois.
  * Chaque étape est vérifiée (état relu sur la télé + capture d'écran).

Ordre conseillé :
  python3 tvtool.py discover          # trouve la télé sur le Wi-Fi
  python3 tvtool.py connect 192.168.1.50
  python3 tvtool.py backup
  python3 tvtool.py debloat           # interactif : demande avant chaque appli/fonction utile
  python3 tvtool.py launcher          # installe Nature Home, choix du dock, accueil par défaut
  python3 tvtool.py wallpapers --fetch 30
  python3 tvtool.py restore           # tout remettre comme avant
"""

import argparse
import concurrent.futures
import datetime
import ipaddress
import json
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE_FILE = HERE / "tv-state.json"
BACKUPS = HERE / "backups"
CATALOG_FILE = HERE / "catalog.json"
LOCAL_WALLPAPERS = HERE / "wallpapers"

LAUNCHER_PKG = "ca.maison.naturehome"
LAUNCHER_HOME = LAUNCHER_PKG + "/.MainActivity"
LAUNCHER_CONFIG = LAUNCHER_PKG + "/.ConfigActivity"
LAUNCHER_URL = ("https://github.com/8ntfchnv6p-laboratoire/maintenance-tools/"
                "releases/download/naturehome-latest/NatureHome.apk")
WALL_DIR_APP = "/sdcard/Android/data/%s/files/wallpapers" % LAUNCHER_PKG
WALL_DIR_PICTURES = "/sdcard/Pictures/NatureHome"

# Écrans d'accueil d'origine : traités par la commande « launcher », jamais par « debloat ».
STOCK_LAUNCHERS = [
    "com.google.android.apps.tv.launcherx",   # Google TV
    "com.google.android.tvlauncher",          # Android TV
    "com.google.android.leanbacklauncher",    # Android TV ancien
]

# Jamais désactivés, quelle que soit la demande (risque de télé inutilisable ou de boucle de démarrage).
PROTECTED_EXACT = {
    "android", "com.android.systemui", "com.android.settings", "com.android.tv.settings",
    "com.google.android.gms", "com.google.android.gsf", "com.android.vending",
    "com.android.shell", "com.android.packageinstaller", "com.google.android.packageinstaller",
    "com.android.permissioncontroller", "com.google.android.permissioncontroller",
    "com.android.externalstorage", "com.android.keychain", "com.android.certinstaller",
    "com.android.bluetooth", "com.android.se", "com.android.location.fused",
    "com.android.webview", "com.google.android.webview", "com.google.android.trichromelibrary",
    "com.google.android.tungsten.setupwraith", "com.google.android.tvsetup",
    "com.google.android.leanback.ime", "com.google.android.inputmethod.latin",
    "com.android.inputdevices", "com.android.wallpaperbackup", "com.android.dynsystem",
    LAUNCHER_PKG,
} | set(STOCK_LAUNCHERS)
PROTECTED_PREFIXES = (
    "com.android.providers.", "com.android.networkstack", "com.google.android.networkstack",
    "com.android.server.", "com.google.android.ext.", "com.android.inputmethod",
    "com.google.android.modulemetadata", "com.android.modulemetadata",
    "com.mediatek.", "com.droidlogic", "com.amlogic.", "com.realtek.", "com.android.internal.",
    "com.google.android.overlay.", "com.android.overlay.",
)
PROTECTED_WORDS = ("tvinput", "tuner", "hdmi", "cec", "inputmethod", "ime", "keyboard", "remote",
                   "bluetooth", "wifi", "network", "systemui", "setupwizard", "setupwraith", "provider",
                   "permission", "installer", "webview", "framework", "overlay", "launcher", "settings",
                   "ota", "update", "factory", "audio", "display", "power", "media", "drm", "widevine")

# Préfixes de paquets fabricant (la liste sert au tri, pas à décider) — [Hypothèse].
VENDOR_PREFIXES = ("com.tcl.", "com.sony.", "org.droidtv.", "com.tpvision.", "com.philips.",
                   "com.hisense.", "com.xiaomi.", "com.mitv.", "com.duokan.", "com.skyworth.",
                   "com.nvidia.", "com.toshiba.", "com.sharp.", "com.changhong.", "com.haier.",
                   "com.funai.", "com.westinghouse.", "com.onn.", "com.walmart.", "com.panasonic.",
                   "com.vizio.", "com.lg.", "com.jvc.", "com.insignia.", "com.bestbuy.", "com.motorola.")
SUSPECT_WORDS = ("ad", "ads", "advert", "advertising", "adservice", "promo", "promotion", "recommend",
                 "recommendation", "recommendations", "analytics", "statistics", "stats", "report",
                 "reporter", "feedback", "logger", "tracker", "tracking", "telemetry", "diagnostic",
                 "diagnostics", "crash", "acr", "samba", "survey", "marketing", "dataservice",
                 "userexperience", "bugreport", "usage", "partner", "store", "shop", "game", "games")

ANIM_SETTINGS = ["window_animation_scale", "transition_animation_scale", "animator_duration_scale"]

CAT_LABEL = {
    "pub": "Publicité / recommandations",
    "telemetrie": "Télémétrie / collecte de données",
    "fonction": "Fonctions que tu pourrais utiliser",
    "appli": "Applis que tu pourrais utiliser",
    "suspect": "Paquets fabricant au nom évocateur (non répertoriés)",
}


# ---------------------------------------------------------------- utilitaires

def die(msg, code=1):
    print("\n✖ " + msg, file=sys.stderr)
    sys.exit(code)


def ok(msg):
    print("  ✔ " + msg)


def warn(msg):
    print("  ⚠ " + msg)


def ask(question, default=False):
    suffix = " [O/n] " if default else " [o/N] "
    while True:
        try:
            r = input(question + suffix).strip().lower()
        except EOFError:
            return default
        if not r:
            return default
        if r in ("o", "oui", "y", "yes"):
            return True
        if r in ("n", "non", "no"):
            return False


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def now_stamp():
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def tokens(pkg):
    return set(re.split(r"[._\-]", pkg.lower()))


def is_protected(pkg):
    if pkg in PROTECTED_EXACT or pkg.startswith(PROTECTED_PREFIXES):
        return True
    t = tokens(pkg)
    return any(w in t for w in PROTECTED_WORDS)


# ---------------------------------------------------------------- ADB

class Adb:
    def __init__(self, adb_path, serial=None):
        self.adb = adb_path
        self.serial = serial

    def run(self, *args, check=False, binary=False, timeout=60):
        cmd = [self.adb] + (["-s", self.serial] if self.serial else []) + list(args)
        try:
            p = subprocess.run(cmd, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            if check:
                die("Délai dépassé : " + " ".join(cmd))
            return 124, b"" if binary else "", "timeout"
        out = p.stdout if binary else p.stdout.decode("utf-8", "replace")
        err = p.stderr.decode("utf-8", "replace")
        if check and p.returncode != 0:
            die("Échec : %s\n%s%s" % (" ".join(cmd), out if not binary else "", err))
        return p.returncode, out, err

    def sh(self, command, timeout=60):
        """Commande shell sur la télé ; renvoie stdout (stderr ajouté si non vide)."""
        rc, out, err = self.run("shell", command, timeout=timeout)
        return (out + (err if err.strip() else "")).strip()

    def state(self):
        rc, out, _ = self.run("get-state", timeout=10)
        return out.strip() if rc == 0 else None

    def prop(self, name):
        return self.sh("getprop " + name)

    def packages(self, flag=""):
        out = self.sh("pm list packages %s" % flag)
        return sorted({l[8:].strip() for l in out.splitlines() if l.startswith("package:")})

    def sdk(self):
        try:
            return int(self.prop("ro.build.version.sdk"))
        except ValueError:
            return 0

    def home_activity(self):
        out = self.sh("cmd package resolve-activity --brief -a android.intent.action.MAIN "
                      "-c android.intent.category.HOME")
        lines = [l.strip() for l in out.splitlines() if "/" in l and " " not in l.strip()]
        return lines[-1] if lines else None

    def resumed_package(self):
        out = self.sh("dumpsys activity activities | grep -E 'mResumedActivity|topResumedActivity|ResumedActivity'")
        m = re.search(r"\{[^}]*\s([\w.]+)/([\w.$]+)", out)
        return m.group(1) if m else None

    def screenshot(self, dest):
        rc, data, err = self.run("exec-out", "screencap", "-p", binary=True, timeout=30)
        if rc != 0 or not data.startswith(b"\x89PNG"):
            warn("Capture impossible (%s)" % (err.strip() or "réponse invalide"))
            return None
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return dest


def find_adb(explicit):
    p = explicit or shutil.which("adb")
    if not p:
        die("adb introuvable. Installe « Android SDK Platform-Tools » "
            "(https://developer.android.com/tools/releases/platform-tools) puis ajoute-le au PATH, "
            "ou passe --adb /chemin/vers/adb.")
    return p


def state():
    return load_json(STATE_FILE, {"serial": None, "backups": {}})


def device(args, need=True):
    st = state()
    serial = args.serial or st.get("serial")
    adb = Adb(find_adb(args.adb), serial)
    if need:
        if not serial:
            die("Aucune télé sélectionnée. Lance « discover » puis « connect <ip> ».")
        if serial.count(".") == 3 and adb.state() != "device":
            adb.run("connect", serial if ":" in serial else serial + ":5555", timeout=15)
        s = adb.state()
        if s != "device":
            die("Télé %s injoignable (état : %s). Vérifie qu'elle est allumée, sur le même Wi-Fi, "
                "et que le débogage est actif, puis « connect »." % (serial, s or "absente"))
    return adb


def current_backup(adb, required=True):
    path = state().get("backups", {}).get(adb.serial)
    if path and (Path(path) / "manifest.json").exists():
        return Path(path)
    if required:
        die("Aucune sauvegarde pour cette télé. Lance d'abord : python3 tvtool.py backup")
    return None


def shot(adb, name):
    bk = current_backup(adb, required=False)
    folder = (bk / "screens") if bk else (HERE / "screens")
    n = len(list(folder.glob("*.png"))) if folder.exists() else 0
    dest = folder / ("%02d-%s.png" % (n, name))
    if adb.screenshot(dest):
        ok("Capture : %s" % dest)
    return dest


# ---------------------------------------------------------------- journal et scripts de restauration

def journal_path(bk):
    return bk / "journal.jsonl"


def journal(bk):
    p = journal_path(bk)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def log(bk, entry, serial):
    entry = dict(entry, at=datetime.datetime.now().isoformat(timespec="seconds"))
    with journal_path(bk).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    write_restore_scripts(bk, serial)


def restore_plan(bk):
    """Actions inverses du journal, dans l'ordre d'exécution (liste de commandes shell télé)."""
    manifest = load_json(bk / "manifest.json", {})
    entries = journal(bk)
    cmds = []
    home = next((e for e in entries if e["op"] == "home"), None)
    disabled = []
    for e in entries:
        if e["op"] == "disable" and e["pkg"] not in disabled:
            disabled.append(e["pkg"])
    # Réactiver d'abord les accueils d'origine, puis rétablir l'accueil par défaut.
    for pkg in sorted(disabled, key=lambda p: p not in STOCK_LAUNCHERS):
        cmds.append("pm enable --user 0 %s" % pkg)
    original_home = (home or {}).get("before") or manifest.get("home")
    # « android/…ResolverActivity » = aucun accueil par défaut : le système choisira seul.
    if home and original_home and not original_home.startswith("android/"):
        cmds.append("cmd package set-home-activity --user 0 %s" % original_home)
    seen = set()
    for e in entries:
        if e["op"] == "setting" and (e["ns"], e["key"]) not in seen:
            seen.add((e["ns"], e["key"]))
            if e["before"] in (None, "null"):
                cmds.append("settings delete %s %s" % (e["ns"], e["key"]))
            else:
                cmds.append("settings put %s %s %s" % (e["ns"], e["key"], e["before"]))
    uninstall = any(e["op"] == "install" and not e.get("was_installed") for e in entries)
    return cmds, uninstall


def write_restore_scripts(bk, serial):
    cmds, uninstall = restore_plan(bk)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    sh = ["#!/bin/sh",
          "# Restauration de la télé à l'état de la sauvegarde %s" % bk.name,
          "# Généré par tvtool.py le %s. Usage : sh restore.sh [ip:port]" % stamp,
          'ADB="${ADB:-adb}"',
          'SERIAL="${1:-%s}"' % serial,
          'case "$SERIAL" in *.*.*.*) $ADB connect "$SERIAL" >/dev/null 2>&1 ;; esac',
          'A="$ADB -s $SERIAL"',
          'if [ "$($A get-state 2>/dev/null)" != "device" ]; then echo "Télé $SERIAL injoignable"; exit 1; fi']
    bat = ["@echo off",
           "rem Restauration de la tele a l'etat de la sauvegarde %s" % bk.name,
           "rem Genere par tvtool.py le %s. Usage : restore.bat [ip:port]" % stamp,
           "if \"%ADB%\"==\"\" set ADB=adb",
           "set SERIAL=%s" % serial,
           "if not \"%1\"==\"\" set SERIAL=%1",
           "%ADB% connect %SERIAL% >nul 2>&1"]
    for c in cmds:
        sh.append('echo "> %s"; $A shell %s' % (c, c))
        bat.append("echo ^> %s & %%ADB%% -s %%SERIAL%% shell %s" % (c, c))
    if uninstall:
        sh.append('echo "> retrait de Nature Home"; $A uninstall %s' % LAUNCHER_PKG)
        bat.append("echo ^> retrait de Nature Home & %%ADB%% -s %%SERIAL%% uninstall %s" % LAUNCHER_PKG)
    sh += ["$A shell input keyevent KEYCODE_HOME", 'echo "Restauration terminée."']
    bat += ["%ADB% -s %SERIAL% shell input keyevent KEYCODE_HOME", "echo Restauration terminee."]
    (bk / "restore.sh").write_text("\n".join(sh) + "\n", encoding="utf-8", newline="\n")
    (bk / "restore.bat").write_text("\r\n".join(bat) + "\r\n", encoding="utf-8", newline="")
    try:
        (bk / "restore.sh").chmod(0o755)
    except OSError:
        pass


# ---------------------------------------------------------------- vérifications

def health(adb, check_sysui=True):
    """Télé réactive et interface système vivante."""
    if adb.state() != "device":
        return False, "ADB ne répond plus"
    if check_sysui and not adb.sh("pidof com.android.systemui").strip():
        return False, "com.android.systemui ne tourne pas"
    return True, "ok"


def sysui_detectable(adb):
    """Certaines télés n'ont pas pidof ou pas com.android.systemui : on ne s'y fie alors pas."""
    return bool(adb.sh("pidof com.android.systemui").strip())


def disable(adb, bk, pkg, reason):
    if is_protected(pkg) and reason != "launcher":
        warn("%s est protégé : ignoré" % pkg)
        return False
    out = adb.sh("pm disable-user --user 0 %s" % pkg)
    if pkg in adb.packages("-d"):
        log(bk, {"op": "disable", "pkg": pkg, "reason": reason}, adb.serial)
        ok("%s désactivé" % pkg)
        return True
    warn("%s : refusé par la télé (%s)" % (pkg, out.splitlines()[-1] if out else "sans message"))
    return False


def enable(adb, pkg):
    adb.sh("pm enable --user 0 %s" % pkg)
    if pkg in adb.packages("-e"):
        ok("%s réactivé" % pkg)
        return True
    warn("%s : réactivation non confirmée" % pkg)
    return False


# ---------------------------------------------------------------- commandes

def cmd_discover(args):
    adb = Adb(find_adb(args.adb))
    found = {}
    rc, out, _ = adb.run("mdns", "services", timeout=10)
    if rc == 0:
        for m in re.finditer(r"(_adb[\w-]*\._tcp)\S*\s+(\d+\.\d+\.\d+\.\d+):(\d+)", out):
            kind = "appairage requis (Android 11+)" if "pairing" in m.group(1) else "débogage sans fil"
            found["%s:%s" % (m.group(2), m.group(3))] = kind
    nets = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("192.0.2.1", 9))
        nets.add(ipaddress.ip_network(s.getsockname()[0] + "/24", strict=False))
        s.close()
    except OSError:
        pass
    for n in args.subnet or []:
        nets.add(ipaddress.ip_network(n, strict=False))
    if not nets:
        die("Réseau local introuvable ; précise-le : --subnet 192.168.1.0/24")

    def probe(ip):
        try:
            with socket.create_connection((str(ip), 5555), timeout=0.5):
                return str(ip)
        except OSError:
            return None

    for net in nets:
        print("Balayage de %s (port 5555)…" % net)
        with concurrent.futures.ThreadPoolExecutor(128) as ex:
            for ip in ex.map(probe, net.hosts()):
                if ip:
                    found.setdefault(ip + ":5555", "débogage réseau (port 5555)")
    if not found:
        print("\nAucune télé trouvée. Sur la télé : Paramètres > Système > À propos > cliquer 7 fois sur "
              "« Build » (Version du système), puis Paramètres > Système > Options pour les développeurs > "
              "activer « Débogage USB » / « Débogage réseau » ou « Débogage sans fil ».")
        return
    print("\nAppareils ADB trouvés :")
    for addr, kind in sorted(found.items()):
        print("  %-22s %s" % (addr, kind))
    print("\nEnsuite : python3 tvtool.py connect <ip:port>  (ou « pair » si appairage requis)")


def cmd_pair(args):
    adb = Adb(find_adb(args.adb))
    rc, out, err = adb.run("pair", args.address, args.code, timeout=30)
    print((out + err).strip())
    if rc != 0 or "Successfully" not in out:
        die("Appairage échoué. Le code et le port s'affichent sur la télé dans "
            "Débogage sans fil > Associer l'appareil avec un code.")
    ok("Appairé. Connecte-toi maintenant avec le port affiché sous « Adresse IP et port ».")


def cmd_connect(args):
    target = args.address if ":" in args.address else args.address + ":5555"
    adb = Adb(find_adb(args.adb), target)
    rc, out, err = adb.run("connect", target, timeout=20)
    print((out + err).strip())
    print("Si la télé affiche « Autoriser le débogage ? », coche « Toujours autoriser » et valide.")
    for _ in range(30):
        s = adb.state()
        if s == "device":
            break
        time.sleep(2)
        if s is None:
            adb.run("connect", target, timeout=20)
    if adb.state() != "device":
        die("Connexion non autorisée ou refusée (état : %s)." % adb.state())
    st = state()
    st["serial"] = target
    save_json(STATE_FILE, st)
    ok("Connecté à %s %s (Android %s)" % (adb.prop("ro.product.manufacturer"), adb.prop("ro.product.model"),
                                         adb.prop("ro.build.version.release")))


def cmd_info(args):
    adb = device(args)
    mem = adb.sh("grep -E 'MemTotal|MemAvailable' /proc/meminfo")
    print("Modèle   : %s %s (%s)" % (adb.prop("ro.product.manufacturer"), adb.prop("ro.product.model"),
                                     adb.prop("ro.product.device")))
    print("Android  : %s (API %s)" % (adb.prop("ro.build.version.release"), adb.sdk()))
    print("Build    : %s" % adb.prop("ro.build.fingerprint"))
    print("Accueil  : %s" % adb.home_activity())
    print("Paquets  : %d installés, %d désactivés" % (len(adb.packages()), len(adb.packages("-d"))))
    print(re.sub(r"\s+kB", " kB", mem))
    bk = current_backup(adb, required=False)
    print("Sauvegarde : %s" % (bk or "aucune"))


def cmd_backup(args):
    adb = device(args)
    brand = re.sub(r"\W+", "", adb.prop("ro.product.manufacturer")) or "tv"
    model = re.sub(r"\W+", "", adb.prop("ro.product.model")) or "android"
    bk = BACKUPS / ("%s-%s-%s" % (brand, model, now_stamp()))
    bk.mkdir(parents=True)
    print("Sauvegarde dans %s" % bk)

    files = {
        "getprop.txt": "getprop",
        "packages_tous.txt": "pm list packages -u -f",
        "packages_actifs.txt": "pm list packages -e",
        "packages_desactives.txt": "pm list packages -d",
        "packages_systeme.txt": "pm list packages -s",
        "packages_tiers.txt": "pm list packages -3",
        "settings_global.txt": "settings list global",
        "settings_secure.txt": "settings list secure",
        "settings_system.txt": "settings list system",
        "accueil.txt": "cmd package resolve-activity -a android.intent.action.MAIN -c android.intent.category.HOME",
        "applis_tv.txt": "cmd package query-activities --brief -a android.intent.action.MAIN "
                         "-c android.intent.category.LEANBACK_LAUNCHER",
        "accueil_prefere.txt": "dumpsys package preferred-activities",
    }
    for name, c in files.items():
        (bk / name).write_text(adb.sh(c, timeout=120) + "\n", encoding="utf-8")
        ok(name)

    settings = {}
    for ns, key in [("global", k) for k in ANIM_SETTINGS]:
        v = adb.sh("settings get %s %s" % (ns, key))
        settings["%s/%s" % (ns, key)] = v
    manifest = {
        "serial": adb.serial,
        "created": datetime.datetime.now().isoformat(timespec="seconds"),
        "manufacturer": adb.prop("ro.product.manufacturer"),
        "model": adb.prop("ro.product.model"),
        "android": adb.prop("ro.build.version.release"),
        "sdk": adb.sdk(),
        "fingerprint": adb.prop("ro.build.fingerprint"),
        "home": adb.home_activity(),
        "enabled": adb.packages("-e"),
        "disabled": adb.packages("-d"),
        "settings": settings,
    }
    # Relecture : la sauvegarde n'est retenue que si elle est complète.
    if not manifest["enabled"] or not manifest["home"]:
        die("Sauvegarde incomplète (liste de paquets ou accueil illisible) : rien ne sera modifié.")
    save_json(bk / "manifest.json", manifest)
    journal_path(bk).touch()
    write_restore_scripts(bk, adb.serial)
    st = state()
    st.setdefault("backups", {})[adb.serial] = str(bk)
    save_json(STATE_FILE, st)
    ok("%d paquets actifs, %d désactivés, accueil : %s" % (len(manifest["enabled"]), len(manifest["disabled"]),
                                                          manifest["home"]))
    adb.sh("input keyevent KEYCODE_HOME")
    time.sleep(2)
    shot(adb, "avant")
    print("\nScripts de restauration : %s et %s" % (bk / "restore.sh", bk / "restore.bat"))


def candidates(adb):
    catalog = load_json(CATALOG_FILE, {"packages": []})["packages"]
    enabled = set(adb.packages("-e"))
    system = set(adb.packages("-s"))
    known = {c["pkg"] for c in catalog}
    groups = {k: [] for k in CAT_LABEL}
    for c in catalog:
        if c["pkg"] in enabled and not is_protected(c["pkg"]):
            groups[c["cat"]].append(c)
    for pkg in sorted(enabled - known):
        if is_protected(pkg):
            continue
        t = tokens(pkg)
        vendor = pkg.startswith(VENDOR_PREFIXES)
        if vendor and pkg in system and any(w in t for w in SUSPECT_WORDS):
            groups["suspect"].append({"pkg": pkg, "cat": "suspect", "risk": "inconnu",
                                      "name": pkg, "desc": "[Hypothèse] nom évocateur ; fonction non vérifiée.",
                                      "loss": "Inconnue : vérifier l'écran après désactivation."})
    return groups


def cmd_audit(args):
    adb = device(args)
    groups = candidates(adb)
    for cat, items in groups.items():
        if not items:
            continue
        print("\n== %s ==" % CAT_LABEL[cat])
        for c in items:
            print("  %-45s %-8s %s" % (c["pkg"], c["risk"], c.get("name", "")))
    vendor = [p for p in adb.packages("-e") if p.startswith(VENDOR_PREFIXES)]
    print("\n%d paquets fabricant actifs au total (liste complète : packages_actifs.txt de la sauvegarde)."
          % len(vendor))


def cmd_debloat(args):
    adb = device(args)
    bk = current_backup(adb)
    sysui = sysui_detectable(adb)
    groups = candidates(adb)
    chosen = []

    def describe(c):
        print("\n  %s — %s" % (c.get("name", c["pkg"]), c["pkg"]))
        if c.get("desc"):
            print("    Rôle   : %s" % c["desc"])
        if c.get("loss"):
            print("    Perte  : %s" % c["loss"])
        print("    Risque : %s" % c["risk"])

    for cat in ("pub", "telemetrie"):
        items = groups[cat]
        if not items:
            continue
        print("\n== %s ==" % CAT_LABEL[cat])
        for c in items:
            describe(c)
        if ask("\nDésactiver ces %d paquets ?" % len(items), default=True):
            chosen += items
        elif ask("Les choisir un par un ?"):
            chosen += [c for c in items if ask("  Désactiver %s ?" % c["pkg"])]

    for cat in ("fonction", "appli"):
        items = groups[cat]
        if not items:
            continue
        print("\n== %s ==  (Non par défaut : réponds « o » seulement si tu ne t'en sers pas)" % CAT_LABEL[cat])
        for c in items:
            describe(c)
            if ask("    Tu ne t'en sers pas, je la désactive ?"):
                chosen.append(c)

    if groups["suspect"]:
        print("\n== %s ==" % CAT_LABEL["suspect"])
        print("  Paquets du fabricant non répertoriés dont le nom évoque pub/stats/boutique. "
              "Réponse Non par défaut ; chacun est vérifié après coup.")
        for c in groups["suspect"]:
            if ask("  Désactiver %s ?" % c["pkg"]):
                chosen.append(c)

    if not chosen:
        print("\nRien à désactiver.")
        return
    print("\nRécapitulatif (%d) :" % len(chosen))
    for c in chosen:
        print("  - %s" % c["pkg"])
    if args.dry_run:
        print("\n--dry-run : aucune modification.")
        return
    if not ask("Appliquer ?", default=True):
        return

    done = []
    for c in chosen:
        if disable(adb, bk, c["pkg"], c["cat"]):
            done.append(c["pkg"])
            if c["cat"] == "suspect":
                good, why = health(adb, sysui)
                if not good:
                    warn("Problème détecté (%s) : réactivation de %s" % (why, c["pkg"]))
                    enable(adb, c["pkg"])
                    done.remove(c["pkg"])
    good, why = health(adb, sysui)
    if not good:
        warn("Problème détecté après la série (%s) : réactivation de toute la série." % why)
        for p in done:
            enable(adb, p)
        die("Série annulée. Indique-moi la référence de la télé pour analyser.")
    still = [p for p in done if p not in adb.packages("-d")]
    if still:
        warn("Réactivés par le système entre-temps : %s" % ", ".join(still))
    ok("%d paquets désactivés, interface système OK" % (len(done) - len(still)))
    adb.sh("input keyevent KEYCODE_HOME")
    time.sleep(2)
    shot(adb, "apres-allegement")

    if ask("\nAccélérer les animations (échelle 0,5 au lieu de 1) ?", default=True):
        for k in ANIM_SETTINGS:
            before = adb.sh("settings get global %s" % k)
            adb.sh("settings put global %s 0.5" % k)
            if adb.sh("settings get global %s" % k) == "0.5":
                log(bk, {"op": "setting", "ns": "global", "key": k, "before": before}, adb.serial)
                ok("%s = 0.5 (avant : %s)" % (k, before))
    print("\nRestauration possible à tout moment : python3 tvtool.py restore  (ou %s)" % (bk / "restore.sh"))


def cmd_disable(args):
    adb = device(args)
    bk = current_backup(adb)
    sysui = sysui_detectable(adb)
    for p in args.packages:
        disable(adb, bk, p, "manuel")
    good, why = health(adb, sysui)
    print("Santé : %s" % why)


def cmd_enable(args):
    adb = device(args)
    for p in args.packages:
        enable(adb, p)


def get_apk(args):
    if args.apk:
        apk = Path(args.apk)
        if not apk.exists():
            die("APK introuvable : %s" % apk)
        return apk
    dest = HERE / "NatureHome.apk"
    print("Téléchargement de Nature Home : %s" % LAUNCHER_URL)
    try:
        with urllib.request.urlopen(LAUNCHER_URL, timeout=60) as r:
            dest.write_bytes(r.read())
    except OSError as e:
        die("Téléchargement impossible (%s). Récupère NatureHome.apk dans l'onglet Actions/Releases "
            "du dépôt puis : python3 tvtool.py launcher --apk NatureHome.apk" % e)
    if dest.read_bytes()[:2] != b"PK":
        die("Fichier téléchargé invalide ; utilise --apk.")
    return dest


def tv_apps(adb):
    out = adb.sh("cmd package query-activities --brief -a android.intent.action.MAIN "
                 "-c android.intent.category.LEANBACK_LAUNCHER")
    pkgs = []
    for l in out.splitlines():
        l = l.strip()
        if "/" in l and " " not in l:
            p = l.split("/")[0]
            if p != LAUNCHER_PKG and p not in pkgs:
                pkgs.append(p)
    return pkgs


def configure(adb, extras):
    out = adb.sh("am start -n %s %s" % (LAUNCHER_CONFIG, extras))
    if "Error" in out or "Exception" in out:
        warn("Configuration refusée : %s" % out)
        return False
    return True


def cmd_dock(args):
    adb = device(args)
    if LAUNCHER_PKG not in adb.packages():
        die("Nature Home n'est pas installé (commande « launcher »).")
    if args.set:
        pkgs = [p.strip() for p in args.set.split(",") if p.strip()]
    else:
        apps = tv_apps(adb)
        print("Applis TV installées :")
        for i, p in enumerate(apps, 1):
            print("  %2d. %s" % (i, p))
        try:
            raw = input("\nNuméros des favoris, dans l'ordre du dock (ex. 3,1,7) : ")
        except EOFError:
            raw = ""
        pkgs = []
        for n in re.findall(r"\d+", raw):
            if 1 <= int(n) <= len(apps):
                pkgs.append(apps[int(n) - 1])
    if not pkgs:
        die("Aucune appli choisie.")
    if configure(adb, '--es dock "%s"' % ",".join(pkgs)):
        ok("Dock : %s" % ", ".join(pkgs))
        time.sleep(3)
        shot(adb, "dock")


def set_home(adb, bk):
    before = adb.home_activity()
    out = adb.sh("cmd package set-home-activity --user 0 %s" % LAUNCHER_HOME)
    if re.search(r"Error|Unknown|Exception", out):
        warn("set-home-activity non pris en charge ici (%s)" % out.splitlines()[-1])
    log(bk, {"op": "home", "before": load_json(bk / "manifest.json", {}).get("home") or before,
             "after": LAUNCHER_HOME}, adb.serial)

    def home_is_ours():
        adb.sh("input keyevent KEYCODE_HOME")
        time.sleep(3)
        return adb.resumed_package() == LAUNCHER_PKG

    if home_is_ours():
        ok("La touche Accueil ouvre Nature Home")
        return True
    stock = [p for p in STOCK_LAUNCHERS if p in adb.packages("-e")]
    warn("La touche Accueil ouvre encore %s (fréquent sur Google TV : l'accueil d'origine garde la main)."
         % adb.resumed_package())
    if not stock:
        return False
    print("  Solution réversible : désactiver l'accueil d'origine (%s)." % ", ".join(stock))
    print("  Conséquence : ses rangées de recommandations disparaissent ; les Réglages restent accessibles "
          "via la tuile « Réglages » de Nature Home ; « restore » le réactive.")
    if not ask("  Désactiver l'accueil d'origine ?"):
        return False
    for p in stock:
        disable(adb, bk, p, "launcher")
    adb.sh("cmd package set-home-activity --user 0 %s" % LAUNCHER_HOME)
    if home_is_ours():
        ok("La touche Accueil ouvre Nature Home")
        return True
    warn("Toujours pas : réactivation de l'accueil d'origine.")
    for p in stock:
        enable(adb, p)
    return False


def cmd_launcher(args):
    adb = device(args)
    bk = current_backup(adb)
    apk = get_apk(args)
    was_installed = LAUNCHER_PKG in adb.packages()
    print("Installation de %s…" % apk.name)
    rc, out, err = adb.run("install", "-r", "-g", str(apk), timeout=180)
    print((out + err).strip().splitlines()[-1] if (out + err).strip() else "")
    if LAUNCHER_PKG not in adb.packages():
        die("Installation non confirmée.")
    log(bk, {"op": "install", "pkg": LAUNCHER_PKG, "was_installed": was_installed}, adb.serial)
    ok("Nature Home installé")

    adb.sh("am start -n %s" % LAUNCHER_HOME)
    time.sleep(4)
    if adb.resumed_package() != LAUNCHER_PKG:
        die("Nature Home ne s'affiche pas au premier plan : arrêt avant de toucher à l'accueil. "
            "Envoie-moi la sortie de : adb logcat -d -s AndroidRuntime")
    ok("Nature Home s'ouvre")
    adb.sh("mkdir -p %s" % WALL_DIR_APP)
    shot(adb, "nature-home")

    if ask("\nChoisir maintenant les applis du dock ?", default=True):
        args.set = None
        cmd_dock(args)
    if ask("\nDéfinir Nature Home comme écran d'accueil (touche Accueil) ?", default=True):
        set_home(adb, bk)
        shot(adb, "accueil")
    print("\nSur la télé : appui long sur OK (ou touche Menu) sur une tuile pour la déplacer/retirer ; "
          "« Toutes les applis » pour en ajouter.")


def fetch_wallpapers(count, category):
    LOCAL_WALLPAPERS.mkdir(exist_ok=True)
    ua = {"User-Agent": "tvtool-naturehome/1.0 (usage personnel)"}
    params = {"action": "query", "format": "json", "generator": "categorymembers",
              "gcmtitle": "Category:" + category, "gcmtype": "file", "gcmlimit": "50",
              "prop": "imageinfo", "iiprop": "url|mime|size", "iiurlwidth": "1920"}

    def pages():
        q = dict(params)
        for _ in range(20):
            url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(q)
            with urllib.request.urlopen(urllib.request.Request(url, headers=ua), timeout=30) as r:
                data = json.load(r)
            for pg in data.get("query", {}).get("pages", {}).values():
                yield pg
            if "continue" not in data:
                return
            q = dict(params, **data["continue"])

    got = 0
    for p in pages():
        if got >= count:
            break
        info = (p.get("imageinfo") or [{}])[0]
        url = info.get("thumburl")
        if not url or info.get("mime") not in ("image/jpeg", "image/png") or info.get("width", 0) < info.get("height", 1):
            continue  # paysage uniquement
        name = re.sub(r"[^\w.-]+", "_", p["title"].split(":", 1)[-1])[:80]
        if not name.lower().endswith((".jpg", ".jpeg", ".png")):
            name += ".jpg"
        dest = LOCAL_WALLPAPERS / name
        if not dest.exists():
            with urllib.request.urlopen(urllib.request.Request(url, headers=ua), timeout=60) as r:
                dest.write_bytes(r.read())
        got += 1
        print("  %s" % name)
    if not got:
        raise OSError("catégorie « %s » vide ou introuvable" % category)
    ok("%d images dans %s (source : Wikimedia Commons, catégorie « %s », licences libres)"
       % (got, LOCAL_WALLPAPERS, category))


def cmd_wallpapers(args):
    if args.fetch:
        try:
            fetch_wallpapers(args.fetch, args.category)
        except OSError as e:
            warn("Téléchargement impossible (%s) ; mets tes propres photos dans %s" % (e, LOCAL_WALLPAPERS))
    adb = device(args)
    if LAUNCHER_PKG not in adb.packages():
        die("Nature Home n'est pas installé (commande « launcher »).")
    folder = Path(args.folder) if args.folder else LOCAL_WALLPAPERS
    imgs = sorted(f for f in folder.glob("*") if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
    extras = "--ez next true"
    if args.interval:
        extras += " --ei interval %d" % args.interval

    def push_to(target):
        adb.sh("mkdir -p %s" % target)
        rc, _, err = adb.run("push", *[str(f) for f in imgs], target + "/", timeout=600)
        if rc != 0:
            warn("Envoi vers %s refusé (%s)" % (target, err.strip()))
            return False
        ok("%s images dans %s" % (adb.sh("ls -1 %s | wc -l" % target), target))
        return True

    def seen_by_app():
        """Nombre de photos que Nature Home déclare avoir trouvées (journal système)."""
        adb.sh("logcat -c")
        configure(adb, extras)
        time.sleep(5)
        found = re.findall(r"photos=(\d+)", adb.sh("logcat -d -s NatureHome:I"))
        return int(found[-1]) if found else -1

    if imgs:
        n = seen_by_app() if push_to(WALL_DIR_APP) else 0
        if n <= 0:
            warn("Nature Home ne voit pas les photos dans son dossier ; repli sur %s" % WALL_DIR_PICTURES)
            if push_to(WALL_DIR_PICTURES):
                perm = ("android.permission.READ_MEDIA_IMAGES" if adb.sdk() >= 33
                        else "android.permission.READ_EXTERNAL_STORAGE")
                adb.sh("pm grant %s %s" % (LAUNCHER_PKG, perm))
                n = seen_by_app()
        if n > 0:
            ok("Nature Home lit %d photos" % n)
        else:
            warn("Nature Home ne lit aucune photo (%s) : il garde ses paysages générés." % n)
    else:
        print("Aucune photo locale : Nature Home utilisera ses paysages générés.")
        configure(adb, extras)
        time.sleep(5)
    shot(adb, "fond-1")
    if args.interval:
        ok("Rotation toutes les %d s" % args.interval)


def cmd_screenshot(args):
    adb = device(args)
    shot(adb, args.name)


def cmd_restore(args):
    adb = device(args)
    bk = Path(args.backup) if args.backup else current_backup(adb)
    manifest = load_json(bk / "manifest.json", None)
    if not manifest:
        die("manifest.json illisible dans %s" % bk)
    cmds, uninstall = restore_plan(bk)
    now_disabled = set(adb.packages("-d"))
    planned = {c.split()[-1] for c in cmds if c.startswith("pm enable")}
    drift = sorted((set(manifest["enabled"]) & now_disabled) - planned)
    print("Restauration depuis %s (%s)" % (bk.name, manifest["created"]))
    for c in cmds:
        print("  > %s" % c)
    if drift:
        print("  Actifs dans la sauvegarde mais désactivés maintenant : %s" % ", ".join(drift))
    if uninstall and not args.keep_launcher:
        print("  > retrait de Nature Home")
    if not args.yes and not ask("Continuer ?", default=True):
        return
    for c in cmds:
        out = adb.sh(c)
        if out:
            print("    %s" % out.splitlines()[-1])
    for p in drift:
        enable(adb, p)
    if uninstall and not args.keep_launcher:
        adb.run("uninstall", LAUNCHER_PKG, timeout=60)
    log(bk, {"op": "restored"}, adb.serial)

    # Vérification : comparaison avec l'état sauvegardé.
    enabled_now = set(adb.packages("-e"))
    missing = sorted(set(manifest["enabled"]) - enabled_now)
    home = adb.home_activity()
    adb.sh("input keyevent KEYCODE_HOME")
    time.sleep(3)
    shot(adb, "restaure")
    if missing:
        warn("Encore désactivés : %s" % ", ".join(missing))
    else:
        ok("Tous les paquets actifs de la sauvegarde sont actifs")
    ok("Accueil : %s (sauvegarde : %s)" % (home, manifest["home"]))
    for k, v in manifest.get("settings", {}).items():
        ns, key = k.split("/")
        cur = adb.sh("settings get %s %s" % (ns, key))
        (ok if cur == v else warn)("%s = %s (sauvegarde : %s)" % (k, cur, v))


# ---------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser(description="Allègement réversible d'Android TV + launcher Nature Home")
    ap.add_argument("--adb", help="chemin d'adb (sinon : PATH)")
    ap.add_argument("-s", "--serial", help="télé ciblée (ip:port), sinon la dernière connectée")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("discover", help="trouver la télé sur le réseau local")
    p.add_argument("--subnet", action="append", help="réseau à balayer, ex. 192.168.1.0/24")
    p.set_defaults(fn=cmd_discover)
    p = sub.add_parser("pair", help="appairage « débogage sans fil » (Android 11+)")
    p.add_argument("address")
    p.add_argument("code")
    p.set_defaults(fn=cmd_pair)
    p = sub.add_parser("connect", help="se connecter à la télé")
    p.add_argument("address")
    p.set_defaults(fn=cmd_connect)
    sub.add_parser("info", help="infos télé").set_defaults(fn=cmd_info)
    sub.add_parser("backup", help="sauvegarder l'état complet (obligatoire avant modification)").set_defaults(fn=cmd_backup)
    sub.add_parser("audit", help="lister ce qui peut être allégé, sans rien modifier").set_defaults(fn=cmd_audit)
    p = sub.add_parser("debloat", help="allègement interactif")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_debloat)
    p = sub.add_parser("disable", help="désactiver des paquets précis")
    p.add_argument("packages", nargs="+")
    p.set_defaults(fn=cmd_disable)
    p = sub.add_parser("enable", help="réactiver des paquets précis")
    p.add_argument("packages", nargs="+")
    p.set_defaults(fn=cmd_enable)
    p = sub.add_parser("launcher", help="installer Nature Home")
    p.add_argument("--apk", help="APK local (sinon téléchargé depuis la release du dépôt)")
    p.set_defaults(fn=cmd_launcher)
    p = sub.add_parser("dock", help="choisir les applis du dock")
    p.add_argument("--set", help="liste de paquets séparés par des virgules")
    p.set_defaults(fn=cmd_dock)
    p = sub.add_parser("wallpapers", help="envoyer des fonds d'écran nature")
    p.add_argument("--fetch", type=int, help="télécharger N photos depuis Wikimedia Commons")
    p.add_argument("--category", default="Featured pictures of landscapes")
    p.add_argument("--folder", help="dossier de photos (défaut : android-tv/wallpapers)")
    p.add_argument("--interval", type=int, help="secondes entre deux fonds (défaut appli : 90)")
    p.set_defaults(fn=cmd_wallpapers)
    p = sub.add_parser("screenshot", help="capture d'écran de la télé")
    p.add_argument("name", nargs="?", default="capture")
    p.set_defaults(fn=cmd_screenshot)
    p = sub.add_parser("restore", help="tout remettre comme dans la sauvegarde")
    p.add_argument("backup", nargs="?", help="dossier de sauvegarde (défaut : la dernière)")
    p.add_argument("--yes", action="store_true", help="sans confirmation")
    p.add_argument("--keep-launcher", action="store_true", help="ne pas retirer Nature Home")
    p.set_defaults(fn=cmd_restore)

    args = ap.parse_args()
    try:
        args.fn(args)
    except KeyboardInterrupt:
        die("Interrompu. Les modifications déjà faites sont journalisées ; « restore » les annule.", 130)


if __name__ == "__main__":
    main()
