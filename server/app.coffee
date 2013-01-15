restify = require 'restify'
sqlite3 = require 'sqlite3'
# https://github.com/developmentseed/node-sqlite3/wiki/API

server = restify.createServer()

# Parse the query string to req.query
server.use (restify.queryParser { mapParams: false })

# ORM alternative
KEYS = [
  ["applicant", /^.*$/],
  ["projectDescription", /^.*$/],
  ["projectManagerPhone", /^.*$/],
  ["projectManagerEmail", /^.*$/],
  ["projectManagerName", /^.*$/],
  ["acreage", /^[0-9.]*$/],
  ["CUP", /^.*$/],
  ["WQC", /^.*$/],
  ["parish", /^(list|of|parishes)$/],
  ["expirationDate", /^.*$/],
  ["longitude", /^[0-9.]*$/],
  ["latitude", /^[0-9.]*$/]
]

server.put '/applications/:permitApplicationNumber', (req, res, next) ->
  db = new sqlite3.Database '/tmp/wetlands.db'

  # Maybe this should be a reduce that passes the db along.
  for key in KEYS
    # Validation
    # The second thing is always a regular expression.
    if req.query[key[0]] && req.query[key[0]].match key[1]
      console.log req.query[key[0]]
      sql = "UPDATE application SET #{key[0]} = ? WHERE permitApplicationNumber = ?;"
      db.run sql, req.query[key[0]], req.params.permitApplicationNumber

  res.send 200
  return next()

server.get '/applications/:permitApplicationNumber', (req, res, next) ->
  db = new sqlite3.Database '/tmp/wetlands.db'
  sql = "SELECT * FROM application WHERE permitApplicationNumber = ? LIMIT 1;"
  db.get sql, req.params.permitApplicationNumber, (err, row) ->
    if row
      console.log row
    else
      console.log 'no permit with this number'
    res.send 200
    return next()

server.get '/applications', (req, res, next) ->
  db = new sqlite3.Database '/tmp/wetlands.db'
  sql = "SELECT * FROM application;"
  db.all sql, (err, rows) ->
    console.log rows
    res.send 200
    return next()

server.listen 8080
