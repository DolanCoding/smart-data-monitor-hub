# backend/app.py: Hauptdatei für das SDMN Flask Backend
"""
    Enthält grundlegende App-Konfiguration, Datenbank-Setup, Flask-Login
    und Routen. Modelldefinitionen sind in models.py.
"""

from flask import Flask, render_template, url_for, redirect, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required # Füge login_required hinzu
# Keine Imports für generate_password_hash, check_password_hash, User oder Monitor hier!

import os
from dotenv import load_dotenv # Importiere load_dotenv

# Imports für die Modelle aus der lokalen models.py Datei
from .models import db, User, Monitor # Importiere db und die Modelle

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

# Initialisiert die SQLAlchemy-Erweiterung mit der Flask-App.
# Das db-Objekt wird hier initialisiert und dann in models.py importiert.
db.init_app(app) # Nutze init_app nach dem Erstellen der App, falls db separat initialisiert wird

# Initialisiert Flask-Login.
login_manager = LoginManager()
login_manager.init_app(app)

# Stellt die Ansichtsfunktion für die Login-Seite ein.
login_manager.login_view = 'login'
login_manager.login_message_category = 'info' # Kategorie für die Standard-Flash-Nachricht

# Flask-Login: user_loader Callback
@login_manager.user_loader
def load_user(user_id):
    """
        Lädt einen Benutzer anhand seiner ID.
        Wird von Flask-Login benötigt.
    """
    if user_id is not None:
        return db.session.get(User, int(user_id))
    return None

# Routen-Definition: Startseite
@app.route('/')
def index():
    #Ansichtsfunktion für die Startseite.
    # TODO: Später auf eine Landing Page im Frontend verweisen oder rendern
    if current_user.is_authenticated:
        return f'Hello, {current_user.username}! Welcome to the SDMN Backend!'
    else:
        return "Welcome to the SDMN Backend! Please log in or register."


# Beispiel für eine Registrierungsroute (mit grundlegender Logik)
@app.route('/register', methods=['GET', 'POST'])
def register():
    """
        Ansichtsfunktion für die Benutzerregistrierung.
        Handelt GET zur Anzeige des Formulars (TODO: Template) und POST zur Verarbeitung.
        Erwartet 'username', 'email', 'password' im POST-Request.
        Gibt Weiterleitung oder Fehlermeldungen zurück.
    """
    if current_user.is_authenticated:
        flash('You are already registered and logged in.', 'info')
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Grundlegende Validierung (TODO: Erweiterte Validierung mit Flask-WTF)
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('register')) # TODO: Formular mit Fehlern anzeigen

        # Prüfen, ob Benutzer oder E-Mail bereits existieren
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or Email already exists.', 'danger')
            return redirect(url_for('register')) # TODO: Formular mit Fehlern anzeigen

        # Neuen Benutzer erstellen
        new_user = User(username=username, email=email)
        new_user.set_password(password) # Passwort hashen und setzen

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback() # Änderungen zurücknehmen im Fehlerfall
            flash(f'Registration failed: {e}', 'danger')
            return redirect(url_for('register')) # TODO: Formular mit Fehlern anzeigen


    # TODO: Echtes Registrierungs-Template für GET rendern
    return "<h1>Registration Page (Placeholder)</h1><form method='POST'><input type='text' name='username' placeholder='Username'><br><input type='email' name='email' placeholder='Email'><br><input type='password' name='password' placeholder='Password'><br><button type='submit'>Register</button></form>"


# Beispiel für eine Login-Route (mit grundlegender Logik)
@app.route('/login', methods=['GET', 'POST'])
def login():
    """
        Ansichtsfunktion für den Benutzer-Login.
        Handelt GET zur Anzeige des Formulars (TODO: Template) und POST zur Verarbeitung.
        Erwartet 'username', 'password' und optional 'remember' im POST-Request.
        Gibt Weiterleitung oder Fehlermeldungen zurück.
    """
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Grundlegende Validierung (TODO: Erweiterte Validierung mit Flask-WTF)
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False # Checkbox für 'Angemeldet bleiben'

        if not username or not password:
             flash('Username and password are required.', 'danger')
             return redirect(url_for('login')) # TODO: Formular mit Fehlern anzeigen


        # Benutzer anhand des Benutzernamens laden
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            # Benutzer mit Flask-Login einloggen
            login_user(user, remember=remember) # remember=True/False
            # Weiterleitung nach erfolgreichem Login (TODO: Nächsten Bereich bestimmen)
            next_page = request.args.get('next')
            flash('Logged in successfully.', 'success')
            return redirect(next_page or url_for('index'))

        flash('Invalid username or password.', 'danger')
        # TODO: Formular mit Fehlern erneut anzeigen

    # TODO: Echtes Login-Template für GET rendern
    return "<h1>Login Page (Placeholder)</h1><form method='POST'><input type='text' name='username' placeholder='Username'><br><input type='password' name='password' placeholder='Password'><br><label><input type='checkbox' name='remember'> Remember Me</label><br><button type='submit'>Login</button></form>"


# Beispiel für eine Logout-Route
@app.route('/logout')
@login_required # Stellt sicher, dass nur eingeloggte Benutzer diese Route aufrufen können
def logout():
    """
    Ansichtsfunktion für den Benutzer-Logout.
    Loggt den aktuellen Benutzer mithilfe von Flask-Login aus.
    """
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index')) # Zum Beispiel zur Startseite weiterleiten


# Beispiel für eine geschützte Route (nur für eingeloggte Benutzer zugänglich)
@app.route('/dashboard')
@login_required # Dieser Decorator schützt die Route
def dashboard():
    """
    Beispiel für eine geschützte Route.
    Nur eingeloggte Benutzer können diese Seite sehen.
    """
    return f"<h1>Welcome to the Dashboard, {current_user.username}!</h1><p>This is a protected area.</p><p><a href='{url_for('logout')}'>Logout</a></p>"


# Startpunkt der Anwendung:
if __name__ == '__main__':
    """
    Datenbanktabellen erstellen im Anwendungs-Kontext:
    Erstellt alle in models.py definierten Tabellen, falls sie noch nicht existieren.
    Möglicherweise müssen Sie site.db löschen, wenn Sie das Schema manuell ändern
    und keine Migrationen verwenden.
    """
    with app.app_context():
        # db.create_all() liest nun die Modelle aus models.py
        db.create_all()

    """
    Flask Entwicklungsserver starten.
    """
    app.run(debug=True)