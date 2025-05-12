# backend/__init__.py: Macht 'backend' zu einem Python-Paket
# und initialisiert das SQLAlchemy-Objekt.

from flask_sqlalchemy import SQLAlchemy #! Importiere SQLAlchemy

db = SQLAlchemy() #! Initialisiere das db-Objekt hier