import os
from functools import lru_cache

import polib
from dotenv import load_dotenv
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_babel import Babel, gettext
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.routing import BuildError
from flask_wtf import CSRFProtect
from authlib.integrations.flask_client import OAuth
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

load_dotenv()

# Supported languages
DEFAULT_LANGUAGE = 'en'
PREFIX_LANGUAGES = ['nl', 'pl', 'es', 'fr', 'de', 'ru']
LANGUAGES = [DEFAULT_LANGUAGE] + PREFIX_LANGUAGES
LANGUAGE_NAMES = {
    'en': 'English',
    'nl': 'Nederlands',
    'pl': 'Polski',
    'es': 'Espanol',
    'fr': 'Francais',
    'de': 'Deutsch',
    'ru': 'Русский',
}

app = Flask(__name__)
# use a randomly-generated secret key each time (for dev); replace with env var in prod
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24).hex())
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Google OAuth Configuration
app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')

# Flask-Mail Configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', True)
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@studyflow.com')

# initialize extensions
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
oauth = OAuth(app)
mail = Mail(app)

# Flask-Login Configuration
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

def validate_language(lang):
    """Validate language from route and return normalized value."""
    if lang is None:
        return DEFAULT_LANGUAGE
    if lang in LANGUAGES:
        return lang
    abort(404)


def get_current_language():
    """Language is derived from route path, never from session."""
    view_args = request.view_args or {}
    lang = view_args.get('lang')
    if lang in PREFIX_LANGUAGES:
        return lang
    if lang == DEFAULT_LANGUAGE:
        return DEFAULT_LANGUAGE
    return DEFAULT_LANGUAGE


def get_locale():
    """Locale selector used by Flask-Babel, aligned with route language."""
    return get_current_language()

babel = Babel(app, locale_selector=get_locale)


@lru_cache(maxsize=64)
def load_po_catalog(lang):
    """Load a msgid->msgstr dict from translations/<lang>/LC_MESSAGES/messages.po."""
    po_path = os.path.join(app.root_path, 'translations', lang, 'LC_MESSAGES', 'messages.po')
    if not os.path.exists(po_path):
        return {}

    try:
        catalog = {}
        for entry in polib.pofile(po_path):
            if entry.obsolete or not entry.msgid:
                continue
            if entry.msgstr:
                catalog[entry.msgid] = entry.msgstr
        return catalog
    except Exception:
        return {}


def translate_text(message, *args, **kwargs):
    """Translate with Babel first, then direct .po fallback for robustness."""
    lang = get_current_language()

    translated = message
    try:
        babel_value = gettext(message)
        if babel_value and babel_value != message:
            translated = babel_value
        else:
            translated = load_po_catalog(lang).get(message, message)
    except Exception:
        translated = load_po_catalog(lang).get(message, message)

    try:
        if kwargs:
            translated = translated % kwargs
        elif args:
            translated = translated % args
    except Exception:
        pass

    return translated


def localized_url(endpoint, lang=None, **values):
    """Build URLs that preserve language prefix (except English canonical routes)."""
    target_lang = validate_language(lang) if lang else get_current_language()
    cleaned_values = {k: v for k, v in values.items() if v is not None}

    if target_lang == DEFAULT_LANGUAGE:
        cleaned_values.pop('lang', None)
    else:
        cleaned_values['lang'] = target_lang

    return url_for(endpoint, **cleaned_values)


def switch_language_url(lang):
    """Build the current page URL in another language."""
    target_lang = validate_language(lang)
    endpoint = request.endpoint

    if not endpoint or endpoint == 'static':
        return localized_url('index', lang=target_lang)

    args = dict(request.view_args or {})
    args.pop('lang', None)

    try:
        base_url = localized_url(endpoint, lang=target_lang, **args)
    except BuildError:
        base_url = localized_url('index', lang=target_lang)

    if request.query_string:
        return f"{base_url}?{request.query_string.decode('utf-8')}"
    return base_url


def active_page():
    """Return endpoint name for active nav state."""
    return request.endpoint or ''


def parse_initial_words(raw_words):
    """Parse textarea lines in `word|description|example|disadvantage` format."""
    parsed_words = []
    if not raw_words:
        return parsed_words

    for line in raw_words.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue

        parts = [part.strip() for part in cleaned.split('|')]
        if not parts[0]:
            continue

        while len(parts) < 4:
            parts.append('')

        parsed_words.append(
            {
                'word': parts[0],
                'description': parts[1],
                'example': parts[2],
                'disadvantage': parts[3],
            }
        )

    return parsed_words


def asset_url(filename):
    """Static URL with per-file cache busting."""
    full_path = os.path.join(app.static_folder, filename)
    version = int(os.path.getmtime(full_path)) if os.path.exists(full_path) else 0
    return url_for('static', filename=filename, v=version)

# Register Google OAuth
google = None
if app.config['GOOGLE_CLIENT_ID'] and app.config['GOOGLE_CLIENT_SECRET']:
    google = oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    return User.query.get(int(user_id))


# ─── MODELS ───────────────────────────────────────────────

class User(UserMixin, db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=True)
    email    = db.Column(db.String(100), unique=True, nullable=True)
    password = db.Column(db.String(200), nullable=True)
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    lists    = db.relationship('WordList', backref='owner', lazy=True)


class WordList(db.Model):
    id      = db.Column(db.Integer, primary_key=True)
    name    = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    words   = db.relationship('Word', backref='word_list', lazy=True, cascade="all, delete-orphan")


class Word(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    word        = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    example     = db.Column(db.String(500))
    disadvantage= db.Column(db.String(500))
    list_id     = db.Column(db.Integer, db.ForeignKey('word_list.id'), nullable=False)


with app.app_context():
    db.create_all()


# ─── HELPERS ──────────────────────────────────────────────

def get_current_user():
    """Returns the logged-in User object, or None."""
    return current_user if current_user.is_authenticated else None


def send_welcome_email(user_email, username):
    """Send a welcome email to the new user."""
    try:
        msg = Message(
            subject='Welcome to StudyFlow',
            recipients=[user_email],
            html=f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <div style="background-color: #4f46e5; color: white; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 20px;">
                            <h1 style="margin: 0; font-size: 28px;">📚 Welcome to StudyFlow</h1>
                        </div>
                        
                        <p>Hi <strong>{username}</strong>,</p>
                        
                        <p>Thank you for joining StudyFlow! We're excited to help you learn faster and smarter.</p>
                        
                        <p>With StudyFlow, you can:</p>
                        <ul>
                            <li>Create custom study lists</li>
                            <li>Organize words and their meanings</li>
                            <li>Track your learning progress</li>
                            <li>Study efficiently with our interactive tools</li>
                        </ul>
                        
                        <p style="margin-top: 30px;">
                            <a href="https://studyflow.onrender.com/dashboard" style="display: inline-block; background-color: #4f46e5; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold;">Start Studying Now</a>
                        </p>
                        
                        <p style="margin-top: 30px; color: #666; font-size: 14px;">
                            If you have any questions, feel free to reply to this email.
                        </p>
                        
                        <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
                        
                        <p style="color: #999; font-size: 12px; text-align: center;">
                            StudyFlow &nbsp; | &nbsp; Learn Smarter, Not Harder
                        </p>
                    </div>
                </body>
            </html>
            """
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email to {user_email}: {str(e)}")
        return False


# ─── CONTEXT PROCESSOR ────────────────────────────────────
# Makes `current_user` and `get_locale` available in ALL templates automatically

@app.context_processor
def inject_globals():
    return dict(
        current_user=get_current_user(),
        get_locale=get_locale,
        get_current_language=get_current_language,
        localized_url=localized_url,
        switch_language_url=switch_language_url,
        active_page=active_page,
        language_names=LANGUAGE_NAMES,
        languages=LANGUAGES,
        default_language=DEFAULT_LANGUAGE,
        google_login_enabled=google is not None,
        asset_url=asset_url,
        _=translate_text,
    )


@login_manager.unauthorized_handler
def unauthorized():
    flash(translate_text('Please log in to continue.'), 'error')
    return redirect(localized_url('login', lang=get_current_language()))


@app.errorhandler(SQLAlchemyError)
def handle_db_error(error):
    db.session.rollback()
    flash(translate_text('A database error occurred. Please try again.'), 'error')
    return redirect(localized_url('index', lang=get_current_language()))


@app.errorhandler(500)
def handle_internal_error(error):
    flash(translate_text('Something went wrong. Please try again.'), 'error')
    return redirect(localized_url('index', lang=get_current_language()))


# ─── ROUTES ───────────────────────────────────────────────

@app.route("/", defaults={'lang': DEFAULT_LANGUAGE})
@app.route("/<lang>")
def index(lang):
    lang = validate_language(lang)
    # Auto redirect to dashboard if already logged in
    if current_user.is_authenticated:
        return redirect(localized_url('dashboard', lang=lang))
    return render_template("index.html")


@app.route("/register", defaults={'lang': DEFAULT_LANGUAGE}, methods=["GET", "POST"])
@app.route("/<lang>/register", methods=["GET", "POST"])
def register(lang):
    lang = validate_language(lang)
    if current_user.is_authenticated:
        return redirect(localized_url('dashboard', lang=lang))

    if request.method == "POST":
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        accepted_privacy = request.form.get('accept_privacy') == 'on'

        # Validation errors
        if not username or not email or not password:
            flash(translate_text('All fields are required.'), 'error')
        elif not accepted_privacy:
            flash(translate_text('You must accept the privacy policy to create an account.'), 'error')
        elif len(password) < 4:
            flash(translate_text('Password must be at least 4 characters long.'), 'error')
        elif not ('@' in email and '.' in email):
            flash(translate_text('Please enter a valid email address.'), 'error')
        elif User.query.filter_by(username=username).first():
            flash(translate_text('Username is already taken.'), 'error')
        elif User.query.filter_by(email=email).first():
            flash(translate_text('Email is already registered.'), 'error')
        else:
            # Create new user with email
            hashed = generate_password_hash(password)
            new_user = User(
                username=username,
                email=email,
                password=hashed
            )
            db.session.add(new_user)
            db.session.commit()
            
            # Send welcome email
            email_sent = send_welcome_email(email, username)
            if email_sent:
                flash(translate_text('Account created successfully! Check your email for a welcome message.'), 'success')
            else:
                flash(translate_text('Account created! (Welcome email could not be sent, but your account is ready.)'), 'info')
            
            return redirect(localized_url('login', lang=lang))

    return render_template("register.html")


@app.route("/login", defaults={'lang': DEFAULT_LANGUAGE}, methods=["GET", "POST"])
@app.route("/<lang>/login", methods=["GET", "POST"])
def login(lang):
    lang = validate_language(lang)
    if current_user.is_authenticated:
        return redirect(localized_url('dashboard', lang=lang))

    if request.method == "POST":
        identifier = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter(
            or_(User.username == identifier, User.email == identifier)
        ).first()

        if user and user.password and check_password_hash(user.password, password):
            login_user(user)
            return redirect(localized_url('dashboard', lang=lang))
        elif user and not user.password:
            flash(translate_text('This account uses Google sign-in. Please continue with Google.'), 'error')
        else:
            flash(translate_text('Invalid username/email or password.'), 'error')

    return render_template("login.html")


@app.route("/login/google", defaults={'lang': DEFAULT_LANGUAGE})
@app.route("/<lang>/login/google")
def login_google(lang):
    lang = validate_language(lang)
    """Redirect user to the Google OAuth login page."""
    if google is None:
        flash(translate_text('Google login is not configured yet. Please use username/password login.'), 'error')
        return redirect(localized_url('login', lang=lang))

    session['oauth_lang'] = lang
    redirect_uri = url_for('auth_google_callback_entry', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route("/auth/google/callback")
def auth_google_callback_entry():
    lang = validate_language(session.get('oauth_lang', DEFAULT_LANGUAGE))
    return auth_google_callback(lang)


@app.route("/login/google/authorized", defaults={'lang': DEFAULT_LANGUAGE})
@app.route("/<lang>/login/google/authorized")
def auth_google_callback(lang):
    lang = validate_language(lang)
    target_lang = validate_language(session.pop('oauth_lang', lang))
    """Handle the Google OAuth callback."""
    if google is None:
        flash(translate_text('Google login is not configured yet. Please use username/password login.'), 'error')
        return redirect(localized_url('login', lang=target_lang))

    try:
        # Retrieve the OAuth access token from Google
        token = google.authorize_access_token()
    except Exception:
        flash(translate_text('Failed to authorize with Google.'), 'error')
        return redirect(localized_url('login', lang=target_lang))
    
    try:
        # Fetch the user's Google profile information
        resp = google.get('userinfo')
        user_info = resp.json()
    except Exception:
        flash(translate_text('Could not retrieve user information from Google.'), 'error')
        return redirect(localized_url('login', lang=target_lang))
    
    # Extract email and name from user info
    email = user_info.get("email")
    name = user_info.get("name")
    google_id = user_info.get("sub")  # Google's unique user ID
    
    if not email or not google_id:
        flash(translate_text('Google account missing required information.'), 'error')
        return redirect(localized_url('login', lang=target_lang))
    
    # Check if user already exists by Google ID
    user = User.query.filter_by(google_id=google_id).first()
    
    if not user:
        # Check if email is already registered with username/password
        user = User.query.filter_by(email=email).first()
        
        if not user:
            safe_username = email.split('@')[0]
            base_username = safe_username or 'google_user'
            candidate = base_username
            suffix = 1
            while User.query.filter_by(username=candidate).first():
                suffix += 1
                candidate = f"{base_username}{suffix}"

            # Create a new user account
            user = User(
                email=email,
                google_id=google_id,
                username=candidate,
                password=None   # No password for Google OAuth users
            )
            db.session.add(user)
            db.session.commit()
            flash(translate_text('Account created successfully! You are now signed in with Google.'), 'success')
        else:
            user.google_id = user.google_id or google_id
            db.session.commit()
    
    # Log the user in using Flask-Login
    login_user(user)
    return redirect(localized_url('dashboard', lang=target_lang))


@app.route("/logout", defaults={'lang': DEFAULT_LANGUAGE})
@app.route("/<lang>/logout")
def logout(lang):
    lang = validate_language(lang)
    """Log out the current user."""
    logout_user()
    return redirect(localized_url('index', lang=lang))


@app.route("/contact", defaults={'lang': DEFAULT_LANGUAGE})
@app.route("/<lang>/contact")
def contact(lang):
    validate_language(lang)
    return render_template("contact.html")


@app.route("/privacy-policy", defaults={'lang': DEFAULT_LANGUAGE})
@app.route("/<lang>/privacy-policy")
def privacy_policy(lang):
    validate_language(lang)
    return render_template("privacy_policy.html")


@app.route("/dashboard", defaults={'lang': DEFAULT_LANGUAGE})
@app.route("/<lang>/dashboard")
@login_required
def dashboard(lang):
    validate_language(lang)
    user = get_current_user()
    lists = WordList.query.filter_by(user_id=user.id).order_by(WordList.id.desc()).all()
    return render_template("dashboard.html", lists=lists)


@app.route("/create_list", defaults={'lang': DEFAULT_LANGUAGE}, methods=["GET", "POST"])
@app.route("/<lang>/create_list", methods=["GET", "POST"])
@login_required
def create_list(lang):
    lang = validate_language(lang)
    if request.method == "POST":
        name = request.form.get('name', '').strip()
        initial_words_raw = request.form.get('initial_words', '').strip()
        if not name:
            flash(translate_text('List name is required.'), 'error')
        else:
            new_list = WordList(name=name, user_id=current_user.id)
            db.session.add(new_list)
            db.session.flush()

            initial_words = parse_initial_words(initial_words_raw)
            for item in initial_words:
                db.session.add(
                    Word(
                        word=item['word'],
                        description=item['description'],
                        example=item['example'],
                        disadvantage=item['disadvantage'],
                        list_id=new_list.id,
                    )
                )

            db.session.commit()
            flash(translate_text('List created successfully.'), 'success')
            return redirect(localized_url('dashboard', lang=lang))

    return render_template("create_list.html")


@app.route("/list/<int:list_id>/edit", defaults={'lang': DEFAULT_LANGUAGE}, methods=["GET", "POST"])
@app.route("/<lang>/list/<int:list_id>/edit", methods=["GET", "POST"])
@login_required
def edit_list(list_id, lang):
    lang = validate_language(lang)
    user = get_current_user()
    word_list = WordList.query.filter_by(id=list_id, user_id=user.id).first_or_404()

    if request.method == "POST":
        word        = request.form.get('word', '').strip()
        description = request.form.get('description', '').strip()
        example     = request.form.get('example', '').strip()
        disadvantage= request.form.get('disadvantage', '').strip()

        if not word:
            flash(translate_text('Word is required.'), 'error')
        else:
            new_word = Word(
                word=word,
                description=description,
                example=example,
                disadvantage=disadvantage,
                list_id=list_id
            )
            db.session.add(new_word)
            db.session.commit()
            flash(translate_text('Word added successfully.'), 'success')
            return redirect(localized_url('edit_list', lang=lang, list_id=list_id))

    words = Word.query.filter_by(list_id=list_id).all()
    return render_template("edit_list.html", word_list=word_list, words=words)


@app.route("/list/<int:list_id>/flashcards", defaults={'lang': DEFAULT_LANGUAGE})
@app.route("/<lang>/list/<int:list_id>/flashcards")
@login_required
def flashcards(list_id, lang):
    validate_language(lang)
    user = get_current_user()
    word_list = WordList.query.filter_by(id=list_id, user_id=user.id).first_or_404()
    words = Word.query.filter_by(list_id=list_id).all()
    words_data = [
        {
            'word': w.word,
            'description': w.description,
            'example': w.example,
            'disadvantage': w.disadvantage,
        }
        for w in words
    ]
    return render_template("flashcards.html", word_list=word_list, words=words, words_data=words_data)


@app.route("/list/<int:list_id>/quiz", defaults={'lang': DEFAULT_LANGUAGE})
@app.route("/<lang>/list/<int:list_id>/quiz")
@login_required
def quiz(list_id, lang):
    validate_language(lang)
    user = get_current_user()
    word_list = WordList.query.filter_by(id=list_id, user_id=user.id).first_or_404()
    words = Word.query.filter_by(list_id=list_id).all()
    study_words = [w for w in words if (w.description or '').strip()]
    words_data = [
        {
            'word': w.word,
            'description': w.description,
            'example': w.example,
            'disadvantage': w.disadvantage,
        }
        for w in study_words
    ]
    return render_template("quiz.html", word_list=word_list, words=study_words, words_data=words_data)


@app.route("/list/<int:list_id>/multiple-choice", defaults={'lang': DEFAULT_LANGUAGE})
@app.route("/<lang>/list/<int:list_id>/multiple-choice")
@login_required
def multiple_choice(list_id, lang):
    validate_language(lang)
    user = get_current_user()
    word_list = WordList.query.filter_by(id=list_id, user_id=user.id).first_or_404()
    words = Word.query.filter_by(list_id=list_id).all()
    study_words = [w for w in words if (w.description or '').strip()]
    words_data = [
        {
            'word': w.word,
            'description': w.description,
            'example': w.example,
            'disadvantage': w.disadvantage,
        }
        for w in study_words
    ]
    return render_template("multiple_choice.html", word_list=word_list, words=study_words, words_data=words_data)


@app.route("/list/<int:list_id>/delete_word/<int:word_id>", defaults={'lang': DEFAULT_LANGUAGE}, methods=["POST"])
@app.route("/<lang>/list/<int:list_id>/delete_word/<int:word_id>", methods=["POST"])
@login_required
def delete_word(list_id, word_id, lang):
    lang = validate_language(lang)
    user = get_current_user()
    # Make sure the list belongs to this user
    WordList.query.filter_by(id=list_id, user_id=user.id).first_or_404()
    word = Word.query.filter_by(id=word_id, list_id=list_id).first_or_404()
    db.session.delete(word)
    db.session.commit()
    return redirect(localized_url('edit_list', lang=lang, list_id=list_id))


@app.route("/set_language/<lang>")
def set_language(lang):
    """Legacy language switch endpoint kept for backward compatibility."""
    if lang not in LANGUAGES:
        lang = DEFAULT_LANGUAGE
    return redirect(localized_url('index', lang=lang))


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)