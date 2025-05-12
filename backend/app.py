# backend/app.py: Hauptdatei für das SDMN Flask Backend
# Enthält grundlegende App-Konfiguration, Datenbank-Setup, Flask-Login
# und Routen für die Authentifizierung und Monitor-API.
# Enthält Logik zum Abrufen und initialen Verarbeiten von Daten.

from flask import Flask, render_template, url_for, redirect, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from sqlalchemy.exc import IntegrityError
from datetime import datetime

import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup

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
    """
    Ansichtsfunktion für die Startseite.
    """
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
        except IntegrityError:
             db.session.rollback()
             flash('Username or Email already exists.', 'danger') # Eindeutigkeitsfehler abfangen
             return redirect(url_for('register'))
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


# API Routen für Monitor CRUD (Create, Read, Update, Delete)

@app.route('/api/monitors', methods=['GET', 'POST'])
@login_required # Nur eingeloggte Benutzer können auf diese Route zugreifen
def manage_monitors():
    """
    API Endpunkt zur Verwaltung von Monitoren (Liste abrufen, neuen Monitor erstellen).
    GET: Ruft alle Monitore des aktuell eingeloggten Benutzers ab.
    POST: Erstellt einen neuen Monitor für den aktuell eingeloggten Benutzer.
    Erwartet JSON-Daten im POST-Request: {"name": "...", "data_source_url": "...", "analysis_type": "..."}
    Gibt eine Liste von Monitoren (GET) oder den neu erstellten Monitor (POST) als JSON zurück.
    """
    if request.method == 'GET':
        # Hole alle Monitore, die dem aktuellen Benutzer gehören, über die Relationship
        monitors = current_user.monitors

        # Bereite die Daten für die JSON-Antwort vor
        monitors_data = []
        for monitor in monitors:
            monitors_data.append({
                'id': monitor.id,
                'name': monitor.name,
                'data_source_url': monitor.data_source_url,
                'analysis_type': monitor.analysis_type,
                'creation_date': monitor.creation_date.isoformat() if monitor.creation_date else None, # Datum als ISO-Format String
                'last_run': monitor.last_run.isoformat() if monitor.last_run else None,
                'is_active': monitor.is_active,
                # 'user_id': monitor.user_id # Nicht unbedingt nötig in der Antwort, da es immer der eingeloggte Benutzer ist
            })

        # Gib die Liste der Monitore als JSON-Antwort zurück
        return jsonify(monitors_data)

    elif request.method == 'POST':
        # Erwarte JSON-Daten vom Frontend
        data = request.get_json()

        # Grundlegende Validierung der JSON-Daten
        if not data or not data.get('name') or not data.get('data_source_url') or not data.get('analysis_type'):
            # Gib eine Fehlermeldung und Statuscode 400 Bad Request zurück
            return jsonify({"error": "Missing required monitor data (name, data_source_url, analysis_type)"}), 400

        name = data.get('name')
        data_source_url = data.get('data_source_url')
        analysis_type = data.get('analysis_type')

        # TODO: Erweiterte Validierung (z.B. URL-Format, erlaubte analysis_type Werte)

        # Erstelle ein neues Monitor-Objekt
        new_monitor = Monitor(
            name=name,
            data_source_url=data_source_url,
            analysis_type=analysis_type,
            user_id=current_user.id # Weise den Monitor dem aktuell eingeloggten Benutzer zu
            # creation_date und is_active haben Standardwerte im Modell
        )

        try:
            # Füge den neuen Monitor zur Datenbank-Session hinzu
            db.session.add(new_monitor)
            # Speichere die Änderungen
            db.session.commit()

            # Gib den neu erstellten Monitor als JSON-Antwort zurück (inklusive ID und Standardwerten)
            return jsonify({
                'id': new_monitor.id,
                'name': new_monitor.name,
                'data_source_url': new_monitor.data_source_url,
                'analysis_type': new_monitor.analysis_type,
                'creation_date': new_monitor.creation_date.isoformat() if new_monitor.creation_date else None,
                'last_run': new_monitor.last_run.isoformat() if new_monitor.last_run else None,
                'is_active': new_monitor.is_active,
                'user_id': new_monitor.user_id
            }), 201 # Statuscode 201 Created zurückgeben

        except IntegrityError:
             # TODO: Hier spezifischere Fehlerbehandlung falls nötig (z.B. Name einzigartig?)
             db.session.rollback()
             return jsonify({"error": "Database integrity error."}), 500 # Interner Serverfehler

        except Exception as e:
            # Allgemeine Fehlerbehandlung
            db.session.rollback()
            # Logge den Fehler für Debugging
            app.logger.error(f"Error creating monitor: {e}")
            return jsonify({"error": "Failed to create monitor due to internal error."}), 500 # Interner Serverfehler


@app.route('/api/monitors/<int:monitor_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required # Nur eingeloggte Benutzer können auf diese Routen zugreifen
def manage_single_monitor(monitor_id):
    """
    API Endpunkt zur Verwaltung eines einzelnen Monitors anhand seiner ID.
    Stellt sicher, dass der Monitor dem aktuell eingeloggten Benutzer gehört.
    GET: Ruft einen spezifischen Monitor ab.
    PUT: Aktualisiert einen spezifischen Monitor. Erwartet JSON-Daten im PUT-Request.
    DELETE: Löscht einen spezifischen Monitor.
    Erwartet Monitor-ID als Teil der URL.
    Gibt den Monitor (GET/PUT) oder Erfolgsmeldung (DELETE) als JSON zurück.
    """
    # Suche den Monitor anhand der ID UND stelle sicher, dass er dem aktuell eingeloggten Benutzer gehört
    monitor = Monitor.query.filter_by(id=monitor_id, user_id=current_user.id).first()

    # Wenn der Monitor nicht gefunden wird ODER er nicht dem aktuellen Benutzer gehört, gib 404 zurück
    if not monitor:
        return jsonify({"error": "Monitor not found or does not belong to the current user"}), 404

    if request.method == 'GET':
        # Gib die Daten des gefundenen Monitors als JSON zurück
        return jsonify({
            'id': monitor.id,
            'name': monitor.name,
            'data_source_url': monitor.data_source_url,
            'analysis_type': monitor.analysis_type,
            'creation_date': monitor.creation_date.isoformat() if monitor.creation_date else None,
            'last_run': monitor.last_run.isoformat() if monitor.last_run else None,
            'is_active': monitor.is_active,
            'user_id': monitor.user_id
        })

    elif request.method == 'PUT':
        # Erwarte JSON-Daten für die Aktualisierung
        data = request.get_json()

        # Grundlegende Validierung der Update-Daten
        if not data:
             return jsonify({"error": "No update data provided"}), 400

        # Aktualisiere die Felder des Monitors, wenn Daten im Request enthalten sind
        if 'name' in data:
            monitor.name = data['name']
        if 'data_source_url' in data:
            monitor.data_source_url = data['data_source_url']
        if 'analysis_type' in data:
            monitor.analysis_type = data['analysis_type']
        if 'is_active' in data:
            # Stelle sicher, dass is_active ein Boolean ist
            if isinstance(data['is_active'], bool):
                monitor.is_active = data['is_active']
            else:
                return jsonify({"error": "is_active must be a boolean value"}), 400
        # TODO: Erweiterte Validierung der Update-Daten

        try:
            # Speichere die Änderungen
            db.session.commit()
            # Gib den aktualisierten Monitor als JSON zurück
            return jsonify({
                'id': monitor.id,
                'name': monitor.name,
                'data_source_url': monitor.data_source_url,
                'analysis_type': monitor.analysis_type,
                'creation_date': monitor.creation_date.isoformat() if monitor.creation_date else None,
                'last_run': monitor.last_run.isoformat() if monitor.last_run else None,
                'is_active': monitor.is_active,
                'user_id': monitor.user_id
            })

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating monitor {monitor_id}: {e}")
            return jsonify({"error": "Failed to update monitor due to internal error."}), 500

    elif request.method == 'DELETE':
        try:
            # Lösche den Monitor aus der Datenbank
            db.session.delete(monitor)
            # Speichere die Änderung
            db.session.commit()
            # Gib eine Erfolgsmeldung zurück
            return jsonify({"message": f"Monitor {monitor_id} deleted successfully."}), 200 # 200 OK oder 204 No Content

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error deleting monitor {monitor_id}: {e}")
            return jsonify({"error": "Failed to delete monitor due to internal error."}), 500


# --- Logik für Datenabruf und initiale Verarbeitung (Schritt 2.3) ---

def fetch_data_from_url(url):
    """
    Holt Daten von einer gegebenen URL.
    Beinhaltet grundlegende Fehlerbehandlung für den HTTP-Abruf.
    Gibt den Text der Antwort zurück oder None bei Fehler.
    """
    try:
        response = requests.get(url)
        response.raise_for_status() # Löst HTTPError für schlechte Antworten (4xx oder 5xx) aus
        return response.text # Gibt den Inhalt der Antwort als String zurück
    except requests.exceptions.RequestException as e:
        # Fehler beim Abrufen der URL (Netzwerkprobleme, ungültige URL, Timeout etc.)
        app.logger.error(f"Error fetching data from {url}: {e}")
        return None # Gib None zurück, um anzuzeigen, dass der Abruf fehlgeschlagen ist


def extract_text_from_html(html_content):
    """
    Extrahiert Text aus HTML-Inhalt.
    Gibt den bereinigten Text zurück.
    """
    if not html_content:
        return None
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        # Entferne Skripte und Style-Elemente
        for script in soup(["script", "style"]):
            script.extract()
        text = soup.get_text()
        # Bereinige Text (entferne überflüssige Leerzeichen und Zeilenumbrüche)
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        return text
    except Exception as e:
        app.logger.error(f"Error extracting text from HTML: {e}")
        return None


def process_monitor_data(monitor: Monitor): #! Neue Funktion beginnt hier
    """ #! Neuer Docstring
    Verarbeitet Daten für einen gegebenen Monitor basierend auf seiner Konfiguration. #! Neuer Docstring
    Holt Daten von der data_source_url und führt initiale Verarbeitung durch (z.B. Text-Extraktion). #! Neuer Docstring
    Gibt die verarbeiteten Daten (z.B. reiner Text) zurück oder None bei Fehlern. #! Neuer Docstring
    """ #! Ende neuer Docstring
    if not monitor or not monitor.data_source_url: #! Neue Zeile
        app.logger.warning("process_monitor_data called with invalid monitor or missing URL.") #! Neue Zeile
        return None #! Neue Zeile

    raw_data = fetch_data_from_url(monitor.data_source_url) #! Neue Zeile
    if raw_data is None: #! Neue Zeile
        # fetch_data_from_url hat den Fehler bereits geloggt #! Neue Zeile
        return None #! Neue Zeile

    processed_data = None #! Neue Zeile

    # Beispiel für initiale Verarbeitung basierend auf analysis_type #! Neue Zeile
    if monitor.analysis_type in ['sentiment', 'keywords']: #! Neue Zeile
        # Für Textanalysen extrahieren wir Text aus HTML #! Neue Zeile
        processed_data = extract_text_from_html(raw_data) #! Neue Zeile
        if processed_data is None: #! Neue Zeile
             app.logger.error(f"Failed to extract text for monitor {monitor.id} from {monitor.data_source_url}") #! Neue Zeile
             return None #! Neue Zeile
        # TODO: Weitere Logik für andere Datenformate (z.B. JSON direkt parsen) #! Neuer TODO

    # TODO: Weitere 'analysis_type's und deren spezifische initiale Verarbeitung #! Neuer TODO

    # Wenn kein spezifischer Verarbeitungsschritt definiert ist, geben wir die Rohdaten zurück (oder None, je nach Design) #! Neue Zeile
    if processed_data is None: #! Neue Zeile
         # Für analysis_types, die keine initiale Verarbeitung benötigen (z.B. API, die direkt saubere Daten liefert) #! Neue Zeile
         # Oder als Fallback, wenn der analysis_type unbekannt ist #! Neue Zeile
         processed_data = raw_data #! Neue Zeile


    return processed_data #! Neue Zeile
#! Ende neue Funktion


# TODO: Funktion, die fetch_data_from_url und extract_text_from_html basierend auf Monitor-Konfiguration aufruft #! Dieser TODO-Kommentar kann nun gelöscht werden, da process_monitor_data diese Rolle übernimmt.


# Startpunkt der Anwendung:
# Dieser Block wird nur ausgeführt, wenn die Datei 'app.py' direkt
# ausgeführt wird (z.B. mit 'python app.py'), nicht wenn sie als Modul importiert wird.
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