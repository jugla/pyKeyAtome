import requests
from concurrent.futures import ThreadPoolExecutor
import time
import threading
import os

# ============================================================
# PARAMETRES A REMPLIR PAR L'UTILISATEUR
# ============================================================
#
# Ce script recherche automatiquement l'identifiant interne associé
# à votre compteur Linky chez Total Energies, afin de pouvoir
# récupérer ensuite vos données de consommation en temps réel.
#
# Avant de lancer le script, vous devez remplir les 3 champs
# ci-dessous avec VOS propres informations :
#
#   1) EMAIL              -> l'adresse email que vous utilisez pour
#                            vous connecter à votre espace client
#                            Total Energies.
#
#   2) MOT_DE_PASSE       -> le mot de passe associé à ce compte.
#                            (gardez bien les guillemets autour)
#
#   3) REFERENCE_CLIENT   -> votre numéro de référence client
#                            (9 chiffres). Vous le trouverez :
#                              - sur n'importe quelle facture Total Energies
#                              - ou sur la page d'accueil de votre espace
#                                client en ligne, juste sous votre adresse.
#
# IMPORTANT : conservez bien les guillemets " " autour de chaque valeur.
# Exemple correct   : EMAIL = "monadresse@gmail.com"
# Exemple incorrect : EMAIL = monadresse@gmail.com   <-- ne fonctionnera pas
#
EMAIL = "votre.email@exemple.com"  # <-- mettez ici votre email Total Energies
MOT_DE_PASSE = "VotreMotDePasse"   # <-- mettez ici votre mot de passe
REFERENCE_CLIENT = "123456789"     # <-- mettez ici votre référence client (9 chiffres)


# ------------------------------------------------------------
# PLAGE DE RECHERCHE
# ------------------------------------------------------------
#
# Le script va tester un par un des identifiants numériques pour
# trouver celui qui correspond à votre compteur.
#
# Par défaut, il teste de 1 à 10 000 000 (dix millions), ce qui
# peut être très long. Si vous préférez découper la recherche en
# plusieurs essais plus courts, vous pouvez modifier les bornes :
#
#   - Premier essai  : DEBUT_RECHERCHE = 1          / FIN_RECHERCHE = 990_000
#   - Deuxième essai : DEBUT_RECHERCHE = 990_001    / FIN_RECHERCHE = 2_000_000
#   - Troisième essai: DEBUT_RECHERCHE = 2_000_001  / FIN_RECHERCHE = 3_000_000
#   - etc.
#
# Le caractère "_" dans les nombres sert juste à les rendre plus
# lisibles (10_000_000 = 10000000). Vous pouvez l'utiliser ou non.
#
DEBUT_RECHERCHE = 1                # point de départ de la recherche
FIN_RECHERCHE = 10_000_000         # point d'arrivée de la recherche


# ============================================================
# CONFIGURATION TECHNIQUE
# (à ne modifier que si vous savez ce que vous faites)
# ============================================================
URL_BASE = "https://esoftlink.esoftthings.com"
NB_THREADS = 30
INTERVALLE_RECONNEXION = 2 * 60 * 60  # 2 heures
INTERVALLE_PROGRESSION = 5            # secondes entre deux affichages de progression


# ------------------------------------------------------------
# ETAT GLOBAL
# ------------------------------------------------------------
session = requests.Session()
id_session_php = None
verrou = threading.Lock()
verrou_stats = threading.Lock()
verrou_succes = threading.Lock()

derniere_connexion = 0

# Statistiques
nb_verifies = 0
nb_trouves = 0
nb_erreurs = 0
temps_debut = 0

# Signal d'arrêt quand un identifiant valide est trouvé
evenement_trouve = threading.Event()


# ------------------------------------------------------------
# CONNEXION AU SERVEUR
# ------------------------------------------------------------
def connexion():
    global id_session_php, derniere_connexion, session

    print("[+] Reconnexion en cours...")

    s = requests.Session()

    r = s.post(
        f"{URL_BASE}/login_check",
        data={
            "_username": EMAIL,
            "_password": MOT_DE_PASSE
        },
        allow_redirects=False,
        timeout=10
    )

    cookies = s.cookies.get_dict()

    if "PHPSESSID" not in cookies:
        print("Echec de la connexion - aucun PHPSESSID reçu")
        return False

    with verrou:
        session = s
        id_session_php = cookies["PHPSESSID"]
        derniere_connexion = time.time()

    print(f"[+] Session rafraîchie avec succès")

    return True


# ------------------------------------------------------------
# VERIFICATION DE L'EXPIRATION DE LA SESSION
# ------------------------------------------------------------
def verifier_connexion():
    global derniere_connexion

    if time.time() - derniere_connexion > INTERVALLE_RECONNEXION:
        connexion()


# ------------------------------------------------------------
# ARRET DU PROGRAMME LORSQU'UN IDENTIFIANT VALIDE EST TROUVE
# ------------------------------------------------------------
def arret_avec_succes(identifiant, reponse):
    """Affiche l'identifiant trouvé, les statistiques finales,
    puis termine immédiatement le programme."""
    duree = time.time() - temps_debut

    print("\n" + "=" * 60)
    print(f"[!!! IDENTIFIANT TROUVE] UserId = {identifiant}")
    print("-" * 60)
    print(reponse)
    print("-" * 60)
    with verrou_stats:
        print(f"[FIN] Vérifiés        : {nb_verifies}")
        print(f"[FIN] Erreurs         : {nb_erreurs}")
    print(f"[FIN] Temps écoulé    : {int(duree//60)}m{int(duree%60)}s")
    print("=" * 60)

    # os._exit termine immédiatement tout le process (et donc tous les threads),
    # sans attendre que les workers du pool aient fini leurs requêtes en cours.
    os._exit(0)


# ------------------------------------------------------------
# VERIFICATION D'UN IDENTIFIANT
# ------------------------------------------------------------
def verifier_utilisateur(id_utilisateur):
    global nb_verifies, nb_trouves, nb_erreurs

    # Si un identifiant valide a déjà été trouvé par un autre thread,
    # on n'effectue plus aucune requête.
    if evenement_trouve.is_set():
        return

    verifier_connexion()

    id_brut = str(id_utilisateur)
    id_complete = str(id_utilisateur).zfill(6)

    deja_vus = set()

    for identifiant in (id_brut, id_complete):

        if identifiant in deja_vus:
            continue
        deja_vus.add(identifiant)

        if evenement_trouve.is_set():
            return

        url = f"{URL_BASE}/api/subscription/{identifiant}/{REFERENCE_CLIENT}/measure/live.json"

        try:
            with verrou:
                s = session

            r = s.get(url, timeout=5)

            with verrou_stats:
                nb_verifies += 1

            if '"error"' not in r.text:
                with verrou_succes:
                    if evenement_trouve.is_set():
                        return
                    evenement_trouve.set()
                    with verrou_stats:
                        nb_trouves += 1
                    arret_avec_succes(identifiant, r.text)

        except requests.RequestException:
            with verrou_stats:
                nb_erreurs += 1

    time.sleep(0.01)


# ------------------------------------------------------------
# AFFICHAGE DE LA PROGRESSION
# ------------------------------------------------------------
def rapport_progression(total_utilisateurs):
    derniers_verifies = 0
    dernier_temps = time.time()

    while True:
        time.sleep(INTERVALLE_PROGRESSION)

        with verrou_stats:
            verifies_actuels = nb_verifies

        maintenant = time.time()
        duree = maintenant - temps_debut
        delta_verifies = verifies_actuels - derniers_verifies
        delta_temps = maintenant - dernier_temps

        cadence_totale = verifies_actuels / duree if duree > 0 else 0
        cadence_recente = delta_verifies / delta_temps if delta_temps > 0 else 0

        # Progression sur le total (2 requêtes par utilisateur, sauf doublons)
        pourcentage = (verifies_actuels / (total_utilisateurs * 2)) * 100 if total_utilisateurs > 0 else 0

        restant = (total_utilisateurs * 2) - verifies_actuels
        eta_sec = restant / cadence_recente if cadence_recente > 0 else 0
        eta_h = int(eta_sec // 3600)
        eta_m = int((eta_sec % 3600) // 60)

        print(
            f"[STATS] vérifiés={verifies_actuels} "
            f"({pourcentage:.2f}%) | "
            f"cadence={cadence_recente:.1f}/s (moy {cadence_totale:.1f}/s) | "
            f"écoulé={int(duree//60)}m{int(duree%60)}s | "
            f"ETA={eta_h}h{eta_m:02d}m"
        )

        derniers_verifies = verifies_actuels
        dernier_temps = maintenant


# ============================================================
# DEMARRAGE DU PROGRAMME
# ============================================================
print("=" * 60)
print(f"[CONFIG] Email             : {EMAIL}")
print(f"[CONFIG] Référence client  : {REFERENCE_CLIENT}")
print(f"[CONFIG] URL de base       : {URL_BASE}")
print(f"[CONFIG] Threads           : {NB_THREADS}")
print(f"[CONFIG] Reconnexion toutes les {INTERVALLE_RECONNEXION // 60} min")
print("=" * 60)

if not connexion():
    print("[FATAL] La connexion initiale a échoué - arrêt du programme.")
    exit(1)

total_utilisateurs = FIN_RECHERCHE - DEBUT_RECHERCHE

print(f"[+] Scan des identifiants de {DEBUT_RECHERCHE} à {FIN_RECHERCHE} ({total_utilisateurs} utilisateurs)")
print(f"[+] Environ {total_utilisateurs * 2} requêtes au total (version brute + version complétée à 6 chiffres)")
print(f"[+] La progression sera affichée toutes les {INTERVALLE_PROGRESSION} secondes")
print("=" * 60)

temps_debut = time.time()

# Démarre l'affichage de progression en arrière-plan
thread_rapport = threading.Thread(
    target=rapport_progression,
    args=(total_utilisateurs,),
    daemon=True
)
thread_rapport.start()

nb_soumis = 0
with ThreadPoolExecutor(max_workers=NB_THREADS) as executor:
    for id_utilisateur in range(DEBUT_RECHERCHE, FIN_RECHERCHE):
        # Si un identifiant valide a été trouvé entre-temps, on arrête
        # d'alimenter la file d'attente.
        # (arret_avec_succes appelle os._exit, donc en pratique on n'arrive
        #  ici que si l'identifiant n'a pas encore été traité.)
        if evenement_trouve.is_set():
            break

        executor.submit(verifier_utilisateur, id_utilisateur)
        nb_soumis += 1

        if nb_soumis % 10000 == 0:
            print(f"[FILE] {nb_soumis}/{total_utilisateurs} identifiants envoyés dans la file")

print("=" * 60)
print("[+] Toutes les tâches ont été soumises. Attente de la fin des workers...")

# Note : on n'arrive ici que si AUCUN identifiant valide n'a été trouvé sur
# toute la plage, puisque arret_avec_succes termine le programme via
# os._exit dès le premier identifiant valide.
duree_totale = time.time() - temps_debut
with verrou_stats:
    print("=" * 60)
    print("[FIN] Scan terminé - AUCUN IDENTIFIANT TROUVE sur la plage complète.")
    print(f"[FIN] Total vérifiés : {nb_verifies}")
    print(f"[FIN] Total erreurs  : {nb_erreurs}")
    print(f"[FIN] Temps total    : {int(duree_totale//3600)}h{int((duree_totale%3600)//60)}m{int(duree_totale%60)}s")
    print("=" * 60)
