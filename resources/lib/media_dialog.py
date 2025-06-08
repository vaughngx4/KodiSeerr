import xbmcgui
import xbmc
import xbmcplugin
import sys
import urllib.parse
import json

class MediaDialog(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.media = kwargs.get('media', {})
        self.media_info = self.media.get('mediaInfo', {})
        self.status_code = self.media_info.get('status', 0)
        self.status_text = self.media.get('status', 'Unknown')

    def onInit(self):
        poster = self.media.get('poster') or self.media.get('poster_path')
        if poster:
            try:
                self.getControl(100).setImage(poster)
            except Exception:
                pass

        title = self.media.get('title') or self.media.get('name') or 'Unknown'
        self._set_label(101, title)
        self._set_label(102, self.media.get('tagline', ''))

        self._set_textbox(103, self.media.get('overview', ''))

        release_date = self.media.get('releaseDate') or self.media.get('firstAirDate') or 'Unknown'
        self._set_label(110, f"Release Date: {release_date}")

        rating = self.media.get('voteAverage')
        self._set_label(111, f"Rating: {rating}/10" if rating else "Rating: N/A")

        genres = ", ".join(g['name'] for g in self.media.get('genres', []))
        self._set_label(112, f"Genres: {genres or 'N/A'}")

        runtime = self.media.get('runtime')
        if not runtime:
            episode_runtimes = self.media.get('episodeRunTime', [])
            runtime = episode_runtimes[0] if episode_runtimes else 0
        self._set_label(113, f"Runtime: {runtime} min" if runtime else "Runtime: Unknown")

        try:
            langs = ", ".join(
                l.get('english_name') or l.get('name') or l.get('iso_639_1', 'Unknown')
                for l in self.media.get('spokenLanguages', [])
            )
        except Exception as e:
            xbmc.log(f"[KodiSeerr] Failed parsing languages: {e}", xbmc.LOGERROR)
            langs = "Unknown"
        self._set_label(114, f"Language(s): {langs or 'Unknown'}")

        cast = self.media.get('credits', {}).get('cast', [])[:3]
        top_cast = ", ".join(f"{c['name']} ({c['character']})" for c in cast)
        self._set_label(115, f"Top Cast: {top_cast or 'N/A'}")

        companies = ", ".join(c['name'] for c in self.media.get('productionCompanies', []))
        self._set_label(116, f"Produced by: {companies or 'N/A'}")

        if 'numberOfSeasons' in self.media:
            self._set_label(117, f"Seasons: {self.media['numberOfSeasons']} | Episodes: {self.media.get('numberOfEpisodes', 'N/A')}")
        else:
            self._set_label(117, '')
        self._set_label(118, f"Show Status: {self.status_text}")

        self._apply_status_logic()

    def _set_label(self, control_id, text):
        try:
            self.getControl(control_id).setLabel(text)
        except Exception:
            pass

    def _set_textbox(self, control_id, text):
        try:
            self.getControl(control_id).setText(text)
        except Exception:
            pass

    def _set_visible(self, control_id, visible):
        try:
            self.getControl(control_id).setVisible(visible)
        except Exception:
            pass

    def _apply_status_logic(self):
        self._set_visible(106, False)
        self._set_visible(107, False)
        self._set_visible(109, False)
        self._set_label(108, '')

        if self.status_code == 3:
            self._set_label(108, '[COLOR blue]REQUESTED[/COLOR]')
        elif self.status_code == 4:
            self._set_label(108, '[COLOR green] PARTIALLY AVAILABLE[/COLOR]')
            self._set_visible(106, True)
            self._set_visible(109, True)
        elif self.status_code == 5:
            self._set_label(108, '[COLOR green]READY TO WATCH[/COLOR]')
            self._set_visible(106, True)
        else:
            self._set_visible(107, True)

    def onClick(self, controlId):
        if controlId == 105:
            self.close()

        elif controlId == 106:  # Watch Now
            media_type = self.media_info.get('mediaType')
            title = self.media.get('title') or self.media.get('name')

            if media_type == 'movie':
                file_path = self._find_movie_path_by_title(title)
            elif media_type == 'tv':
                file_path = self._find_first_unwatched_episode(title)
            else:
                file_path = None

            if file_path:
                xbmcgui.Dialog().notification("KodiSeerr", "Playing from library...", xbmcgui.NOTIFICATION_INFO)
                xbmc.Player().play(file_path)
            else:
                xbmcgui.Dialog().notification("KodiSeerr", "Media not found in library", xbmcgui.NOTIFICATION_ERROR)

            self.close()

        elif controlId == 107 or controlId == 109:
            media_type = "tv" if self.media.get('numberOfEpisodes') else "movie"
            id = self.media.get('id')
            mode = 'list_seasons' if media_type == 'tv' else 'request'
            url = sys.argv[0] + '?' + urllib.parse.urlencode({
                'mode': mode,
                'type': media_type,
                'id': id
            })
            xbmc.executebuiltin(f'RunPlugin({url})')
            self.close()

    def _find_movie_path_by_title(self, title):
        query = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "VideoLibrary.GetMovies",
            "params": {
                "properties": ["file"],
                "filter": {"field": "title", "operator": "is", "value": title}
            }
        }
        response = xbmc.executeJSONRPC(json.dumps(query))
        data = json.loads(response)
        try:
            return data['result']['movies'][0]['file']
        except Exception as e:
            xbmc.log(f"[KodiSeerr] Movie not found: {e}", xbmc.LOGWARNING)
            return None

    def _find_first_unwatched_episode(self, show_title):
        # Step 1: Get TV show ID
        query = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "VideoLibrary.GetTVShows",
            "params": {
                "properties": ["title"],
                "filter": {"field": "title", "operator": "is", "value": show_title}
            }
        }
        response = xbmc.executeJSONRPC(json.dumps(query))
        data = json.loads(response)

        try:
            tvshowid = data['result']['tvshows'][0]['tvshowid']
        except Exception:
            xbmc.log(f"[KodiSeerr] TV show not found in library: {show_title}", xbmc.LOGWARNING)
            return None

        # Step 2: Try to get first unwatched episode
        episode_query = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "VideoLibrary.GetEpisodes",
            "params": {
                "tvshowid": tvshowid,
                "properties": ["playcount", "file"],
                "filter": {"field": "playcount", "operator": "is", "value": "0"},
                "sort": {"order": "ascending", "method": "episode"}
            }
        }
        ep_response = xbmc.executeJSONRPC(json.dumps(episode_query))
        ep_data = json.loads(ep_response)

        episodes = ep_data.get('result', {}).get('episodes', [])
        if episodes:
            return episodes[0]['file']

        # Step 3: Fallback - get first episode regardless of playcount
        fallback_query = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "VideoLibrary.GetEpisodes",
            "params": {
                "tvshowid": tvshowid,
                "properties": ["file"],
                "sort": {"order": "ascending", "method": "episode"}
            }
        }
        fb_response = xbmc.executeJSONRPC(json.dumps(fallback_query))
        fb_data = json.loads(fb_response)

        try:
            return fb_data['result']['episodes'][0]['file']
        except Exception:
            xbmc.log(f"[KodiSeerr] No episodes found for fallback on show: {show_title}", xbmc.LOGWARNING)
            return None

