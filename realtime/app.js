var io = require('socket.io').listen(8001);
var redis = require('redis');

var sub = redis.createClient();

sub.on('message', function (channel, message) {
  message_obj = JSON.parse(message);
  if (message_obj.room && message_obj.name) {
    io.sockets.in(message_obj.room).emit(
      message_obj.name,
      message_obj.data
    );
  }
});

io.sockets.on('connection', function (socket) {
  socket.on('subscribe', function (data) {
    if (data.room) {
      socket.join(data.room);
    }
  });

  socket.on('unsubscribe', function (data) {
    if (data.room) {
      socket.leave(data.room);
    }
  });
});

sub.subscribe("push");
