# app.py: Hauptdatei für das SDMN Flask Backend
# Enthält grundlegende App-Konfiguration, Datenbank-Setup und ein Beispielmodell.

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os # Importiere das os Modul, um mit Dateipfaden zu arbeiten

"""
    basedir holt das Verzeichnis der aktuellen Datei (__file__).
    Das ist nützlich, um Pfade relativ zur App-Datei anzugeben.
"""
basedir = os.path.abspath(os.path.dirname(__file__))

"""
    Erstellt die Flask-Anwendungsinstanz.
    __name__ hilft Flask, den Root-Pfad der Anwendung zu bestimmen,
    wichtig für das Finden von Ressourcen (z.B. Templates, statische Dateien).
"""
app = Flask(__name__)

"""
    Datenbank-Konfiguration:
    Setzt die URI für die SQLAlchemy-Datenbank.
    'sqlite:///' gibt an, dass wir SQLite verwenden.
    os.path.join erstellt einen betriebssystemunabhängigen Pfad.
    'instance' ist ein Standardordner für Instanz-spezifische Dateien.
    'site.db' ist der Name unserer Datenbankdatei.
    Der 'instance'-Ordner wird durch .gitignore ignoriert, was wichtig ist,
    da Datenbankdateien Build-spezifisch sind und potenziell Geheimnisse enthalten können.
"""
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'site.db')
"""
    # Deaktiviert die Verfolgung von Änderungen an SQLAlchemy-Objekten.
    # Das spart Ressourcen und wird empfohlen, wenn es nicht explizit benötigt wird.
"""
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialisiert die SQLAlchemy-Erweiterung mit der Flask-App.
db = SQLAlchemy(app)

# Datenbankmodell: User-Tabelle
class User(db.Model):
    """
    Datenbankmodell für einen Benutzer.
    Repräsentiert die 'user' Tabelle in der SQLite-Datenbank.
    
    id: Primärschlüssel, automatisch generiert und hochgezählt
    username: Textfeld (String), muss einzigartig sein, darf nicht leer sein
    email: Textfeld (String), muss einzigartig sein, darf nicht leer sein
    
    TODO: Später Passwort-Hash-Spalte hinzufügen (in Schritt 1.3 des neuen Plans)
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    def __repr__(self):
        """
        Gibt eine lesbare String-Repräsentation des User-Objekts zurück.
        Nützlich für Debugging und das Anzeigen von Objekten in der Konsole.
        """
        return f'<User {self.username}>'

# Routen-Definition: Startseite
# Der Decorator @app.route('/') ordnet die URL '/' dieser Funktion zu.
@app.route('/')
def index():
    """
    Ansichtsfunktion für die Startseite.
    Wird aufgerufen, wenn ein Benutzer die Root-URL der Anwendung besucht.
    Gibt eine einfache Willkommensnachricht als String zurück.
    """
    return "Welcome to the SDMN Backend!"

"""
Startpunkt der Anwendung:
Dieser Block wird nur ausgeführt, wenn die Datei 'app.py' direkt
ausgeführt wird (z.B. mit 'python app.py'), nicht wenn sie als Modul importiert wird.
"""

if __name__ == '__main__':
    """
    Datenbanktabellen erstellen im Anwendungs-Kontext:
    app.app_context() erstellt einen temporären Kontext, in dem Flask-Erweiterungen
    wie SQLAlchemy korrekt arbeiten können.
    db.create_all() liest alle in der App definierten db.Model-Klassen
    und erstellt entsprechende Tabellen in der Datenbank, falls sie noch nicht existieren.
    In einer Produktionsanwendung oder bei komplexeren Datenbankänderungen
    würde man hierfür üblicherweise Flask-Migrate verwenden, um Datenbankmigrationen
    zu verwalten. Für dieses Projekt und die anfängliche Einrichtung ist create_all() ausreichend.
    """
    with app.app_context():
        db.create_all()

    """
    Flask Entwicklungsserver starten:
    app.run() startet den lokalen Webserver.
    debug=True:
    - Ermöglicht das Debugging (zeigt detaillierte Fehlermeldungen im Browser/Konsole).
    - Aktiviert den automatischen Neuladen des Servers bei Code-Änderungen.
    Sollte in Produktion IMMER auf False gesetzt werden!
    """
    app.run(debug=True)