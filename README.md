musicroom
=========

Install Node.js, NPM, Redis, SQLite3, and Python. Then run `pip install -r
requirements.txt` (from a virtualenv, preferably), and run `./utils/reset`.
Finally run `./go` to start the servers.

*Important:* For rdio playback to work, replace the domain in the definition of
`rdio_token` in `musicroom/__init__.py`.
