# backend/models.py: Definitionen der Datenbankmodelle

from . import db #! Importiere db aus der __init__.py
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Datenbankmodell: User-Tabelle
# Erbt von db.Model (für SQLAlchemy) und UserMixin (für Flask-Login).
class User(UserMixin, db.Model):
    """
        Datenbankmodell für einen Benutzer.
        Repräsentiert die 'user' Tabelle in der SQLite-Datenbank.
        UserMixin stellt Standardimplementierungen für Eigenschaften
        und Methoden bereit, die von Flask-Login benötigt werden (z.B. is_authenticated).
        
        id:             Primärschlüssel, automatisch generiert und hochgezählt
        username:       Textfeld (String), muss einzigartig sein, darf nicht leer sein
        email:          Textfeld (String), muss einzigartig sein, darf nicht leer sein
        password_hash:  Speichert den gehashten String des Passworts.
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128)) # 128 für gehashte Passwörter, nicht unique
    """
        Relation zu den Monitor-Modellen dieses Benutzers
        'Monitor' bezieht sich auf den Namen der Monitor-Klasse in dieser Datei.
        'backref="owner"' erstellt eine 'owner'-Eigenschaft im Monitor-Objekt,
        die auf den Benutzer verweist.
        lazy='True' bedeutet, dass die Monitore bei Bedarf geladen werden.
    """
    monitors = db.relationship('Monitor', backref='owner', lazy=True)


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


# Datenbankmodell: Monitor-Tabelle
class Monitor(db.Model):
    """
        Datenbankmodell für einen Monitor.
        Speichert Konfigurationen für jeden Monitor eines Benutzers.
        
        id:                 Primärschlüssel für den Monitor
        user_id:            Fremdschlüssel, verknüpft diesen Monitor mit einem Benutzer.
        name:               Name des Monitors (z.B. "Sentiment Monitor für Twitter Feed")
        data_source_url:    Die URL oder Identifikator der Datenquelle
        analysis_type:      Die Art der durchzuführenden Analyse (z.B. 'sentiment', 'keywords')
        creation_date:      Datum und Uhrzeit der Erstellung des Monitors
        last_run:           Datum und Uhrzeit des letzten Laufs des Monitors
        is_active:          Ob der Monitor aktiv ist oder nicht
    """
    id = db.Column(db.Integer, primary_key=True)
    # 'user.id' bezieht sich auf den Namen der 'user' Tabelle (Kleinbuchstaben).
    # cascade="all, delete-orphan" sorgt dafür, dass Monitore gelöscht werden, wenn der zugehörige Benutzer gelöscht wird.
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    data_source_url = db.Column(db.String(255), nullable=False)
    analysis_type = db.Column(db.String(50), nullable=False)
    # default=datetime.utcnow setzt den Standardwert auf die aktuelle UTC-Zeit bei Erstellung
    creation_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_run = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    # TODO: Weitere Felder für spezifische Konfigurationen hinzufügen (z.B. Schwellenwerte für Benachrichtigungen)

    def __repr__(self):
        """
            Gibt eine lesbare String-Repräsentation des Monitor-Objekts zurück.
        """
        return f'<Monitor {self.name} by User {self.user_id}>'