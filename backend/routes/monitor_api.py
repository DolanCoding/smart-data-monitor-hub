# backend/routes/monitor_api.py: Blueprint für Monitor API Routen
# Enthält Routen für CRUD-Operationen auf Monitoren und die Datenverarbeitungslogik.

from flask import Blueprint, request, jsonify #! Importiere Flask-Funktionen
from flask_login import login_required, current_user #! Importiere Flask-Login Funktionen
from sqlalchemy.exc import IntegrityError #! Importiere IntegrityError
from datetime import datetime #! Importiere datetime

import requests #! Importiere requests
from bs4 import BeautifulSoup #! Importiere BeautifulSoup

# Importiere das db-Objekt und die Modelle aus den übergeordneten Paketen
# Die Punkte (..) navigieren ein Verzeichnis hoch (von 'routes' nach 'backend')
from .. import db #! Importiere db aus backend/__init__.py
from ..models import Monitor, User #! Importiere Monitor und User aus backend/models.py

# Erstelle einen Blueprint für Monitor API Routen
# 'monitor_api_bp' ist der Name des Blueprints
# url_prefix='/api' gibt allen Routen in diesem Blueprint das Präfix '/api'
monitor_api_bp = Blueprint('monitor_api', __name__, url_prefix='/api') #! Definiere den Blueprint mit Präfix


# --- API Routen für Monitor CRUD (Create, Read, Update, Delete) ---

@monitor_api_bp.route('/monitors', methods=['GET', 'POST']) #! Route auf Blueprint (ohne /api, da Präfix gesetzt)
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
            # Logge den Fehler für Debugging (TODO: app.logger muss noch verfügbar gemacht werden oder hier anders loggen) #! TODO anpassen wegen logging
            # app.logger.error(f"Error creating monitor: {e}")
            return jsonify({"error": "Failed to create monitor due to internal error."}), 500 # Interner Serverfehler


@monitor_api_bp.route('/monitors/<int:monitor_id>', methods=['GET', 'PUT', 'DELETE']) #! Route auf Blueprint (ohne /api)
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
            # TODO: app.logger muss noch verfügbar gemacht werden oder hier anders loggen #! TODO anpassen wegen logging
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
            # TODO: app.logger muss noch verfügbar gemacht werden oder hier anders loggen #! TODO anpassen wegen logging
            # app.logger.error(f"Error deleting monitor {monitor_id}: {e}")
            return jsonify({"error": "Failed to delete monitor due to internal error."}), 500


# --- Logik für Datenabruf und initiale Verarbeitung (Schritt 2.3) ---
# Diese Funktionen werden hier platziert, da sie eng mit der API interagieren werden,
# insbesondere mit einem zukünftigen Endpunkt, der die Verarbeitung anstößt.

def fetch_data_from_url(url): #! Funktion verschoben
    """ #! Docstring verschoben
    Holt Daten von einer gegebenen URL. #! Docstring verschoben
    Beinhaltet grundlegende Fehlerbehandlung für den HTTP-Abruf. #! Docstring verschoben
    Gibt den Text der Antwort zurück oder None bei Fehler. #! Docstring verschoben
    """ #! Docstring verschoben
    try: #! Zeile verschoben
        response = requests.get(url) #! Zeile verschoben
        response.raise_for_status() # Löst HTTPError für schlechte Antworten (4xx oder 5xx) aus #! Zeile verschoben
        return response.text # Gibt den Inhalt der Antwort als String zurück #! Zeile verschoben
    except requests.exceptions.RequestException as e: #! Zeile verschoben
        # Fehler beim Abrufen der URL (Netzwerkprobleme, ungültige URL, Timeout etc.) #! Zeile verschoben
        # TODO: app.logger muss noch verfügbar gemacht werden oder hier anders loggen #! TODO anpassen wegen logging
        # app.logger.error(f"Error fetching data from {url}: {e}")
        return None # Gib None zurück, um anzuzeigen, dass der Abruf fehlgeschlagen ist #! Zeile verschoben


def extract_text_from_html(html_content): #! Funktion verschoben
    """ #! Docstring verschoben
    Extrahiert Text aus HTML-Inhalt. #! Docstring verschoben
    Gibt den bereinigten Text zurück. #! Docstring verschoben
    """ #! Docstring verschoben
    if not html_content: #! Zeile verschoben
        return None #! Zeile verschoben
    try: #! Zeile verschoben
        soup = BeautifulSoup(html_content, 'html.parser') #! Zeile verschoben
        # Entferne Skripte und Style-Elemente #! Zeile verschoben
        for script in soup(["script", "style"]): #! Zeile verschoben
            script.extract() #! Zeile verschoben
        text = soup.get_text() #! Zeile verschoben
        # Bereinige Text (entferne überflüssige Leerzeichen und Zeilenumbrüche) #! Zeile verschoben
        lines = (line.strip() for line in text.splitlines()) #! Zeile verschoben
        chunks = (phrase.strip() for line in lines for phrase in line.split("  ")) #! Zeile verschoben
        text = '\n'.join(chunk for chunk in chunks if chunk) #! Zeile verschoben
        return text #! Zeile verschoben
    except Exception as e: #! Zeile verschoben
        # TODO: app.logger muss noch verfügbar gemacht werden oder hier anders loggen #! TODO anpassen wegen logging
        # app.logger.error(f"Error extracting text from HTML: {e}")
        return None #! Zeile verschoben


def process_monitor_data(monitor: Monitor): #! Funktion verschoben
    """ #! Docstring verschoben
    Verarbeitet Daten für einen gegebenen Monitor basierend auf seiner Konfiguration. #! Docstring verschoben
    Holt Daten von der data_source_url und führt initiale Verarbeitung durch (z.B. Text-Extraktion). #! Docstring verschoben
    Gibt die verarbeiteten Daten (z.B. reiner Text) zurück oder None bei Fehlern. #! Docstring verschoben
    """ #! Docstring verschoben
    if not monitor or not monitor.data_source_url: #! Zeile verschoben
        # TODO: app.logger muss noch verfügbar gemacht werden oder hier anders loggen #! TODO anpassen wegen logging
        # app.logger.warning("process_monitor_data called with invalid monitor or missing URL.")
        return None #! Zeile verschoben

    raw_data = fetch_data_from_url(monitor.data_source_url) #! Zeile verschoben
    if raw_data is None: #! Zeile verschoben
        # fetch_data_from_url hat den Fehler bereits geloggt (TODO: Anpassung wegen Logging) #! Zeile verschoben
        return None #! Zeile verschoben

    processed_data = None #! Zeile verschoben

    # Beispiel für initiale Verarbeitung basierend auf analysis_type #! Zeile verschoben
    if monitor.analysis_type in ['sentiment', 'keywords']: #! Zeile verschoben
        # Für Textanalysen extrahieren wir Text aus HTML #! Zeile verschoben
        processed_data = extract_text_from_html(raw_data) #! Zeile verschoben
        if processed_data is None: #! Zeile verschoben
             # TODO: app.logger muss noch verfügbar gemacht werden oder hier anders loggen #! TODO anpassen wegen logging
             # app.logger.error(f"Failed to extract text for monitor {monitor.id} from {monitor.data_source_url}")
             return None #! Zeile verschoben
        # TODO: Weitere Logik für andere Datenformate (z.B. JSON direkt parsen) #! TODO bleibt

    # TODO: Weitere 'analysis_type's und deren spezifische initiale Verarbeitung #! TODO bleibt

    # Wenn kein spezifischer Verarbeitungsschritt definiert ist, geben wir die Rohdaten zurück (oder None, je nach Design) #! Zeile verschoben
    if processed_data is None: #! Zeile verschoben
         # Für analysis_types, die keine initiale Verarbeitung benötigen (z.B. API, die direkt saubere Daten liefert) #! Zeile verschoben
         # Oder als Fallback, wenn der analysis_type unbekannt ist #! Zeile verschoben
         processed_data = raw_data #! Zeile verschoben


    return processed_data #! Zeile verschoben

# TODO: Funktion, die fetch_data_from_url und extract_text_from_html basierend auf Monitor-Konfiguration aufruft (Dieser TODO-Kommentar kann nun gelöscht werden, da process_monitor_data diese Rolle übernimmt.) #! Dieser TODO-Kommentar kann nun gelöscht werden
# Note: Die Logging-Aufrufe (app.logger.error etc.) müssen angepasst werden, da app in diesem Modul nicht direkt verfügbar ist. Späteres TODO. #! Neuer Hinweis wegen Logging   