# backend/app.py: Hauptdatei für das SDMN Flask Backend
# Enthält grundlegende App-Konfiguration, Datenbank-Setup, Flask-Login
# und Registrierung von Blueprints für Routen.
# Modelldefinitionen sind in models.py.
# Routen sind in Blueprints in backend/routes/.

from flask import Flask, render_template, url_for, redirect, request, flash, jsonify
# Entferne Imports für SQLAlchemy, LoginManager, UserMixin, login_user, logout_user, current_user, login_required hier, falls nicht für andere Zwecke benötigt #! Imports für diese in Blueprints verschoben
from flask_sqlalchemy import SQLAlchemy #! SQLAlchemy Import bleibt hier
from flask_login import LoginManager #! LoginManager Import bleibt hier

# Entferne Imports für SQLAlchemy.exc, datetime, requests, BeautifulSoup hier #! Imports in Blueprints verschoben

import os
from dotenv import load_dotenv

# Importiere das db-Objekt aus der lokalen __init__.py Datei
from . import db #! Importiere db aus backend/__init__.py

# Importiere die Blueprints aus dem routes Unterpaket
from .routes.auth import auth_bp #! Importiere den Auth Blueprint
from .routes.monitor_api import monitor_api_bp #! Importiere den Monitor API Blueprint

# basedir holt das Verzeichnis der aktuellen Datei (__file__).
# Dies ist nützlich, um Pfade relativ zur App-Datei anzugeben.
basedir = os.path.abspath(os.path.dirname(__file__))

# Lade Umgebungsvariablen aus der .env Datei
load_dotenv(os.path.join(basedir, '.env'))

# Erstellt die Flask-Anwendungsinstanz.
# __name__ hilft Flask, den Root-Pfad der Anwendung zu bestimmen.
app = Flask(__name__)

# Lade den geheimen Schlüssel aus der .env Datei
# os.getenv('SECRET_KEY') liest den Wert der Umgebungsvariable SECRET_KEY
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') # Jetzt aus .env geladen!

"""
Datenbank-Konfiguration:
Setzt die URI für die SQLAlchemy-Datenbank.
'sqlite:///' gibt an, dass wir SQLite verwenden.
os.path.join erstellt einen betriebssystemunabhängigen Pfad.
'instance' ist ein Standardordner für Instanz-spezifische Dateien.
'site.db' ist der Name unserer Datenbankdatei.
Der 'instance'-Ordner wird durch .gitignore ignoriert.
"""
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'site.db')

# Deaktiviert die Verfolgung von Änderungen an SQLAlchemy-Objekten.
# Das spart Ressourcen.
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialisiert das in __init__.py erstellte db-Objekt mit dieser Flask-App.
db.init_app(app) # Initialisiere db-Objekt mit der app Instanz

# Initialisiert Flask-Login.
login_manager = LoginManager()
login_manager.init_app(app)

# Stellt die Ansichtsfunktion für die Login-Seite ein.
login_manager.login_view = 'auth.login' #! Login View verweist nun auf Blueprint Route
login_manager.login_message_category = 'info' # Kategorie für die Standard-Flash-Nachricht

# Importiere das User-Modell für load_user (oder stelle es in models.py bereit und importiere es dort) #! User Modell wird direkt in models.py importiert, die von __init__.py importiert werden kann, wo db ist.
# Flask-Login: user_loader Callback
@login_manager.user_loader
def load_user(user_id):
    """
    Lädt einen Benutzer anhand seiner ID.
    Wird von Flask-Login benötigt.
    """
    # Importiere das User-Modell nur hier, um Zirkuläre Imports zu vermeiden,
    # falls models.py direkt von app.py importiert würde (was wir jetzt nicht tun, da db in __init__.py ist).
    # Da db in __init__.py ist und Modelle in models.py, die db importieren,
    # können wir Modelle sicher importieren, nachdem db initialisiert wurde.
    # Das User-Modell ist bereits über den Import in models.py registriert.
    from .models import User #! Importiere User hier lokal in der Funktion (alternative zum globalen Import oben)
    if user_id is not None:
        return db.session.get(User, int(user_id))
    return None

# Registriere die Blueprints bei der Haupt-App
app.register_blueprint(auth_bp) #! Registriere den Auth Blueprint
app.register_blueprint(monitor_api_bp) #! Registriere den Monitor API Blueprint


# Routen-Definition: Startseite (Diese Route bleibt in app.py, da sie global ist)
@app.route('/')
def index():
    """
    Ansichtsfunktion für die Startseite.
    """
    # TODO: Später auf eine Landing Page im Frontend verweisen oder rendern
    # current_user wird von Flask-Login bereitgestellt (Import ist oben) #! current_user Import behalten falls nötig
    from flask_login import current_user #! Importiere current_user hier lokal, falls nicht global benötigt
    if current_user.is_authenticated:
        return f'Hello, {current_user.username}! Welcome to the SDMN Backend!'
    else:
        return "Welcome to the SDMN Backend! Please log in or register."


# Entferne alle anderen Routen-Funktionen hier (/register, /login, /logout, /dashboard, /api/monitors, /api/monitors/<id>) #! Alle Routen wurden in Blueprints verschoben


# Entferne die Funktionen für Datenabruf und initiale Verarbeitung hier #! Funktionen wurden in monitor_api.py verschoben

# Startpunkt der Anwendung:
# Dieser Block wird nur ausgeführt, wenn die Datei 'app.py' direkt
# ausgeführt wird (z.B. mit 'python app.py'), nicht wenn sie als Modul importiert wird.
# BEI VERWENDUNG VON FLASK RUN WIRD DIESER BLOCK NICHT AUSGEFÜHRT, ABER ER IST FÜR ALTERNATIVES STARTEN NÜTZLICH
if __name__ == '__main__':
    """
    Datenbanktabellen erstellen im Anwendungs-Kontext:
    Erstellt alle in models.py definierten Tabellen, falls sie noch nicht existieren.
    Möglicherweise müssen Sie site.db löschen, wenn Sie das Schema manuell ändern
    und keine Migrationen verwenden.
    """
    with app.app_context():
        # db.create_all() liest nun die Modelle über die registrierten Blueprints und den db-Import aus models.py
        db.create_all()

    """
    Flask Entwicklungsserver starten.
    """
    # app.run(debug=True) #! Dieser Aufruf ist nicht notwendig, wenn Sie 'flask run' verwenden. Kann entfernt oder auskommentiert werden.
    pass #! Füge pass ein, da der Block leer sein könnte, wenn app.run auskommentiert ist

# TODO: app.logger muss noch verfügbar gemacht werden in den Blueprint-Dateien (auth.py, monitor_api.py) #! Neuer TODO für Logging