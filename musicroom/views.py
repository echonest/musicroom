from flask import request, redirect, url_for, session, flash, abort, render_template
from flask_oauth import OAuthException
from pyechonest import catalog, playlist
import time
import json

from musicroom import app, facebook, rdio_token, redis
from musicroom.models import APIError, UnauthorizedError, NonexistentError, Room, User

BASE_URL = 'http://localhost:5000'

@app.route('/')
def index():
  return "Music Room"

@app.route('/me/')
def profile():
  try:
    user = User()
  except APIError:
    abort(500) # Internal Server Error
  except UnauthorizedError:
    return redirect(url_for('login', next=request.url))

  owned_rooms = user.get_owned_rooms()
  joined_rooms = user.get_joined_rooms()
  return render_template(
    'profile.html',
    owned_rooms=owned_rooms,
    joined_rooms=joined_rooms
  )

@app.route('/room/create')
def create():
  name = request.args.get('name')
  findable = request.args.get('findable')
  if name is None:
    abort(400) # Bad Request

  if findable is None:
    findable = True
  else:
    if findable in ["true", "True"]:
      findable = True
    elif findable in ["false", "False", ""]:
      findable = False
    else:
      abort(400) # Bad Request

  try:
    user = User()
  except APIError:
    abort(500) # Internal Server Error
  except UnauthorizedError:
    return redirect(url_for('login', next=request.url))

  room = Room(name=name, findable=findable, owner=user)

  return redirect(url_for('profile'))

@app.route('/room/<room_id>/')
def room(room_id):
  try:
    me = User()
  except APIError:
    abort(500)
  except UnauthorizedError:
    return redirect(url_for('login', next=request.url))

  try:
    room = Room(room_id)
  except NonexistentError:
    abort(404)

  if (me == room.owner()):
    # Show speaker / admin page
    return render_template('speaker.html', room=room, members=room.members(), in_room=me.in_room(room))
  else:
    # Show listener page
    return "YOU ARE NOT THE MAN"
    # return render_template('speaker.html', room=room, listeners=len(room['listeners']), listener_link=url_for('listener', mrid=mrid), start_link=url_for('start', mrid=mrid))

@app.route('/room/<room_id>/join')
def join(room_id):
  try:
    room = Room(room_id)
  except NonexistentError:
    abort(404)

  try:
    me = User()
  except APIError:
    abort(500)
  except UnauthorizedError:
    return redirect(url_for('login', next=request.url))

  if not me.in_room(room):
    me.join_room(room)
    redis.publish('push', json.dumps({'room': room_id, 'name': 'joined', 'data': {'name': me.name()}}))

  return "joined room"

@app.route('/room/<room_id>/start')
def start(room_id):
  try:
    room = Room(room_id)
  except NonexistentError:
    abort(404)

  if (room.num_members() == 0):
    # Do something better like returning some json
    abort(400)

  try:
    me = User()
  except APIError:
    abort(500)
  except UnauthorizedError:
    return redirect(url_for('login', next=request.url))

  liked_artists = room.artist_counts()
  updater = []
  for artist in liked_artists:
    count = liked_artists[artist]
    item = {'item': {'item_id': artist, 'artist_id': 'facebook:artist:' + artist, 'play_count': count}}
    updater.append(item)

  cat = room.seed_catalog()
  ticket = cat.update(updater)
  while True:
    status = cat.status(ticket)
    if status['ticket_status'] == 'complete':
      break
    time.sleep(0.1)

  pl = room.playlist(generate=True)
  return str(pl.session_id)
  # next_song = pl.get_next_songs(lookahead='1')[0]
  # next_track = next_song.get_tracks('rdio-US')[0]
  # return next_track['foreign_id']

@app.route('/room/<room_id>/next')
def next(room_id):
  try:
    room = Room(room_id)
  except NonexistentError:
    abort(404)

  try:
    me = User()
  except APIError:
    abort(500)
  except UnauthorizedError:
    return redirect(url_for('login', next=request.url))

  pl = room.playlist()
  count = request.args.get('count')
  if count is None:
    count = '1'
  pl.get_next_songs(results='0',lookahead=count)
  next_songs = pl.get_lookahead_songs()
  print next_songs
  tracks = map(lambda song: song.get_tracks('rdio-US')[0]['foreign_id'], next_songs)
  return json.dumps(map(lambda track: track.split(':')[-1], tracks))

@app.route('/playback_token')
def playback_token():
  return rdio_token['result']
