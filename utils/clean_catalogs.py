from pyechonest import config, catalog

config.ECHO_NEST_API_KEY = 'ZMBQQBZ4DBZVTKOTB'

while True:
  catalogs = catalog.list_catalogs()
  if len(catalogs) == 0:
    break

  for cat in catalogs:
    print "Deleting catalog " + cat.name
    cat.delete()
