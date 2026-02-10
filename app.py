from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# Database configuration – uses DATABASE_URL from env (Postgres on Render) or local SQLite
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'sqlite:///' + os.path.join(basedir, 'waoshaji.db')
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False  # Set to True for query debugging

db = SQLAlchemy(app)

# Admin password – use env var on Render, fallback for local
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
if not ADMIN_PASSWORD:
    ADMIN_PASSWORD = "fallback-secret-for-local-testing"
    print("Warning: Using fallback password – set ADMIN_PASSWORD env var in production!")

class Contact(db.Model):
    phone = db.Column(db.String(30), primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<Contact {self.name} - {self.phone}>"

# Create tables if they don't exist (safe for both SQLite and Postgres)
with app.app_context():
    db.create_all()

# Home = search + full list (public)
@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    query = ""
    search_type = "name"

    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        search_type = request.form.get('search_type', 'name')
        if query:
            if search_type == 'phone':
                contact = Contact.query.get(query)
                if contact:
                    results = [contact]
            else:
                results = Contact.query.filter(
                    Contact.name.ilike(f'%{query}%')
                ).order_by(Contact.name).all()
    else:
        results = Contact.query.order_by(Contact.name).all()

    total_count = Contact.query.count()

    return render_template(
        'index.html',
        results=results,
        query=query,
        search_type=search_type,
        total_count=total_count,
        show_full_list=(request.method == 'GET')
    )

# Admin-only: Add contact
@app.route('/add', methods=['GET', 'POST'])
def add():
    error = None
    if request.method == 'POST':
        if request.form.get('admin_pass') != ADMIN_PASSWORD:
            error = "Wrong admin password!"
        else:
            phone = request.form.get('phone').strip()
            name = request.form.get('name').strip()
            if not phone or not name:
                error = "Phone and name are required!"
            else:
                existing = Contact.query.get(phone)
                if existing:
                    error = f"Phone {phone} already exists!"
                else:
                    new_contact = Contact(phone=phone, name=name)
                    try:
                        db.session.add(new_contact)
                        db.session.commit()
                        print(f"Added contact: {name} - {phone}")
                        return redirect(url_for('index'))
                    except Exception as e:
                        db.session.rollback()
                        error = f"Add failed: {str(e)}"
    return render_template('add.html', error=error)

# Admin-only: Remove contact
@app.route('/remove', methods=['GET', 'POST'])
def remove():
    error = None
    if request.method == 'POST':
        if request.form.get('admin_pass') != ADMIN_PASSWORD:
            error = "Wrong admin password!"
        else:
            phone = request.form.get('phone').strip()
            contact = Contact.query.get(phone)
            if contact:
                try:
                    db.session.delete(contact)
                    db.session.commit()
                    print(f"Deleted contact: {contact.name} - {phone}")
                    return redirect(url_for('index'))
                except Exception as e:
                    db.session.rollback()
                    error = f"Delete failed: {str(e)}"
            else:
                error = f"No contact with phone {phone}"
    return render_template('remove.html', error=error)

if __name__ == '__main__':
    app.run(debug=False)
