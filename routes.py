#!/usr/bin/env python
from flask import Flask, render_template, request, flash, redirect
from flask_flatpages import FlatPages
from flask.ext.mail import Message, Mail
from forms import ContactForm, ContributeForm
from datetime import datetime
from ghettodown import ghettodown
import shutil
import yaml
import sys
import re

mail = Mail()

app = Flask(__name__)
flatpages = FlatPages(app)

app.config.from_object('config')
app.config['FLATPAGES_HTML_RENDERER'] = ghettodown
app.secret_key = 'development key'
mail.init_app(app)


def notify(group, subject, body):
    try:
        recv = app.config[group]
        sender = app.config["MAIL_USERNAME"]
        msg = Message(subject, sender=sender, recipients=[recv])

        if body.startswith('/'):
            body = app.config['SELF'] + body

        msg.body = body
        mail.send(msg)
    except:
        pass


@app.route('/')
def posts():
    postdir = app.config['POST_DIR']
    posts = [p for p in flatpages if p.path.startswith(postdir)]
    posts.sort(key=lambda item: item['date'], reverse=False)
    return render_template('index.html', posts=posts)


@app.route('/projekt')
def projekt():
    return render_template('projekt.html')


@app.route('/<name>.html')
def post(name):
    postdir = app.config['POST_DIR']
    path = '{}/{}'.format(postdir, name)
    post = flatpages.get_or_404(path)
    return render_template('post.html', post=post)


@app.route('/contribute/', methods=['GET', 'POST'])
def contribute():
    form = ContributeForm()
    if request.method == 'POST':
        if not form.validate():
            return render_template('contribute.html', form=form)
        else:
            post = {}
            post['title'] = str(form.title.data)
            post['author'] = str(form.author.data) or 'Anonymous'
            post['date'] = datetime.now().strftime('%Y-%m-%d')
            body = str(form.article.data)
            output = yaml.dump(post, default_flow_style=False) + '\n' + body

            path = str(form.title.data.lower())
            path = re.sub('\W', '_', path)

            with open('content/drafts/%s.md' % path, 'w') as f:
                f.write(output)

            notify('MAIL_RECV_MODERATE', 'Please unlock post: %s' % post['title'], '/moderate/')

            return redirect('/contribute/done')
    else:
        return render_template('contribute.html', form=form)


@app.route('/contribute/done')
def contribute_done():
    return render_template('contribute.html', success=True)


@app.route('/moderate/')
def moderate():
    return render_template('moderate.html', posts=flatpages)


@app.route('/moderate/<post>', methods=['POST'])
def moderate_post(post):
    if 'unlock' in request.form:
        shutil.move('content/drafts/%s.md' % post, 'content/posts/%s.md' % post)
        notify('MAIL_RECV_MODERATE', 'freigeschaltet: %s' % post, '/%s.html' % post)
    else:
        return 'invalid action'
    return redirect('/moderate/')


@app.route('/kontakt/', methods=['GET', 'POST'])
def kontakt():
    form = ContactForm()
    if request.method == 'POST':
        if not form.validate():
            return render_template('kontakt.html', form=form)
        else:
            subject = form.subject.data
            body = """
            From: %s <%s>
            %s
            """ % (form.name.data, form.email.data, form.message.data)
            notify('MAIL_RECV_CONTACT', subject, body)
            return redirect('/kontakt/done')
    elif request.method == 'GET':
        return render_template('kontakt.html', form=form)


@app.route('/kontakt/done')
def kontakt_done():
    return render_template('kontakt.html', success=True)


if __name__ == "__main__":
    app.run(debug=True)
