from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
from textblob import TextBlob
import sqlite3
from datetime import datetime
import os
import random
from werkzeug.security import generate_password_hash, check_password_hash
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = 'your_secret_key'


def init_db():
    if not os.path.exists('instance'):
        os.makedirs('instance')
    conn = sqlite3.connect('instance/journal.db')
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            content TEXT,
            mood TEXT,
            gratitude TEXT,
            sentiment TEXT,
            polarity REAL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()


init_db()


def get_user_id():
    return session.get('user_id')


@app.route('/')
def start():
    return render_template("start.html")

@app.route('/index')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('instance/journal.db')
    c = conn.cursor()
    c.execute("SELECT * FROM entries WHERE user_id = ? ORDER BY id DESC", (get_user_id(),))
    entries = c.fetchall()
    conn.close()

    quotes = [
        "Breathe. You’re doing better than you think.",
        "Feelings are just visitors. Let them come and go.",
        "Your mental health is a priority. Not a luxury.",
        "It’s okay to not be okay — just don’t unpack and live there.",
        "Little progress is still progress. Keep going."
    ]
    quote = random.choice(quotes)

    return render_template('index.html', entries=entries, quote=quote)



@app.route('/add', methods=['POST'])
def add_entry():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    content = request.form['entry']
    mood = request.form['mood']
    gratitude = request.form['gratitude']
    blob = TextBlob(content)
    polarity = blob.sentiment.polarity
    sentiment = 'Positive' if polarity > 0 else 'Negative' if polarity < 0 else 'Neutral'

    conn = sqlite3.connect('instance/journal.db')
    c = conn.cursor()
    c.execute("INSERT INTO entries (user_id, date, content, mood, gratitude, sentiment, polarity) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (get_user_id(), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), content, mood, gratitude, sentiment, polarity))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/delete/<int:entry_id>', methods=['POST'])
def delete_entry(entry_id):
    conn = sqlite3.connect('instance/journal.db')
    c = conn.cursor()
    c.execute("DELETE FROM entries WHERE id = ? AND user_id = ?", (entry_id, get_user_id()))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/edit/<int:entry_id>', methods=['GET', 'POST'])
def editentry(entry_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('instance/journal.db')
    c = conn.cursor()

    if request.method == 'POST':
        updated_content = request.form['entry']
        updated_mood = request.form['mood']
        updated_gratitude = request.form['gratitude']
        blob = TextBlob(updated_content)
        polarity = blob.sentiment.polarity
        sentiment = 'Positive' if polarity > 0 else 'Negative' if polarity < 0 else 'Neutral'

        c.execute('''
            UPDATE entries 
            SET content = ?, mood = ?, gratitude = ?, sentiment = ?, polarity = ?
            WHERE id = ? AND user_id = ?
        ''', (updated_content, updated_mood, updated_gratitude, sentiment, polarity, entry_id, get_user_id()))

        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    c.execute("SELECT * FROM entries WHERE id = ? AND user_id = ?", (entry_id, get_user_id()))
    entry = c.fetchone()
    conn.close()

    if entry:
        return render_template('editentry.html', entry=entry)
    else:
        flash("Entry not found.")
        return redirect(url_for('index'))


@app.route('/export')
def export_pdf():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('instance/journal.db')
    c = conn.cursor()
    c.execute("SELECT date, content, mood, gratitude FROM entries WHERE user_id = ? ORDER BY id DESC", (get_user_id(),))
    entries = c.fetchall()
    conn.close()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Mental Wellness Journal", ln=True, align='C')

    for entry in entries:
        pdf.multi_cell(0, 10, txt=f"Date: {entry[0]}\nMood: {entry[2]}\nGratitude: {entry[3]}\nEntry: {entry[1]}\n\n")

    export_path = "instance/exported_journal.pdf"
    pdf.output(export_path)
    return send_file(export_path, as_attachment=True)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        conn = sqlite3.connect('instance/journal.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
        except sqlite3.IntegrityError:
            flash("Username already exists.")
            return redirect(url_for('signup'))
        conn.close()
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('instance/journal.db')
        c = conn.cursor()
        c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            return redirect(url_for('index'))
        else:
            flash("Invalid credentials.")
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
