from flask import Flask
from flask_oauth import OAuth, OAuthException
from pyechonest import config
from redis import StrictRedis
from rdio import Rdio

base_url = 'http://localhost:5000'

app = Flask(__name__)

app.config['MONGO_DBNAME'] = 'db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////db.sqlite'
app.secret_key = 'super secret'
app.debug = True

config.ECHO_NEST_API_KEY = 'ZMBQQBZ4DBZVTKOTB'

oauth = OAuth()
facebook = oauth.remote_app('facebook',
  base_url='https://graph.facebook.com/',
  request_token_url=None,
  access_token_url='/oauth/access_token',
  authorize_url='https://www.facebook.com/dialog/oauth',
  consumer_key='255490651260325',
  consumer_secret='8fd6a30d356b85bfa58daa327c9eacea',
  request_token_params={'scope': 'email'}
)

redis = StrictRedis()

_rdio = Rdio(('yjgnkcp2kr8ykwwjtujb5ajv', 'trpsv6n6gm'))
rdio_token = _rdio.call('getPlaybackToken', {'domain': 'localhost'})

import musicroom.login
import musicroom.models
import musicroom.views
