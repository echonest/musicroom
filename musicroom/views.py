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
  return redirect(url_for('profile'))

@app.route('/me/')
def profile():
  try:
    user = User()
  except APIError:
    abort(500) # Internal Server Error
  except UnauthorizedError:
    return redirect(url_for('login', next=request.url))

  return render_template(
    'profile.html',
    user=user
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

@app.route('/room/<room_id>/delete')
def delete(room_id):
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

  if me == room.owner():
    room.delete()

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

  return render_template('room.html', room=room, in_room=me.in_room(room), is_owner=(me == room.owner()))

@app.route('/room/<room_id>/listen')
def listen(room_id):
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

  return render_template('listen.html', room=room)

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

  return redirect(url_for('room', room_id=room_id))

@app.route('/room/<room_id>/leave')
def leave(room_id):
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

  if me.in_room(room):
    me.leave_room(room)

  return redirect(url_for('room', room_id=room_id))

@app.route('/room/<room_id>/playback')
def playback(room_id):
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

  if (me != room.owner()):
    abort(401)
  else:
    return render_template('playback.html', room=room)

@app.route('/room/<room_id>/action/start')
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
  pl.get_next_songs(results='0', lookahead='1')
  song = pl.get_lookahead_songs()[0]
  track = song.get_tracks('rdio-US')[0]
  rdio_id = track['foreign_id'].split(':')[-1]
  return json.dumps({'song_id': song.id, 'rdio_id': rdio_id, 'artist': song.artist_name, 'title': song.title})

@app.route('/room/<room_id>/action/play')
def play(room_id):
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
  print room.cur_song()
  if room.cur_song()['song_id'] is not None and room.num_members() > 0:
    pl.feedback(rate_song='last^'+str(room.get_cur_rating()))
  pl.get_next_songs(results='1', lookahead='1')

  cur_song = pl.get_current_songs()[0]
  cur_track = cur_song.get_tracks('rdio-US')[0]
  cur_rdio_id = cur_track['foreign_id'].split(':')[-1]
  current = {
    'song_id': cur_song.id,
    'rdio_id': cur_rdio_id,
    'artist': cur_song.artist_name,
    'title': cur_song.title
  }
  room.set_song(current)
  redis.publish('push', json.dumps({'room': room_id, 'name': 'playing', 'data': current}))
  print current

  next_song = pl.get_lookahead_songs()[0]
  next_track = next_song.get_tracks('rdio-US')[0]
  next_rdio_id = next_track['foreign_id'].split(':')[-1]
  return json.dumps({
    'song_id': next_song.id,
    'rdio_id': next_rdio_id,
    'artist': next_song.artist_name,
    'title': next_song.title
  })

@app.route('/room/<room_id>/action/like')
def like(room_id):
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

  me.like(room);
  return "ok"

@app.route('/room/<room_id>/action/dislike')
def dislike(room_id):
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

  me.dislike(room);
  return "ok"

@app.route('/playback_token')
def playback_token():
  return rdio_token['result']
