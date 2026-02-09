from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'sqlite:///' + os.path.join(basedir, 'waoshaji.db')
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# CHANGE THIS PASSWORD!
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')  # ← Your secret password
if not ADMIN_PASSWORD:
    ADMIN_PASSWORD = "fallback-secret-for-local-testing"  # only for dev
    print("Warning: Using fallback password – set ADMIN_PASSWORD env var in production!")

class Contact(db.Model):
    phone = db.Column(db.String(30), primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<Contact {self.name} - {self.phone}>"

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
        # On GET (page load) → show ALL contacts
        results = Contact.query.order_by(Contact.name).all()

    # Get total count for display
    total_count = Contact.query.count()

    return render_template(
        'index.html',
        results=results,
        query=query,
        search_type=search_type,
        total_count=total_count,
        show_full_list=(request.method == 'GET')  # Used to change heading
    )

# Admin-only routes (hidden – access by typing URL directly)
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
                    db.session.add(new_contact)
                    db.session.commit()
                    return redirect(url_for('index'))
    return render_template('add.html', error=error)

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
                db.session.delete(contact)
                db.session.commit()
                return redirect(url_for('index'))
            else:
                error = f"No contact with phone {phone}"
    return render_template('remove.html', error=error)

if __name__ == '__main__':
    app.run(debug=False)
