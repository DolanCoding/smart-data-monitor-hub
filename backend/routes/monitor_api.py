# backend/routes/monitor_api.py: Blueprint für Monitor API Routen
# Enthält Routen für CRUD-Operationen auf Monitoren und die Datenverarbeitungslogik.

from flask import Blueprint, request, jsonify #! Importiere Flask-Funktionen
from flask_login import login_required, current_user # Importiere Flask-Login Funktionen (werden hier nicht für den Trigger-Endpunkt benötigt, aber für CRUD)
from sqlalchemy.exc import IntegrityError #! Importiere IntegrityError
from datetime import datetime #! Importiere datetime

import requests #! Importiere requests
from bs4 import BeautifulSoup #! Importiere BeautifulSoup
import os #! Importiere os für Umgebungsvariablen

# Importiere das db-Objekt und die Modelle aus den übergeordneten Paketen
# Die Punkte (..) navigieren ein Verzeichnis hoch (von 'routes' nach 'backend')
from .. import db #! Importiere db aus backend/__init__.py
from ..models import Monitor, User #! Importiere Monitor und User aus backend/models.py

# Erstelle einen Blueprint für Monitor API Routen
# 'monitor_api_bp' ist der Name des Blueprints
# url_prefix='/api' gibt allen Routen in diesem Blueprint das Präfix '/api'
monitor_api_bp = Blueprint('monitor_api', __name__, url_prefix='/api') #! Definiere den Blueprint mit Präfix


# --- API Routen für Monitor CRUD (Create, Read, Update, Delete) ---
# (Diese Routen bleiben hier, wurden aber im vorherigen Schritt verschoben)

@monitor_api_bp.route('/monitors', methods=['GET', 'POST'])
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
            # TODO: app.logger muss noch verfügbar gemacht werden oder hier anders loggen
            # app.logger.error(f"Error creating monitor: {e}")
            return jsonify({"error": "Failed to create monitor due to internal error."}), 500 # Interner Serverfehler


@monitor_api_bp.route('/monitors/<int:monitor_id>', methods=['GET', 'PUT', 'DELETE'])
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
            # TODO: app.logger muss noch verfügbar gemacht werden oder hier anders loggen
            # app.logger.error(f"Error updating monitor {monitor_id}: {e}")
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
            # TODO: app.logger muss noch verfügbar gemacht werden oder hier anders loggen
            # app.logger.error(f"Error deleting monitor {monitor_id}: {e}")
            return jsonify({"error": "Failed to delete monitor due to internal error."}), 500


# --- Logik für Datenabruf und initiale Verarbeitung (Schritt 2.3) ---
# Diese Funktionen werden hier platziert, da sie eng mit der API interagieren werden,
# insbesondere mit einem zukünftigen Endpunkt, der die Verarbeitung anstößt.

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
        # TODO: app.logger muss noch verfügbar gemacht werden oder hier anders loggen
        # app.logger.error(f"Error fetching data from {url}: {e}")
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
        # TODO: app.logger muss noch verfügbar gemacht werden oder hier anders loggen
        # app.logger.error(f"Error extracting text from HTML: {e}")
        return None


def process_monitor_data(monitor: Monitor):
    """
    Verarbeitet Daten für einen gegebenen Monitor basierend auf seiner Konfiguration.
    Holt Daten von der data_source_url und führt initiale Verarbeitung durch (z.B. Text-Extraktion).
    Gibt die verarbeiteten Daten (z.B. reiner Text) zurück oder None bei Fehlern.
    """
    if not monitor or not monitor.data_source_url:
        # TODO: app.logger muss noch verfügbar gemacht werden oder hier anders loggen
        # app.logger.warning("process_monitor_data called with invalid monitor or missing URL.")
        return None

    raw_data = fetch_data_from_url(monitor.data_source_url)
    if raw_data is None:
        # fetch_data_from_url hat den Fehler bereits geloggt (TODO: Anpassung wegen Logging)
        return None

    processed_data = None

    # Beispiel für initiale Verarbeitung basierend auf analysis_type
    if monitor.analysis_type in ['sentiment', 'keywords']:
        # Für Textanalysen extrahieren wir Text aus HTML
        processed_data = extract_text_from_html(raw_data)
        if processed_data is None:
             # TODO: app.logger muss noch verfügbar gemacht werden oder hier anders loggen
             # app.logger.error(f"Failed to extract text for monitor {monitor.id} from {monitor.data_source_url}")
             return None
        # TODO: Weitere Logik für andere Datenformate (z.B. JSON direkt parsen)

    # TODO: Weitere 'analysis_type's und deren spezifische initiale Verarbeitung

    # Wenn kein spezifischer Verarbeitungsschritt definiert ist, geben wir die Rohdaten zurück (oder None, je nach Design)
    if processed_data is None:
         # Für analysis_types, die keine initiale Verarbeitung benötigen (z.B. API, die direkt saubere Daten liefert)
         # Oder als Fallback, wenn der analysis_type unbekannt ist
         processed_data = raw_data


    return processed_data


# --- Endpunkt für n8n Trigger (Schritt 2.4) ---

@monitor_api_bp.route('/monitors/trigger', methods=['POST']) #! Neue Route auf Blueprint (ohne /api)
def trigger_monitor_processing():
    """ #! Neuer Docstring
    API Endpunkt, den n8n aufruft, um die Verarbeitung eines Monitors anzustoßen. #! Neuer Docstring
    Erfordert API-Schlüssel-Authentifizierung. #! Neuer Docstring
    Erwartet JSON im POST-Request: {"monitor_id": <id>} #! Neuer Docstring
    Gibt Erfolgs- oder Fehlermeldung als JSON zurück. #! Neuer Docstring
    """ #! Ende neuer Docstring
    # API-Schlüssel Authentifizierung #! Neue Zeile
    # Erwarte den API-Schlüssel im 'X-API-KEY' Header #! Neue Zeile
    api_key_header = request.headers.get('X-API-KEY') #! Neue Zeile
    expected_api_key = os.getenv('N8N_API_KEY') #! Neue Zeile

    if not api_key_header or api_key_header != expected_api_key: #! Neue Zeile
        # Gib 401 Unauthorized zurück, wenn der Schlüssel fehlt oder falsch ist #! Neue Zeile
        return jsonify({"error": "Unauthorized: Invalid or missing API key"}), 401 #! Neue Zeile

    # Hole die Monitor-ID aus dem Request Body #! Neue Zeile
    data = request.get_json() #! Neue Zeile
    if not data or 'monitor_id' not in data: #! Neue Zeile
        # Gib 400 Bad Request zurück, wenn monitor_id fehlt #! Neue Zeile
        return jsonify({"error": "Missing 'monitor_id' in request body"}), 400 #! Neue Zeile

    monitor_id = data.get('monitor_id') #! Neue Zeile

    # Hole den Monitor aus der Datenbank #! Neue Zeile
    # WICHTIG: Für diesen Endpunkt, der von n8n (System) aufgerufen wird,
    # prüfen wir NICHT, ob der Monitor zum aktuellen Benutzer gehört (da es keinen eingeloggten Benutzer gibt).
    # n8n muss die Monitor-ID kennen und autorisiert sein, diesen Endpunkt aufzurufen (via API Key).
    monitor = Monitor.query.get(monitor_id) #! Suche Monitor direkt nach ID

    if not monitor: #! Neue Zeile
        # Gib 404 Not Found zurück, wenn Monitor nicht existiert #! Neue Zeile
        return jsonify({"error": f"Monitor with ID {monitor_id} not found"}), 404 #! Neue Zeile

    # TODO: Optional prüfen, ob der Monitor aktiv ist (monitor.is_active) #! Neuer TODO

    try: #! Neue Zeile
        # Starte den Datenabruf- und Verarbeitungsprozess für diesen Monitor #! Neue Zeile
        # Die process_monitor_data Funktion gibt die verarbeiteten Daten zurück #! Neue Zeile
        processed_data = process_monitor_data(monitor) #! Neue Zeile

        if processed_data is None: #! Neue Zeile
             # process_monitor_data hat Fehler geloggt, falls etwas schiefging #! Neue Zeile
             # Gib einen Fehler zurück, wenn die Verarbeitung fehlschlug #! Neue Zeile
             return jsonify({"error": f"Failed to process data for monitor {monitor_id}"}), 500 # Interner Serverfehler #! Neue Zeile

        # TODO: Rufe hier die AI-Analysefunktion auf (Phase 3) und verarbeite das Ergebnis #! Neuer TODO für AI

        # TODO: Speichere Analyseergebnisse oder erstelle Benachrichtigung (später in Phase 3/4) #! Neuer TODO für Ergebnis/Benachrichtigung

        # Gib eine Erfolgsmeldung und die verarbeiteten Daten zurück (oder nur eine Erfolgsmeldung) #! Neue Zeile
        return jsonify({ #! Neue Zeile
            "message": f"Processing triggered successfully for monitor {monitor_id}", #! Neue Zeile
            "processed_data": processed_data # Gib die verarbeiteten Daten zurück (kann groß sein!) #! Neue Zeile
        }), 200 # 200 OK #! Neue Zeile

    except Exception as e: #! Neue Zeile
        # Allgemeine Fehlerbehandlung während des Trigger-Prozesses #! Neue Zeile
        # TODO: app.logger muss noch verfügbar gemacht werden oder hier anders loggen #! TODO anpassen wegen logging
        # app.logger.error(f"Error processing trigger for monitor {monitor_id}: {e}")
        return jsonify({"error": f"An error occurred during processing trigger for monitor {monitor_id}."}), 500 # Interner Serverfehler #! Neue Zeile
#! Ende neuer Endpunkt


# TODO: Note: Die Logging-Aufrufe (app.logger.error etc.) müssen angepasst werden, da app in diesem Modul nicht direkt verfügbar ist. Eine mögliche Lösung ist, das Logger-Objekt von app.py an die Funktionen zu übergeben oder eine separate Logging-Konfiguration zu verwenden. #! TODO bleibt

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
    # app.run(debug=True) # Dieser Aufruf ist nicht notwendig, wenn Sie 'flask run' verwenden. Kann entfernt oder auskommentiert werden.
    pass # Füge pass ein, da der Block leer sein könnte, wenn app.run auskommentiert ist