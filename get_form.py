# all the imports
from __future__ import with_statement
from contextlib import closing
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash
import form_builder
import valid

# flask initialization
app = Flask(__name__)
app.config.from_object(__name__)

# database initialization
def connect_db():
    return sqlite3.connect('Form_db.db')

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('Form_db.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    g.db.close()

# main module

@app.route('/<form_link>', methods=['GET', 'POST'])
def show_form(form_link):

    # variable
    g_form = valid.create_class(g.db, form_link)()
    g_form.form_link = form_link
    form_name = g_form.get_form_name()
    questions = g_form.get_questions()
    
    if request.method == 'POST':

        if not g_form.is_valid(request.form):
            print g_form.errors
            return redirect(url_for('show_form', form_link = form_link))
        else:
            return render_template('send_page.html', error = None)

    return render_template('form.html', form_link = form_link, form_name = form_name, 
                           questions = questions, answer = g_form.answer_data, errors = g_form.errors)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
