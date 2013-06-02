from musicroom import facebook, app, base_url
from flask import request, session, url_for, redirect

@facebook.tokengetter
def get_facebook_token(token=None):
  return session.get('facebook_token')

@app.route('/login')
def login():
  return facebook.authorize(url_for('facebook_authorized', _external=True,
    next=request.args.get('next') or request.referrer or url_for('index')))

@app.route('/facebook-authorized')
@facebook.authorized_handler
def facebook_authorized(resp):
  if resp is None:
    flash(u'You denied the request to sign in.')
    return redirect(request.args.get('next'))

  session['facebook_token'] = (resp['access_token'], '')

  return redirect(request.args.get('next'))
