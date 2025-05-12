# backend/routes/monitor_api.py: Blueprint für Monitor API Routen
# Enthält Routen für CRUD-Operationen auf Monitoren und die Datenverarbeitungslogik.

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from datetime import datetime

import requests
from bs4 import BeautifulSoup
import os

# Importiere die VADER SentimentIntensityAnalyzer
from nltk.sentiment.vader import SentimentIntensityAnalyzer #! Importiere VADER

# Importiere das db-Objekt und die Modelle aus den übergeordneten Paketen
from .. import db
from ..models import Monitor, User

# Erstelle einen Blueprint für Monitor API Routen
monitor_api_bp = Blueprint('monitor_api', __name__, url_prefix='/api')


# Initialisiere den VADER SentimentIntensityAnalyzer
# Diesen Analyzer können wir wiederverwenden, er muss nicht bei jeder Analyse neu erstellt werden
analyzer = SentimentIntensityAnalyzer() #! Initialisiere VADER Analyzer


# --- API Routen für Monitor CRUD (Create, Read, Update, Delete) ---

@monitor_api_bp.route('/monitors', methods=['GET', 'POST'])
@login_required
def manage_monitors():
    """
    API Endpunkt zur Verwaltung von Monitoren (Liste abrufen, neuen Monitor erstellen).
    ...
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
                'creation_date': monitor.creation_date.isoformat() if monitor.creation_date else None,
                'last_run': monitor.last_run.isoformat() if monitor.last_run else None,
                'is_active': monitor.is_active,
            })

        return jsonify(monitors_data)

    elif request.method == 'POST':
        # Erwarte JSON-Daten vom Frontend
        data = request.get_json()

        # Grundlegende Validierung der JSON-Daten
        if not data or not data.get('name') or not data.get('data_source_url') or not data.get('analysis_type'):
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
            user_id=current_user.id
        )

        try:
            db.session.add(new_monitor)
            db.session.commit()

            return jsonify({
                'id': new_monitor.id,
                'name': new_monitor.name,
                'data_source_url': new_monitor.data_source_url,
                'analysis_type': new_monitor.analysis_type,
                'creation_date': new_monitor.creation_date.isoformat() if new_monitor.creation_date else None,
                'last_run': new_monitor.last_run.isoformat() if new_monitor.last_run else None,
                'is_active': new_monitor.is_active,
                'user_id': new_monitor.user_id
            }), 201

        except IntegrityError:
             db.session.rollback()
             return jsonify({"error": "Database integrity error."}), 500

        except Exception as e:
            db.session.rollback()
            # TODO: app.logger muss noch verfügbar gemacht werden oder hier anders loggen
            # app.logger.error(f"Error creating monitor: {e}")
            return jsonify({"error": "Failed to create monitor due to internal error."}), 500


@monitor_api_bp.route('/monitors/<int:monitor_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_single_monitor(monitor_id):
    """
    API Endpunkt zur Verwaltung eines einzelnen Monitors anhand seiner ID.
    ...
    """
    monitor = Monitor.query.filter_by(id=monitor_id, user_id=current_user.id).first()

    if not monitor:
        return jsonify({"error": "Monitor not found or does not belong to the current user"}), 404

    if request.method == 'GET':
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
        data = request.get_json()

        if not data:
             return jsonify({"error": "No update data provided"}), 400

        if 'name' in data:
            monitor.name = data['name']
        if 'data_source_url' in data:
            monitor.data_source_url = data['data_source_url']
        if 'analysis_type' in data:
            monitor.analysis_type = data['analysis_type']
        if 'is_active' in data:
            if isinstance(data['is_active'], bool):
                monitor.is_active = data['is_active']
            else:
                return jsonify({"error": "is_active must be a boolean value"}), 400

        try:
            db.session.commit()
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
            db.session.delete(monitor)
            db.session.commit()
            return jsonify({"message": f"Monitor {monitor_id} deleted successfully."}), 200

        except Exception as e:
            db.session.rollback()
            # TODO: app.logger muss noch verfügbar gemacht werden oder hier anders loggen
            # app.logger.error(f"Error deleting monitor {monitor_id}: {e}")
            return jsonify({"error": "Failed to delete monitor due to internal error."}), 500


# --- Logik für Datenabruf und initiale Verarbeitung (Schritt 2.3) ---

def fetch_data_from_url(url):
    """
    Holt Daten von einer gegebenen URL.
    ...
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        # TODO: app.logger muss noch verfügbar gemacht werden oder hier anders loggen
        # app.logger.error(f"Error fetching data from {url}: {e}")
        return None


def extract_text_from_html(html_content):
    """
    Extrahiert Text aus HTML-Inhalt.
    ...
    """
    if not html_content:
        return None
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        for script in soup(["script", "style"]):
            script.extract()
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        return text
    except Exception as e:
        # TODO: app.logger muss noch verfügbar gemacht werden oder hier anders loggen
        # app.logger.error(f"Error extracting text from HTML: {e}")
        return None


def perform_sentiment_analysis_with_vader(text): #! Neue Funktion für VADER Analyse
    """ #! Neuer Docstring
    Führt Sentiment-Analyse mit NLTK VADER auf gegebenem Text durch. #! Neuer Docstring
    Gibt das Compound-Sentiment-Score zurück. #! Neuer Docstring
    """ #! Ende neuer Docstring
    if not text: #! Neue Zeile
        return None #! Neue Zeile
    # analyzer wurde global initialisiert #! Neue Zeile
    vs = analyzer.polarity_scores(text) #! Neue Zeile
    # Das Compound-Score ist ein gängiger Indikator für die Gesamtstimmung #! Neue Zeile
    return vs['compound'] #! Neue Zeile


def process_monitor_data(monitor: Monitor):
    """
    Verarbeitet Daten für einen gegebenen Monitor basierend auf seiner Konfiguration.
    Holt Daten von der data_source_url, führt initiale Verarbeitung durch
    und wendet AI-Analyse (z.B. Sentiment) basierend auf analysis_type an.
    Gibt die Analyseergebnisse zurück oder None bei Fehlern.
    """
    if not monitor or not monitor.data_source_url:
        # TODO: app.logger muss noch verfügbar gemacht werden oder hier anders loggen
        # app.logger.warning("process_monitor_data called with invalid monitor or missing URL.")
        return None

    raw_data = fetch_data_from_url(monitor.data_source_url)
    if raw_data is None:
        # fetch_data_from_url hat den Fehler bereits geloggt (TODO: Anpassung wegen Logging)
        return None

    processed_data = None #! Initialisiere processed_data
    analysis_results = None #! Initialisiere analysis_results

    # Schritt 1: Initiale Verarbeitung (Text-Extraktion für Webseiten)
    if monitor.data_source_url.startswith('http'): #! Beispielhafte Bedingung für Webseiten
         processed_data = extract_text_from_html(raw_data)
         if processed_data is None:
              # TODO: app.logger muss noch verfügbar gemacht werden oder hier anders loggen
              # app.logger.error(f"Failed to extract text for monitor {monitor.id} from {monitor.data_source_url}")
              return None #! Gib None zurück, wenn Textextraktion fehlschlägt
    else:
         # TODO: Behandlung anderer Datenquellen, z.B. direkte API-Antwort (JSON/Text)
         processed_data = raw_data #! Vorläufig: Rohdaten als processed_data verwenden, falls keine Extraktion nötig ist

    if not processed_data: #! Prüfe, ob nach der Verarbeitung Daten vorhanden sind
         # TODO: app.logger loggen, dass keine verarbeiteten Daten für Analyse verfügbar sind
         return None #! Gib None zurück, wenn keine Daten für Analyse da sind


    # Schritt 2: AI-Analyse basierend auf analysis_type
    if monitor.analysis_type == 'sentiment': #! Führe Sentiment-Analyse durch, wenn Typ 'sentiment'
        # Stelle sicher, dass wir Textdaten haben, bevor wir Sentiment-Analyse durchführen
        if isinstance(processed_data, str): #! Prüfe, ob processed_data ein String ist
             sentiment_score = perform_sentiment_analysis_with_vader(processed_data) #! Rufe VADER Analyse auf
             analysis_results = {"sentiment_compound": sentiment_score} #! Speichere Ergebnis im Dictionary

        else: #! Neue Zeile
             # TODO: app.logger loggen, dass Sentiment-Analyse Textdaten benötigt, aber keine erhalten hat
             pass #! Neue Zeile

    elif monitor.analysis_type == 'keywords': #! Beispiel für andere Analyse
        # TODO: Implementiere Keyword-Extraktion (z.B. mit NLTK oder spaCy NER, falls doch spaCy installiert wird)
        # Vorerst nur ein Platzhalter
        analysis_results = {"keywords": ["TODO: Implementierung", "Keywords"]} #! Platzhalter Ergebnis
        pass #! Platzhalter

    # TODO: Weitere analysis_type implementieren


    # Gib die Ergebnisse der Analyse zurück (nicht die processed_data selbst, die groß sein kann)
    # In Phase 4 werden wir diese Ergebnisse in der Datenbank speichern.
    return analysis_results #! Gib das Analyseergebnis-Dictionary zurück


# --- Endpunkt für n8n Trigger (Schritt 2.4) ---

@monitor_api_bp.route('/monitors/trigger', methods=['POST'])
def trigger_monitor_processing():
    """
    API Endpunkt, den n8n aufruft, um die Verarbeitung eines Monitors anzustoßen.
    ...
    """
    # API-Schlüssel Authentifizierung
    api_key_header = request.headers.get('X-API-KEY')
    expected_api_key = os.getenv('N8N_API_KEY')

    if not api_key_header or api_key_header != expected_api_key:
        return jsonify({"error": "Unauthorized: Invalid or missing API key"}), 401

    # Hole die Monitor-ID aus dem Request Body
    data = request.get_json()
    if not data or 'monitor_id' not in data:
        return jsonify({"error": "Missing 'monitor_id' in request body"}), 400

    monitor_id = data.get('monitor_id')

    # Hole den Monitor aus der Datenbank
    monitor = Monitor.query.get(monitor_id)

    if not monitor:
        return jsonify({"error": f"Monitor with ID {monitor_id} not found"}), 404

    # TODO: Optional prüfen, ob der Monitor aktiv ist (monitor.is_active)

    try:
        # Starte den Datenabruf- und Verarbeitungsprozess für diesen Monitor
        # Die process_monitor_data Funktion gibt die Analyseergebnisse zurück
        analysis_results = process_monitor_data(monitor) #! Erfasse die Analyseergebnisse

        if analysis_results is None:
             # process_monitor_data hat Fehler geloggt, falls etwas schiefging
             # Gib einen Fehler zurück, wenn die Verarbeitung fehlschlug (z.B. keine Daten extrahiert)
             return jsonify({"error": f"Failed to process data for monitor {monitor_id} or no data available for analysis."}), 500 #! Angepasste Fehlermeldung

        # TODO: Rufe hier die AI-Analysefunktion auf (ist jetzt in process_monitor_data) und verarbeite das Ergebnis (Ergebnis kommt jetzt aus process_monitor_data)

        # TODO: Speichere Analyseergebnisse in der Datenbank (Phase 4) oder erstelle Benachrichtigung (später in Phase 4)

        # Gib die Analyseergebnisse zurück
        return jsonify({ #! Passe Rückgabe an
            "message": f"Processing triggered successfully for monitor {monitor_id}",
            "analysis_results": analysis_results #! Gib die Analyseergebnisse zurück
        }), 200

    except Exception as e:
        # Allgemeine Fehlerbehandlung während des Trigger-Prozesses
        # TODO: app.logger muss noch verfügbar gemacht werden oder hier anders loggen
        # app.logger.error(f"Error processing trigger for monitor {monitor_id}: {e}")
        return jsonify({"error": f"An error occurred during processing trigger for monitor {monitor_id}. Error: {e}"}), 500 #! Füge Fehlerdetails hinzu

# TODO: Note: Die Logging-Aufrufe (app.logger.error etc.) müssen angepasst werden, da app in diesem Modul nicht direkt verfügbar ist. Eine mögliche Lösung ist, das Logger-Objekt von app.py an die Funktionen zu übergeben oder eine separate Logging-Konfiguration zu verwenden.