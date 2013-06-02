import musicroom
from musicroom import app

musicroom.domain = 'localhost'
app.debug = True
app.run(host='0.0.0.0', port=80)
