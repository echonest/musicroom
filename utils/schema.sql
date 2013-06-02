drop table if exists likes_artist;
drop table if exists rates_song;
drop table if exists memberof;
drop table if exists room;
drop table if exists user;

create table user (
  fbid varchar(40),
  name varchar(50) not null,
  loaded boolean not null,
  primary key (fbid)
);

create table room (
  id varchar(20),
  name varchar(50) not null,
  findable boolean not null,
  seed_catalog varchar(20),
  playlist varchar(20),
  status integer not null,
  owner_fbid varchar(20) not null,
  cur_song_id varchar(20),
  cur_rdio_id varchar(20),
  cur_artist varchar(50),
  cur_title varchar(50),
  primary key (id),
  foreign key (owner_fbid) references user(fbid),
  check (status in (0, 1, 2))
);
-- status:
-- 0 = Initialized
-- 1 = Started
-- 2 = Paused

create table memberof (
  user_fbid varchar(20),
  room_id varchar(20),
  primary key (user_fbid, room_id),
  foreign key (user_fbid) references user(fbid),
  foreign key (room_id) references room(id)
);

create table rates_song (
  user_fbid varchar(20),
  room_id integer,
  rating integer,
  primary key (user_fbid, room_id),
  foreign key (user_fbid) references user(fbid),
  foreign key (room_id) references room(id),
  check (rating in (-1, 1))
);

create table likes_artist (
  user_fbid varchar(20),
  artist_fbid varchar(20),
  primary key (user_fbid, artist_fbid),
  foreign key (user_fbid) references user(fbid)
);
