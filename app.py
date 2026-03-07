import os
from dotenv import load_dotenv

from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_babel import Babel, gettext, lazy_gettext as _l
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import CSRFProtect
from authlib.integrations.flask_client import OAuth

load_dotenv()

# Supported languages
LANGUAGES = ['en', 'nl', 'pl', 'es', 'fr', 'ru']

app = Flask(__name__)
# use a randomly-generated secret key each time (for dev); replace with env var in prod
app.secret_key = os.urandom(24)
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
babel = Babel(app)

# Locale selector for Flask-Babel
def get_locale():
    """Select user language from session, then browser, then default."""
    # First check if user has selected a language in session
    lang = session.get('language')
    if lang in LANGUAGES:
        return lang
    # Fall back to browser language preference
    return request.accept_languages.best_match(LANGUAGES) or 'en'

babel.locale_selector_func = get_locale

# Register Google OAuth
google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)


# ─── MODELS ───────────────────────────────────────────────

class User(db.Model):
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
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

def login_required(f):
    """Simple login guard — use as a manual check or wrap routes."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


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
# Makes `current_user` available in ALL templates automatically

@app.context_processor
def inject_user():
    return dict(current_user=get_current_user())


# ─── ROUTES ───────────────────────────────────────────────

@app.route("/")
def index():
    # Auto redirect to dashboard if already logged in
    if get_current_user():
        return redirect(url_for('dashboard'))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if get_current_user():
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        # Validation errors
        if not username or not email or not password:
            flash('All fields are required.', 'error')
        elif len(password) < 4:
            flash('Password must be at least 4 characters long.', 'error')
        elif not ('@' in email and '.' in email):
            flash('Please enter a valid email address.', 'error')
        elif User.query.filter_by(username=username).first():
            flash('Username is already taken.', 'error')
        elif User.query.filter_by(email=email).first():
            flash('Email is already registered.', 'error')
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
                flash('Account created successfully! Check your email for a welcome message.', 'success')
            else:
                flash('Account created! (Welcome email could not be sent, but your account is ready.)', 'info')
            
            return redirect(url_for('login'))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if get_current_user():
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        else:
            pass

    return render_template("login.html")


@app.route("/login/google")
def login_google():
    """Redirect user to the Google OAuth login page."""
    redirect_uri = url_for('auth_google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route("/auth/google/callback")
def auth_google_callback():
    """Handle the Google OAuth callback."""
    try:
        token = google.authorize_access_token()
    except Exception as e:
        flash('Failed to authorize with Google.', 'error')
        return redirect(url_for('login'))
    
    # Get user info from Google
    user_data = token.get('userinfo')
    if not user_data:
        flash('Could not retrieve user information from Google.', 'error')
        return redirect(url_for('login'))
    
    email = user_data.get('email')
    google_id = user_data.get('sub')  # Google's unique user ID
    
    if not email or not google_id:
        flash('Google account missing required information.', 'error')
        return redirect(url_for('login'))
    
    # Check if user already exists by Google ID
    user = User.query.filter_by(google_id=google_id).first()
    
    if not user:
        # Check if email is already registered with username/password
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Create a new user account
            user = User(
                email=email,
                google_id=google_id,
                username=None,  # No username for Google OAuth users
                password=None   # No password for Google OAuth users
            )
            db.session.add(user)
            db.session.commit()
    
    # Log the user in
    session['user_id'] = user.id
    return redirect(url_for('dashboard'))


@app.route("/logout")
def logout():
    # completely clear session for security
    session.clear()
    return redirect(url_for('index'))


@app.route("/dashboard")
@login_required
def dashboard():
    user = get_current_user()
    lists = WordList.query.filter_by(user_id=user.id).order_by(WordList.id.desc()).all()
    return render_template("dashboard.html", lists=lists)


@app.route("/create_list", methods=["GET", "POST"])
@login_required
def create_list():
    if request.method == "POST":
        name = request.form.get('name', '').strip()
        if not name:
            pass
        else:
            new_list = WordList(name=name, user_id=session['user_id'])
            db.session.add(new_list)
            db.session.commit()
            return redirect(url_for('dashboard'))

    return render_template("create_list.html")


@app.route("/list/<int:list_id>", methods=["GET", "POST"])
@login_required
def study(list_id):
    user = get_current_user()
    word_list = WordList.query.filter_by(id=list_id, user_id=user.id).first_or_404()

    if request.method == "POST":
        word        = request.form.get('word', '').strip()
        description = request.form.get('description', '').strip()
        example     = request.form.get('example', '').strip()
        disadvantage= request.form.get('disadvantage', '').strip()

        if not word:
            pass
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
            return redirect(url_for('study', list_id=list_id))

    words = Word.query.filter_by(list_id=list_id).all()
    return render_template("study.html", word_list=word_list, words=words)


@app.route("/list/<int:list_id>/delete_word/<int:word_id>", methods=["POST"])
@login_required
def delete_word(list_id, word_id):
    user = get_current_user()
    # Make sure the list belongs to this user
    WordList.query.filter_by(id=list_id, user_id=user.id).first_or_404()
    word = Word.query.filter_by(id=word_id, list_id=list_id).first_or_404()
    db.session.delete(word)
    db.session.commit()
    return redirect(url_for('study', list_id=list_id))


@app.route("/set_language", methods=["POST"])
@csrf.exempt
def set_language():
    """Set the user's preferred language."""
    language = request.form.get('language')
    if language in LANGUAGES:
        session['language'] = language
    return redirect(request.referrer or url_for('index'))


if __name__ == "__main__":
    app.run(debug=True)