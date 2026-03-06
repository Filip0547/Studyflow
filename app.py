import os

from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import CSRFProtect

app = Flask(__name__)
# use a randomly-generated secret key each time (for dev); replace with env var in prod
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# initialize extensions
db = SQLAlchemy(app)
csrf = CSRFProtect(app)


# ─── MODELS ───────────────────────────────────────────────

class User(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
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
        password = request.form.get('password', '')

        if not username or not password:
            pass
        elif len(password) < 4:
            pass
        elif User.query.filter_by(username=username).first():
            pass
        else:
            hashed = generate_password_hash(password)
            db.session.add(User(username=username, password=hashed))
            db.session.commit()
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


if __name__ == "__main__":
    app.run(debug=True)