from musicroom import app, facebook
from pyechonest import catalog, playlist
from pyechonest.util import EchoNestAPIError
import sqlite3
import random
import string
from flask import g
from flask_oauth import OAuthException

DATABASE = 'musicroom.db'

def connect_db():
  return sqlite3.connect(DATABASE)

@app.before_request
def before_request():
  g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
  if hasattr(g, 'db'):
    g.db.close()

class UnauthorizedError(Exception):
  pass

class APIError(Exception):
  pass

class NonexistentError(Exception):
  pass

class User:
  def __init__(self, fbid=None, name=None):
    if fbid is None:
      try:
        me = facebook.get('me')
        if me.status != 200:
          raise APIError()
      except OAuthException:
        raise UnauthorizedError()
      fbid = me.data['id']
      name = me.data['name']

    self._fbid = fbid

    cur = g.db.execute('select loaded from user where fbid = ?', (self._fbid,))
    row = cur.fetchone()
    if row is None:
      g.db.execute('insert into user values (?, ?, 0);', (self._fbid, name))
      g.db.commit()
      loaded = False
    else:
      loaded = row[0]

    if not loaded:
      self.load_artists()


  def __eq__(self, other):
    return self._fbid == other._fbid

  def __ne__(self, other):
    return not self.__eq__(other)

  # fbid : () -> string
  def fbid(self):
    return self._fbid

  # name : () -> string
  def name(self):
    cur = g.db.execute('select name from user where fbid = ?;', (self._fbid,))
    return cur.fetchone()[0]

  # loaded : () -> boolean
  def loaded(self):
    cur = g.db.execute('select loaded from user where fbid = ?;', (self._fbid,))
    return cur.fetchone()[0]

  # load_artists : string list -> ()
  def load_artists(self, artist_fbids=None):
    g.db.execute('delete from likes_artist where user_fbid = ?;', (self._fbid,))
    if artist_fbids is None:
      try:
        resp = facebook.get('me/music')
        if resp.status != 200:
          raise APIError()
      except OAuthException:
        raise UnauthorizedError()
      music = resp.data['data']
      artists = filter(lambda item: item['category'] == 'Musician/band', music)
      values = map(lambda item: (self._fbid, item['id']), artists)
    else: 
      values = map(lambda artist_fbid: (self._fbid, artist_fbid), artist_fbids)
    g.db.executemany('insert or ignore into likes_artist values (?, ?);', values)
    g.db.execute('update user set loaded = 1 where fbid = ?;', (self._fbid,))
    g.db.commit()

  # join_room : Room -> ()
  def join_room(self, room):
    g.db.execute('insert into memberof values (?, ?);', (self._fbid, room.id()))
    g.db.commit()

  # in_room : Room -> boolean
  def in_room(self, room):
    cur = g.db.execute('select * from memberof where user_fbid = ? and room_id = ?', (self._fbid, room.id()))
    return (cur.fetchone() is not None)

  # leave_room : Room -> ()
  def leave_room(self, room):
    g.db.execute('delete from memberof where user_fbid = ? and room_id = ?;', (self._fbid, room.id()))
    g.db.commit()

  # owned_rooms : () -> Room list
  def owned_rooms(self):
    cur = g.db.execute('select id from room where owner_fbid = ?', (self._fbid,))
    return map(lambda row: Room(row[0]), cur)

  # joined_rooms : () -> Room list
  def joined_rooms(self):
    cur = g.db.execute('select room_id from memberof where user_fbid = ?', (self._fbid,))
    return map(lambda row: Room(row[0]), cur)

  def like(self, room):
    g.db.execute('insert or replace into rates_song values (?, ?, 1)', (self._fbid, room.id()))
    g.db.commit()

  def dislike(self, room):
    g.db.execute('insert or replace into rates_song values (?, ?, -1)', (self._fbid, room.id()))
    g.db.commit()

class Room:
  def __init__(self, id=None, name=None, owner=None, findable=True):
    if id is None and (name is None or owner is None or findable is None):
      raise Exception('new room requires a name and owner')
    elif id is None:
      # Generate random ids until one of them is unused.
      # This is really really hacky and bad.
      while True:
        try:
          id = ''.join([random.choice(string.letters[:26]) for i in xrange(8)])
          g.db.execute('insert into room values (?, ?, ?, null, null, 0, ?, null, null, null, null);', (id, name, findable, owner._fbid))
          g.db.commit()
        except:
          continue
        else:
          break
    else:
      cur = g.db.execute('select * from room where id = ?', (id,))
      if cur.fetchone() is None:
        raise NonexistentError()

    self._id = id

  def delete(self):
    self.seed_catalog().delete()
    g.db.execute('delete from memberof where room_id = ?', (self._id,))
    g.db.execute('delete from rates_song where room_id = ?', (self._id,))
    g.db.execute('delete from room where id = ?', (self._id,))
    g.db.commit()

  @classmethod
  def public_rooms(cls):
    cur = g.db.execute('select id from room where findable = 1')
    return map(lambda row: cls(row[0]), cur)

  # id : () -> string
  def id(self):
    return self._id

  # name : () -> string
  def name(self):
    cur = g.db.execute('select name from room where id = ?', (self._id,))
    return cur.fetchone()[0]

  # name : () -> boolean
  def findable(self):
    cur = g.db.execute('select findable from room where id = ?', (self._id,))
    return cur.fetchone()[0]

  # seed_catalog : () -> Catalog
  # if generate, creates a new catalog if it doesn't already exist
  def seed_catalog(self):
    cur = g.db.execute('select seed_catalog from room where id = ?', (self._id,))
    result = cur.fetchone()[0]
    if result is not None:
      try:
        return catalog.Catalog(result)
      except EchoNestAPIError:
        pass

    cat = catalog.Catalog(str(self.id()), 'general')
    g.db.execute('update room set seed_catalog = ? where id = ?', (cat.id, self._id))
    g.db.commit()
    return cat

  # playlist : () -> Playlist
  # if generate, creates a new playlist seeded by the seed_catalog (if it
  # exists)
  def playlist(self, generate=False):
    cur = g.db.execute('select playlist from room where id = ?', (self._id,))
    result = cur.fetchone()[0]
    if result is not None:
      try:
        print "using existing playlist"
        pl = playlist.Playlist(session_id=result)
      except EchoNestAPIError:
        pass # The playlist has probably expired. Just create a new one.
      else:
        if generate:
          cat = self.seed_catalog()
          pl.restart(
            buckets=['id:rdio-US', 'tracks'],
            seed_catalog=cat.id,
            type='catalog-radio'
          )
        return pl

    cat = self.seed_catalog()
    pl = playlist.Playlist(
      buckets=['id:rdio-US', 'tracks'],
      seed_catalog=cat.id,
      type='catalog-radio'
    )
    g.db.execute('update room set playlist = ? where id = ?', (pl.session_id, self._id))
    g.db.commit()
    return pl

  # status : () -> int
  def status(self):
    cur = g.db.execute('select status from room where id = ?', (self._id,))
    return cur.fetchone()[0]

  # name : () -> User
  def owner(self):
    cur = g.db.execute('select owner_fbid from room where id = ?', (self._id,))
    return User(cur.fetchone()[0])

  # members : () -> User  list
  def members(self):
    cur = g.db.execute('select user_fbid from memberof where room_id = ?', (self._id,))
    result = []
    for row in cur:
      result.append(User(row[0]))
    return result

  # num_members : () -> int
  def num_members(self):
    cur = g.db.execute('select count(user_fbid) from memberof where room_id = ?', (self._id,))
    return cur.fetchone()[0]

  # artist_counts : () -> (string, int) dict
  def artist_counts(self):
    cur = g.db.execute( 'select L.artist_fbid, count(L.user_fbid) from memberof M, likes_artist L '
                  'where M.room_id = ? and M.user_fbid = L.user_fbid group by L.artist_fbid', (self._id,) )
    mapping = {}
    for row in cur:
      mapping[row[0]] = row[1]
    return mapping

  def cur_song(self):
    cur = g.db.execute('select cur_song_id, cur_rdio_id, cur_artist, cur_title from room where id = ?', (self._id,))
    row = cur.fetchone()
    return {'song_id': row[0], 'rdio_id': row[1], 'artist': row[2], 'title': row[3]}

  def set_song(self, song):
    g.db.execute(
      'update room set cur_song_id = ?, cur_rdio_id = ?, cur_artist = ?, cur_title = ? where id = ?',
      (song['song_id'], song['rdio_id'], song['artist'], song['title'], self._id)
    )
    g.db.execute('delete from rates_song where room_id = ?', (self._id,))
    g.db.commit()

  def get_cur_rating(self):
    cur = g.db.execute('select sum(rating) from rates_song where room_id = ? group by room_id', (self._id,))
    row = cur.fetchone()
    if row is None:
      sum_ = 0
    else:
      sum_ = row[0]
    return int(round(((float(sum_) / self.num_members()) + 1) * 5))
