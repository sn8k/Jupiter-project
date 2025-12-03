"""
cli/commands.py – Commandes CLI exposées via le Bridge.
Version: 0.1.0

Utilise argparse pour rester léger ; compatible Typer si le projet l'adopte.
"""

import argparse


def build_parser(subparsers):
    """
    Ajoute les sous-commandes du plugin au parser CLI principal.
    
    Args:
        subparsers: Objet subparsers d'argparse.
    """
    parser = subparsers.add_parser(
        "example",
        help="Commandes du plugin Example"
    )
    sub = parser.add_subparsers(dest="example_cmd")

    # Sous-commande : run
    run_parser = sub.add_parser("run", help="Exécute l'action exemple")
    run_parser.add_argument("--verbose", "-v", action="store_true", help="Mode verbeux")
    run_parser.set_defaults(func=cmd_run)

    # Sous-commande : status
    status_parser = sub.add_parser("status", help="Affiche le statut du plugin")
    status_parser.set_defaults(func=cmd_status)


def cmd_run(args):
    """
    Exécute l'action exemple.
    """
    print("[Example Plugin] Running example action...")
    if args.verbose:
        print("[Example Plugin] Verbose mode enabled.")
    # Logique métier ici (appel à core/logic.py)
    print("[Example Plugin] Done.")


def cmd_status(args):
    """
    Affiche le statut du plugin.
    """
    print("[Example Plugin] Status: OK")


def register_cli_contribution(main_subparsers):
    """
    Point d'entrée appelé par le Bridge pour enregistrer les commandes.
    
    Args:
        main_subparsers: Subparsers de la CLI principale.
    """
    build_parser(main_subparsers)
