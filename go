pushd "$(dirname "$0")"

trap 'kill $(jobs -p)' EXIT

redis-server >/dev/null 2>&1 &
node realtime/app.js &
python runserver.py

popd
