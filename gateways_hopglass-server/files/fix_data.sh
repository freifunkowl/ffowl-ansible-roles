#!/bin/bash

# HTTP-Header ausgeben
echo "Content-Type: application/json"
echo

# Query-String verfügbar als:
# $QUERY_STRING  -> filter=bar&value=barfoo

REQ_URI="$(echo $REQUEST_URI | sed -e 's%^/json%%g')"

logger "$0: http://127.0.0.1:4444$REQ_URI"

wget -O - -q "http://127.0.0.1:4444$REQ_URI" | jq '(.nodes[] | select(.nodeinfo.owner.contact?) | .nodeinfo.owner.contact) |= "none-of-your-business.ffmuc@mail.local"'
