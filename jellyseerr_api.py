import urllib.request
import urllib.error
import http.cookiejar
import ssl
import xbmcaddon
import xbmc
import json
from urllib.parse import urlencode, quote

class JellyseerrClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = None  # Will be initialized with SSL context
        self.logged_in = False
        self.allowed_user_type = xbmcaddon.Addon().getSetting("allowed_user_type") or "0"

    def init_opener(self):
        """Initializes the opener with SSL context based on addon settings."""
        addon = xbmcaddon.Addon()
        allow_self_signed = addon.getSettingBool("allow_self_signed")

        if allow_self_signed:
            ssl_context = ssl._create_unverified_context()
        else:
            ssl_context = ssl.create_default_context()

        https_handler = urllib.request.HTTPSHandler(context=ssl_context)
        cookie_handler = urllib.request.HTTPCookieProcessor(self.cookie_jar)
        self.opener = urllib.request.build_opener(https_handler, cookie_handler)

    def login(self):
        """Logs into the Jellyseerr instance - Endpoints based on allowed user type."""
        if self.logged_in:
            return

        self.init_opener()

        mode = str(self.allowed_user_type)
        # 0: local only, 1: remote only, 2: local then remote, 3: remote then local
        if mode == "0":
            self._login_local()
        elif mode == "1":
            self._login_remote()
        elif mode == "2":
            first = self._login_local()
            if first is False:
                self._login_remote()
        elif mode == "3":
            first = self._login_remote()
            if first is False:
                self._login_local()
        else:
            # Fallback to local only if setting is unexpected
            self._login_local()

    def _make_request(self, url, payload):
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data)
        req.add_header("Content-Type", "application/json")
        try:
            with self.opener.open(req) as resp:
                resp.read()
            return True
        except urllib.error.HTTPError as e:
            # 401/403 should allow fallback
            if e.code in (401, 403):
                xbmc.log(f"[kodiseerr] Auth HTTP error {e.code} for {url}", xbmc.LOGWARNING)
                return False
            xbmc.log(f"[kodiseerr] Auth failed HTTP {e.code} for {url}", xbmc.LOGERROR)
            # Non-fallback eligible error
            return None
        except urllib.error.URLError as e:
            xbmc.log(f"[kodiseerr] Auth network error for {url}: {e}", xbmc.LOGWARNING)
            return False

    def _login_local(self):
        login_url = f"{self.base_url}/auth/local"
        payload = {
            "email": self.username,
            "password": self.password,
        }
        result = self._make_request(login_url, payload)
        if result is True:
            self.logged_in = True
        return result

    def _login_remote(self):
        login_url = f"{self.base_url}/auth/jellyfin"
        payload = {
            "username": self.username,
            "password": self.password,
        }
        result = self._make_request(login_url, payload)
        if result is True:
            self.logged_in = True
        return result

    def api_request(self, endpoint, method="GET", data=None, params=None):
        """Sends an authenticated API request to the server."""
        if not self.logged_in:
            self.login()

        if not self.opener:
            self.init_opener()

        url = self.base_url + endpoint
        if params:
            safe_params = {k: str(v) for k, v in params.items()}
            url += '?' + urlencode(safe_params, quote_via=quote)

        if data is not None:
            data = json.dumps(data).encode('utf-8')

        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Accept", "application/json")
        if method == "POST":
            req.add_header("Content-Type", "application/json")

        try:
            with self.opener.open(req) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.URLError as e:
            xbmc.log(f"[kodiseerr] API request failed: {e}", xbmc.LOGERROR)
            xbmc.log(f"[kodiseerr] Failed URL: {url}", xbmc.LOGERROR)
            return None

