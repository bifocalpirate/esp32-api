
# Useful test commands


## Upload a file
``
curl -X POST "192.168.1.116:8000/upload" -H "x-api-key: <api key>"  -F "file=@labyrinth.jpg"
``

## List upload images

``
curl "192.168.1.116:8000/list" -H "x-api-key: <api key>"
``

## Send notification (used by the device when booting up)

``
curl -H "x-api-key: <api key>>" -H "Content-Type: application/json" -d '{"message":"test message", "topic":"<channel>"}' 192.168.1.116:8000/notification
``

On initial bootup the device will flash the LED and send an encrypted string representing the bootup snapshot.

# Retrieve file

``
curl "192.168.1.116:8000/get-file/<thefile>" -H "x-api-key: <api key>" --output <destination filename>
``

# Retrieve file by encrypted string

``
curl "192.168.1.116:8000/get-file-by-encrypted-name/<thefile>" -H "x-api-key: <api key>" --output <destination filename>`
``

Does not require an API key as the file will be retrieved by the client when viewed by the [ntfy.sh](https://ntfy.sh) notification. If the API can decrypt the string using the configured password and the file exists, it will be returned. 