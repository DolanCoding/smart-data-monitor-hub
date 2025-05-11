# app.py: Hauptdatei für das SDMN Flask Backend
# Enthält grundlegende App-Konfiguration, Datenbank-Setup, ein User-Modell
# und Implementierung der Benutzerauthentifizierung.

from flask import Flask, render_template, url_for, redirect, request, flash # Importiere weitere Flask-Funktionen
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user # Importiere Flask-Login
from werkzeug.security import generate_password_hash, check_password_hash # Importiere Sicherheitsfunktionen von Werkzeug
import os

# basedir holt das Verzeichnis der aktuellen Datei (__file__).
# Das ist nützlich, um Pfade relativ zur App-Datei anzugeben.
basedir = os.path.abspath(os.path.dirname(__file__))

# Erstellt die Flask-Anwendungsinstanz.
# __name__ hilft Flask, den Root-Pfad der Anwendung zu bestimmen,
# wichtig für das Finden von Ressourcen (z.B. Templates, statische Dateien).
app = Flask(__name__)

# Füge einen geheimen Schlüssel für die App hinzu. Wichtig für Sicherheit wie Sessions und Flask-WTF.
# In einer echten Anwendung sollte dies aus einer .env-Datei geladen werden!
# Für jetzt verwenden wir einen Platzhalter. Später sicherer machen!
app.config['SECRET_KEY'] = 'Dolan' # TODO: Diesen Schlüssel aus .env laden!

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

# Deaktiviert die Verfolgung von Änderungen an SQLAlchemy-Objekten.
# Das spart Ressourcen und wird empfohlen, wenn es nicht explizit benötigt wird.
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialisiert die SQLAlchemy-Erweiterung mit der Flask-App.
db = SQLAlchemy(app)

# Initialisiert Flask-Login.
# Wird zur Verwaltung von Benutzer-Sessions benötigt.
login_manager = LoginManager()
login_manager.init_app(app)

# Stellt die Ansichtsfunktion für die Login-Seite ein.
# Flask-Login leitet unauthentifizierte Benutzer hierhin um.
login_manager.login_view = 'login'

# Datenbankmodell: User-Tabelle
# Erbt von db.Model (für SQLAlchemy) und UserMixin (für Flask-Login).
class User(UserMixin, db.Model):
    """
    Datenbankmodell für einen Benutzer.
    Repräsentiert die 'user' Tabelle in der SQLite-Datenbank.
    UserMixin stellt Standardimplementierungen für Eigenschaften
    und Methoden bereit, die von Flask-Login benötigt werden (z.B. is_authenticated).
    """
    # id: Primärschlüssel, automatisch generiert und hochgezählt
    id = db.Column(db.Integer, primary_key=True)
    # username: Textfeld (String), muss einzigartig sein, darf nicht leer sein
    username = db.Column(db.String(80), unique=True, nullable=False)
    # email: Textfeld (String), muss einzigartig sein, darf nicht leer sein
    email = db.Column(db.String(120), unique=True, nullable=False)
    # password_hash: Speichert den gehashten String des Passworts.
    password_hash = db.Column(db.String(128)) # 128 für gehashte Passwörter, nicht unique

    # Methode zum Setzen des Passworts (hasht es)
    def set_password(self, password):
        """
        Hasht das übergebene Passwort und speichert es im password_hash Feld.
        Verwendet generate_password_hash von Werkzeug für sicheres Hashing.
        """
        self.password_hash = generate_password_hash(password)

    # Methode zur Überprüfung des Passworts
    def check_password(self, password):
        """
        Überprüft, ob das gegebene Passwort mit dem gespeicherten Hash übereinstimmt.
        Verwendet check_password_hash von Werkzeug.
        """
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        """
        Gibt eine lesbare String-Repräsentation des User-Objekts zurück.
        Nützlich für Debugging und das Anzeigen von Objekten in der Konsole.
        """
        return f'<User {self.username}>'

# Flask-Login: user_loader Callback
# Diese Funktion wird von Flask-Login verwendet, um einen Benutzer anhand seiner ID zu laden.
@login_manager.user_loader
def load_user(user_id):
    """
    Lädt einen Benutzer anhand seiner ID.
    Wird von Flask-Login benötigt, um den eingeloggten Benutzer zu verwalten.
    Sollte None zurückgeben, wenn der Benutzer nicht existiert.
    """
    if user_id is not None:
        return db.session.get(User, int(user_id)) # Verwende session.get statt query.get für neuere SQLAlchemy-Versionen
    return None

# Routen-Definition: Startseite
# Der Decorator @app.route('/') ordnet die URL '/' dieser Funktion zu.
@app.route('/')
def index():
    """
    Ansichtsfunktion für die Startseite.
    Wird aufgerufen, wenn ein Benutzer die Root-URL der Anwendung besucht.
    Gibt eine einfache Willkommensnachricht als String zurück.
    """
    return "Welcome to the SDMN Backend!" # TODO: Später auf eine Landing Page im Frontend verweisen oder rendern

# TODO: Implementiere Registrierungs- und Login-Routen (später in diesem Schritt)

# Beispiel für eine Registrierungsroute (noch nicht vollständig implementiert, dient als Platzhalter)
@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Ansichtsfunktion für die Benutzerregistrierung.
    Behandelt GET-Anfragen zur Anzeige des Formulars und POST-Anfragen zur Verarbeitung.
    """
    # TODO: Formularverarbeitung mit Flask-WTF hinzufügen
    if request.method == 'POST':
        # TODO: Daten validieren
        username = request.form.get('username') # Beispiel, Formularfeld vorausgesetzt
        email = request.form.get('email')
        password = request.form.get('password')

        # TODO: Prüfen, ob Benutzer oder E-Mail bereits existieren

        # Beispiel: Neuen Benutzer erstellen (noch ohne Validierung!)
        new_user = User(username=username, email=email)
        new_user.set_password(password) # Passwort hashen und setzen

        # TODO: Benutzer zur Datenbank hinzufügen und commiten

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return "<h1>Registration Page (Placeholder)</h1><p>TODO: Add registration form here.</p>" # TODO: Echtes Template rendern

# Beispiel für eine Login-Route (noch nicht vollständig implementiert, dient als Platzhalter)
@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Ansichtsfunktion für den Benutzer-Login.
    Behandelt GET-Anfragen zur Anzeige des Formulars und POST-Anfragen zur Verarbeitung.
    """
    # TODO: Formularverarbeitung mit Flask-WTF hinzufügen
    if request.method == 'POST':
        # TODO: Daten validieren
        username = request.form.get('username') # Beispiel, Formularfeld vorausgesetzt
        password = request.form.get('password')
        remember = request.form.get('remember') # Checkbox für 'Angemeldet bleiben'

        # TODO: Benutzer anhand des Benutzernamens aus der Datenbank laden
        user = None # Platzhalter: user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            # TODO: Benutzer mit Flask-Login einloggen
            login_user(user, remember=remember) # remember=True/False
            # TODO: Zum nächsten geschützten Bereich weiterleiten
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index')) # Beispiel: Weiterleitung zur Startseite

        flash('Invalid username or password.', 'danger')
        # TODO: Formular mit Fehlern erneut anzeigen

    return "<h1>Login Page (Placeholder)</h1><p>TODO: Add login form here.</p>" # TODO: Echtes Template rendern

# Beispiel für eine Logout-Route
@app.route('/logout')
# @login_required # TODO: Nur eingeloggte Benutzer sollten sich ausloggen können
def logout():
    """
    Ansichtsfunktion für den Benutzer-Logout.
    Loggt den aktuellen Benutzer mithilfe von Flask-Login aus.
    """
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index')) # Zum Beispiel zur Startseite oder Login-Seite weiterleiten


# Startpunkt der Anwendung:
# Dieser Block wird nur ausgeführt, wenn die Datei 'app.py' direkt
# ausgeführt wird (z.B. mit 'python app.py'), nicht wenn sie als Modul importiert wird.
if __name__ == '__main__':
    """
    Datenbanktabellen erstellen im Anwendungs-Kontext:
    app.app_context() erstellt einen temporären Kontext, in dem Flask-Erweiterungen
    wie SQLAlchemy korrekt arbeiten können.
    db.create_all() liest alle in der App definierten db.Model-Klassen
    und erstellt entsprechende Tabellen in der Datenbank, falls sie noch nicht existieren.
    Da wir das User-Modell erweitert haben (password_hash), muss die Datenbank
    aktualisiert werden. Da wir noch keine Migrationen nutzen, kann es notwendig sein,
    die alte site.db zu löschen, damit create_all die neue Spalte hinzufügt.
    In einer Produktionsanwendung oder bei komplexeren Datenbankänderungen
    würde man hierfür üblicherweise Flask-Migrate verwenden.
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