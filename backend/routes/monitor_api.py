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
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# Importiere NLTK Module für Tokenisierung, Stopwords und Frequenzanalyse
from nltk.tokenize import word_tokenize #! Importiere word_tokenize
from nltk.corpus import stopwords #! Importiere stopwords
from nltk import FreqDist #! Importiere FreqDist

# Importiere das db-Objekt und die Modelle aus den übergeordneten Paketen
from .. import db
from ..models import Monitor, User

# Erstelle einen Blueprint für Monitor API Routen
monitor_api_bp = Blueprint('monitor_api', __name__, url_prefix='/api')

# Initialisiere den VADER SentimentIntensityAnalyzer
analyzer = SentimentIntensityAnalyzer()

# Lade die Stopwords für Englisch (könnte in __init__ besser sein, aber für jetzt hier)
# TODO: Stopwords besser laden, z.B. im App-Kontext oder globaler #! Neuer TODO
try: #! Füge Try-Block hinzu für den Fall, dass Stopwords nicht geladen wurden
    stop_words = set(stopwords.words('english')) #! Lade englische Stopwords
except LookupError: #! Füge Exception Handling hinzu
    # Handle den Fall, dass Stopwords nicht heruntergeladen wurden
    print("NLTK 'stopwords' data not found. Please run: python -m nltk.downloader stopwords") #! Gib Hinweis aus
    stop_words = set() #! Leeres Set als Fallback

# TODO: Füge Stopwords für andere Sprachen hinzu, falls nötig #! Neuer TODO


# --- API Routen für Monitor CRUD (Create, Read, Update, Delete) ---
# (Diese Routen bleiben hier)
@monitor_api_bp.route('/monitors', methods=['GET', 'POST'])
@login_required
def manage_monitors():
    """ API Endpunkt zur Verwaltung von Monitoren (Liste abrufen, neuen Monitor erstellen). """
    # ... unverändert ...
    if request.method == 'GET':
        monitors = current_user.monitors
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
        data = request.get_json()
        if not data or not data.get('name') or not data.get('data_source_url') or not data.get('analysis_type'):
            return jsonify({"error": "Missing required monitor data (name, data_source_url, analysis_type)"}), 400
        name = data.get('name')
        data_source_url = data.get('data_source_url')
        analysis_type = data.get('analysis_type')
        # TODO: Erweiterte Validierung
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
            # TODO: app.logger loggen
            # app.logger.error(f"Error creating monitor: {e}")
            return jsonify({"error": "Failed to create monitor due to internal error."}), 500

@monitor_api_bp.route('/monitors/<int:monitor_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_single_monitor(monitor_id):
    """ API Endpunkt zur Verwaltung eines einzelnen Monitors anhand seiner ID. """
    # ... unverändert ...
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
        if 'name' in data: monitor.name = data['name']
        if 'data_source_url' in data: monitor.data_source_url = data['data_source_url']
        if 'analysis_type' in data: monitor.analysis_type = data['analysis_type']
        if 'is_active' in data:
            if isinstance(data['is_active'], bool): monitor.is_active = data['is_active']
            else: return jsonify({"error": "is_active must be a boolean value"}), 400
        # TODO: Erweiterte Validierung
        try:
            db.session.commit()
            return jsonify({
                'id': monitor.id, 'name': monitor.name, 'data_source_url': monitor.data_source_url,
                'analysis_type': monitor.analysis_type,
                'creation_date': monitor.creation_date.isoformat() if monitor.creation_date else None,
                'last_run': monitor.last_run.isoformat() if monitor.last_run else None,
                'is_active': monitor.is_active, 'user_id': monitor.user_id
            })
        except Exception as e:
            db.session.rollback()
            # TODO: app.logger loggen
            # app.logger.error(f"Error updating monitor {monitor_id}: {e}")
            return jsonify({"error": "Failed to update monitor due to internal error."}), 500

    elif request.method == 'DELETE':
        try:
            db.session.delete(monitor)
            db.session.commit()
            return jsonify({"message": f"Monitor {monitor_id} deleted successfully."}), 200
        except Exception as e:
            db.session.rollback()
            # TODO: app.logger loggen
            # app.logger.error(f"Error deleting monitor {monitor_id}: {e}")
            return jsonify({"error": "Failed to delete monitor due to internal error."}), 500

# --- Logik für Datenabruf und initiale Verarbeitung (Schritt 2.3) ---
# ... (fetch_data_from_url, extract_text_from_html bleiben unverändert) ...
def fetch_data_from_url(url):
    """ Holt Daten von einer gegebenen URL. ... """
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        # TODO: app.logger loggen
        # app.logger.error(f"Error fetching data from {url}: {e}")
        return None

def extract_text_from_html(html_content):
    """ Extrahiert Text aus HTML-Inhalt. ... """
    if not html_content: return None
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        for script in soup(["script", "style"]): script.extract()
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        return text
    except Exception as e:
        # TODO: app.logger loggen
        # app.logger.error(f"Error extracting text from HTML: {e}")
        return None

def perform_sentiment_analysis_with_vader(text):
    """ Führt Sentiment-Analyse mit NLTK VADER auf gegebenem Text durch. """
    if not text: return None
    vs = analyzer.polarity_scores(text)
    return vs['compound'] # Gib das Compound-Score zurück

def perform_keyword_extraction_with_nltk(text, num_keywords=10): #! Neue Funktion für Keyword Extraktion
    """ #! Neuer Docstring
    Führt einfache Stichwort-Extraktion mit NLTK durch (Tokenisierung, Stopwords entfernen, Frequenz). #! Neuer Docstring
    Gibt eine Liste der häufigsten Nicht-Stopwords zurück. #! Neuer Docstring
    """ #! Ende neuer Docstring
    if not text: #! Neue Zeile
        return [] #! Neue Zeile
    # Konvertiere den Text in Kleinbuchstaben #! Neue Zeile
    text = text.lower() #! Neue Zeile
    # Tokenisiere den Text in Wörter #! Neue Zeile
    tokens = word_tokenize(text) #! Neue Zeile
    # Entferne Stopwords und nicht-alphanumerische Tokens #! Neue Zeile
    filtered_tokens = [word for word in tokens if word.isalpha() and word not in stop_words] #! Neue Zeile
    # Finde die Verteilung der Frequenzen #! Neue Zeile
    fdist = FreqDist(filtered_tokens) #! Neue Zeile
    # Gib die häufigsten Tokens als Keywords zurück #! Neue Zeile
    return [word for word, frequency in fdist.most_common(num_keywords)] #! Neue Zeile


def process_monitor_data(monitor: Monitor):
    """
    Verarbeitet Daten für einen gegebenen Monitor basierend auf seiner Konfiguration.
    Holt Daten, führt initiale Verarbeitung und AI-Analyse durch.
    Gibt die Analyseergebnisse als Dictionary zurück oder None bei Fehlern.
    """
    if not monitor or not monitor.data_source_url:
        # TODO: app.logger loggen
        # app.logger.warning("process_monitor_data called with invalid monitor or missing URL.")
        return None

    raw_data = fetch_data_from_url(monitor.data_source_url)
    if raw_data is None:
        # fetch_data_from_url hat den Fehler bereits geloggt
        return None

    processed_data = None
    analysis_results = {} #! Initialisiere analysis_results als Dictionary


    # Schritt 1: Initiale Verarbeitung
    if monitor.data_source_url.startswith('http'):
         processed_data = extract_text_from_html(raw_data)
         if processed_data is None:
              # TODO: app.logger loggen
              # app.logger.error(f"Failed to extract text for monitor {monitor.id} from {monitor.data_source_url}")
              return None #! Rückgabe bei Fehler bei Textextraktion
    else:
         # TODO: Behandlung anderer Datenquellen
         processed_data = raw_data

    if not processed_data:
         # TODO: app.logger loggen
         return None #! Rückgabe, wenn keine Daten für Analyse verfügbar sind


    # Schritt 2: AI-Analyse basierend auf analysis_type
    if monitor.analysis_type == 'sentiment':
        if isinstance(processed_data, str):
             sentiment_score = perform_sentiment_analysis_with_vader(processed_data)
             analysis_results["sentiment_compound"] = sentiment_score #! Füge Sentiment Ergebnis zum Dictionary hinzu

        else:
             # TODO: app.logger loggen
             pass

    elif monitor.analysis_type == 'keywords': #! Füge Bedingung für Keyword Analyse hinzu
        if isinstance(processed_data, str): #! Prüfe, ob processed_data ein String ist
             keywords = perform_keyword_extraction_with_nltk(processed_data) #! Rufe Keyword Extraktion auf
             analysis_results["keywords"] = keywords #! Füge Keyword Ergebnis zum Dictionary hinzu
        else: #! Neue Zeile
             # TODO: app.logger loggen
             pass #! Neue Zeile

    # TODO: Weitere analysis_type implementieren

    # Gib die Ergebnisse der Analyse als Dictionary zurück
    return analysis_results


# --- Endpunkt für n8n Trigger (Schritt 2.4) ---
# ... (trigger_monitor_processing bleibt unverändert, ruft process_monitor_data auf und gibt dessen Ergebnis zurück) ...
@monitor_api_bp.route('/monitors/trigger', methods=['POST'])
def trigger_monitor_processing():
    """ API Endpunkt, den n8n aufruft, um die Verarbeitung eines Monitors anzustoßen. ... """
    # API-Schlüssel Authentifizierung
    api_key_header = request.headers.get('X-API-KEY')
    expected_api_key = os.getenv('N8N_API_KEY')
    if not api_key_header or api_key_header != expected_api_key:
        return jsonify({"error": "Unauthorized: Invalid or missing API key"}), 401

    # Hole die Monitor-ID
    data = request.get_json()
    if not data or 'monitor_id' not in data:
        return jsonify({"error": "Missing 'monitor_id' in request body"}), 400
    monitor_id = data.get('monitor_id')

    # Hole den Monitor
    monitor = Monitor.query.get(monitor_id)
    if not monitor:
        return jsonify({"error": f"Monitor with ID {monitor_id} not found"}), 404

    # TODO: Optional prüfen, ob der Monitor aktiv ist

    try:
        # Starte den Verarbeitungsprozess
        analysis_results = process_monitor_data(monitor)

        if analysis_results is None or not analysis_results: #! Passe Prüfung auf leeres Dictionary an
             # process_monitor_data gibt None bei Fehler oder leeres Dictionary zurück, wenn keine Analyse möglich war/Daten fehlten
             # TODO: Genauere Fehlermeldung je nach Rückgabe von process_monitor_data
             return jsonify({"error": f"Failed to process data or perform analysis for monitor {monitor_id}. No results."}), 500 #! Angepasste Fehlermeldung

        # TODO: Speichere Analyseergebnisse in DB (Phase 4) oder erstelle Benachrichtigung

        # Gib die Analyseergebnisse zurück
        return jsonify({
            "message": f"Processing triggered successfully for monitor {monitor_id}",
            "analysis_results": analysis_results # Gibt das Dictionary zurück
        }), 200

    except Exception as e:
        # Allgemeine Fehlerbehandlung
        # TODO: app.logger loggen
        # app.logger.error(f"Error processing trigger for monitor {monitor_id}: {e}")
        return jsonify({"error": f"An error occurred during processing trigger for monitor {monitor_id}. Error: {e}"}), 500

# TODO: Logging-Aufrufe anpassen