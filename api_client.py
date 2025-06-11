import xbmcaddon
from jellyseerr_api import JellyseerrClient
from overseerr_api import OverseerrClient  # (Overseerr support is untested)

addon = xbmcaddon.Addon()
service = addon.getSetting("api_service")
url = addon.getSetting("jellyseerr_url").rstrip("/") + "/api/v1"
username = addon.getSetting("jellyseerr_username")
password = addon.getSetting("jellyseerr_password")

if service == "1":
    client = OverseerrClient(url, username, password)
else:
    client = JellyseerrClient(url, username, password)
