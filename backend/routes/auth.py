# backend/routes/auth.py: Blueprint für Authentifizierungs-Routen

from flask import Blueprint, render_template, url_for, redirect, request, flash #! Importiere Flask-Funktionen
from flask_login import login_user, logout_user, current_user, login_required #! Importiere Flask-Login Funktionen
from werkzeug.security import generate_password_hash, check_password_hash #! Importiere Sicherheitsfunktionen

# Importiere das db-Objekt und das User-Modell aus den übergeordneten Paketen
# Die Punkte (..) navigieren ein Verzeichnis hoch (von 'routes' nach 'backend')
from .. import db #! Importiere db aus backend/__init__.py
from ..models import User #! Importiere User aus backend/models.py

# Erstelle einen Blueprint für Authentifizierungs-Routen
# 'auth_bp' ist der Name des Blueprints
# url_prefix='/auth' kann optional hinzugefügt werden, um allen Routen ein Präfix zu geben (hier nicht gemacht, da /register, /login globale Pfade sind)
auth_bp = Blueprint('auth', __name__) #! Definiere den Blueprint


# Routen-Definition: Registrierung
@auth_bp.route('/register', methods=['GET', 'POST']) #! Route definiert auf Blueprint
def register():
    """
    Ansichtsfunktion für die Benutzerregistrierung.
    Handelt GET zur Anzeige des Formulars (TODO: Template) und POST zur Verarbeitung.
    Erwartet 'username', 'email', 'password' im POST-Request.
    Gibt Weiterleitung oder Fehlermeldungen zurück.
    """
    if current_user.is_authenticated:
        flash('You are already registered and logged in.', 'info')
        return redirect(url_for('index')) # TODO: 'index' Route anpassen falls nötig

    if request.method == 'POST':
        # Grundlegende Validierung (TODO: Erweiterte Validierung mit Flask-WTF)
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('auth.register')) #! Redirect zur Blueprint-Route

        # Prüfen, ob Benutzer oder E-Mail bereits existieren
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or Email already exists.', 'danger')
            return redirect(url_for('auth.register')) #! Redirect zur Blueprint-Route

        # Neuen Benutzer erstellen
        new_user = User(username=username, email=email)
        new_user.set_password(password) # Passwort hashen und setzen

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login')) #! Redirect zur Blueprint-Route
        except Exception as e:
            db.session.rollback() # Änderungen zurücknehmen im Fehlerfall
            flash(f'Registration failed: {e}', 'danger')
            return redirect(url_for('auth.register')) #! Redirect zur Blueprint-Route


    # TODO: Echtes Registrierungs-Template für GET rendern
    return "<h1>Registration Page (Placeholder)</h1><form method='POST'><input type='text' name='username' placeholder='Username'><br><input type='email' name='email' placeholder='Email'><br><input type='password' name='password' placeholder='Password'><br><button type='submit'>Register</button></form>"


# Routen-Definition: Login
@auth_bp.route('/login', methods=['GET', 'POST']) #! Route definiert auf Blueprint
def login():
    """
    Ansichtsfunktion für den Benutzer-Login.
    Handelt GET zur Anzeige des Formulars (TODO: Template) und POST zur Verarbeitung.
    Erwartet 'username', 'password' und optional 'remember' im POST-Request.
    Gibt Weiterleitung oder Fehlermeldungen zurück.
    """
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for('index')) # TODO: 'index' Route anpassen falls nötig

    if request.method == 'POST':
        # Grundlegende Validierung (TODO: Erweiterte Validierung mit Flask-WTF)
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False # Checkbox für 'Angemeldet bleiben'

        if not username or not password:
             flash('Username and password are required.', 'danger')
             return redirect(url_for('auth.login')) #! Redirect zur Blueprint-Route


        # Benutzer anhand des Benutzernamens laden
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            # Benutzer mit Flask-Login einloggen
            login_user(user, remember=remember) # remember=True/False
            # Weiterleitung nach erfolgreichem Login (TODO: Nächsten Bereich bestimmen)
            next_page = request.args.get('next')
            flash('Logged in successfully.', 'success')
            return redirect(next_page or url_for('index')) # TODO: 'index' Route anpassen falls nötig

        flash('Invalid username or password.', 'danger')
        # TODO: Formular mit Fehlern erneut anzeigen

    # TODO: Echtes Login-Template für GET rendern
    return "<h1>Login Page (Placeholder)</h1><form method='POST'><input type='text' name='username' placeholder='Username'><br><input type='password' name='password' placeholder='Password'><br><label><input type='checkbox' name='remember'> Remember Me</label><br><button type='submit'>Login</button></form>"


# Routen-Definition: Logout
@auth_bp.route('/logout') #! Route definiert auf Blueprint
@login_required # Stellt sicher, dass nur eingeloggte Benutzer diese Route aufrufen können
def logout():
    """
    Ansichtsfunktion für den Benutzer-Logout.
    Loggt den aktuellen Benutzer mithilfe von Flask-Login aus.
    """
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index')) # TODO: 'index' Route anpassen falls nötig


# Routen-Definition: Geschützte Dashboard Route (Beispiel)
@auth_bp.route('/dashboard') #! Route definiert auf Blueprint
@login_required # Dieser Decorator schützt die Route
def dashboard():
    """
    Beispiel für eine geschützte Route.
    Nur eingeloggte Benutzer können diese Seite sehen.
    """
    return f"<h1>Welcome to the Dashboard, {current_user.username}!</h1><p>This is a protected area.</p><p><a href='{url_for('auth.logout')}'>Logout</a></p>" #! Link zur Blueprint-Route