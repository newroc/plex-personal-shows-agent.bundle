import os, json
import urllib
import hashlib
from Helpers import clear_posters

class PersonalShowsAgent(Agent.TV_Shows):
    name, primary_provider, fallback_agent, contributes_to, accepts_from, languages, persist_stored_files = 'NewrocPersonal Shows', True, None,['com.plexapp.agents.thetvdb'], ['com.plexapp.agents.localmedia'], [Locale.Language.NoLanguage],False

    def search(self, results, media, lang):
        Log.Info('进入search()')
        filename = String.Unquote(media.filename)
        infoData = LoadAnyJSON(os.path.splitext(filename)[0] + '.info.json')
        Log.Info('加载: %s 从: %s' % (infoData['title'], os.path.splitext(filename)[0] + '.info.json'))
        if infoData:
            ytdl_id = 'movie-' + infoData['extractor'] + '-' + infoData['id']
            metadata = MetadataSearchResult(
                id=ytdl_id,
                name=infoData['title'],
                year=int(infoData['upload_date'][:4]) if 'upload_date' in infoData else None,
                score=infoData['average_rating'] if 'average_rating' in infoData else 100,
                lang=lang
            )
            results.Append(metadata)
            Log.Info('metadata=: %s ' % (metadata))
        
        #Log.Info('Searching Metadata')
        #x = "My Title %s %s %s" % (media.name, media.episode, media.season)
        #results.Append(MetadataSearchResult(id = media.filename, score = 100, name=media.filename, lang=Locale.Language.NoLanguage))

    def update_season(self, season_id, summary):
        Log.Info(' 进入update_season()')
        ip_address = Prefs['ip_address']
        port = Prefs['port']
        username = Prefs['username']
        password = Prefs['password']
        
        if not ip_address or not port or not username or not password:
            Log.Info('Missing Preferences, Skipping Summary Update')
            return

        host = '%s:%s' % (ip_address, port)
        HTTP.SetPassword(host, username, password)

        metadata = json.loads(HTTP.Request(url=('http://%s/library/metadata/%s' %(host, season_id)), immediate=True, headers={'Accept': 'application/json'}).content)
        section_id = metadata['MediaContainer']['librarySectionID']
        Log.Info('HAHA_season_id='+season_id+";summary="+summary+";metadata:"+metadata)
        request = HTTP.Request(url=('http://%s/library/sections/%s/all?summary.value=%s&type=3&id=%s' % (host, section_id, urllib.quote(summary), season_id)), method='PUT' )
        request.load()

    def update_poster(self, metadata, link, base_path = None):
        try:
            Log.Info('更新海报链接: %s base: %s' % (link, base_path))
            if not link or not metadata:
                Log.Info('Skipping poster update. Link or metadata missing')
                return

            if link.startswith('http://') or link.startswith('https://'):
                metadata.posters[link] = Proxy.Preview(None)
                return

            if not link.startswith('/') and not base_path:
                Log.Info('Skipping poster update, link is relative and base path is missing')
                return

            if link.startswith('/'):
                poster_path = link
            else:
                poster_path = os.path.normpath(os.path.join(base_path, link))
                if not os.path.exists(poster_path):
                    poster_path = os.path.normpath(os.path.join(base_path, '../', link))

            Log.Info('海报路径 %s' % (poster_path))
            data = Core.storage.load(poster_path)
            media_hash = hashlib.md5(data).hexdigest()
            metadata.posters[media_hash] = Proxy.Media(data)
        except Exception as e:
            Log.Error('Error updating poster %s' % e.message)

    def update(self, metadata, media, lang):
        Log.Info('进入update()')
        tempSeason=media.seasons[media.seasons.keys()[0]];
        tempEpisodes=tempSeason.episodes[tempSeason.episodes.keys()[0]]
        main_path = tempEpisodes.items[0].parts[0].file
        filename = String.Unquote(main_path)
        dir_name = os.path.normpath(os.path.join(filename, '../'))
        show_name=os.path.basename(dir_name)
        Log.Info('更新节目信息='+show_name)
        #  main_path = media.seasons['1'].episodes['1'].items[0].parts[0].file

        show_path = os.path.normpath(os.path.join(main_path, '../'))
        meta_path = os.path.join(show_path, 'meta.json')
        Log.Info('meta_path='+meta_path)
        metadata.title = show_name

        #  if not os.path.exists(meta_path):
        #      show_path = os.path.normpath(os.path.join(main_path, '../../'))
        #      meta_path = os.path.join(show_path, 'meta.json')

        #  show_name = os.path.basename(show_path)

        #  Log.Info('meta_path='+meta_path)

        if os.path.exists(meta_path):
            meta_json = json.loads(Core.storage.load(meta_path))
            # Log.Info(meta_json)
            trySet(metadata, 'summary', any(meta_json, ['summary', 'description']))
            trySet(metadata, 'studio', any(meta_json, ['publisher','uploader']))
            # metadata.summary = meta_json.get('summary', '')
            # metadata.studio = meta_json.get('publisher', '')
            metadata.genres.clear()
            for genre in meta_json.get('tags', []):
                metadata.genres.add(genre)

            metadata.roles.clear()
            for actor in meta_json.get('actors', []):
                role = metadata.roles.new()
                role.role = actor.get('role', '')
                role.name = actor.get('name', '')
                role.photo = actor.get('photo', '')
        
            clear_posters(metadata)
            self.update_poster(metadata, meta_json.get('show_thumbnail', 'cover.jpg'), show_path)

        else:
            clear_posters(metadata)
            self.update_poster(metadata, 'cover.jpg', show_path)

        for season_index in media.seasons.keys():
            season_metadata = metadata.seasons[season_index]
            episode_keys = media.seasons[season_index].episodes.keys()
            first_episode_path = media.seasons[season_index].episodes[episode_keys[0]].items[0].parts[0].file
            season_path = os.path.normpath(os.path.join(first_episode_path, '../'))
            season_name = os.path.basename(season_path)

            season_summary = season_name
            Log.Info('更新季信息='+season_name)

            clear_posters(season_metadata)
            #  if meta_json and 'seasons' in meta_json and season_index in meta_json['seasons']:
            #      season_meta_json = meta_json['seasons'][season_index]

            #      self.update_poster(season_metadata, season_meta_json.get('poster', 'cover.jpg'), season_path)
            #      season_summary = ('%s\n%s' % (season_name, meta_json['seasons'][season_index].get('summary', ''))).strip()
            #  else:
            #      self.update_poster(season_metadata, 'cover.jpg', season_path)

            #season_metadata.summary = season_summary
            #self.update_season(media.seasons[season_index].id, season_summary)

            for episode_index in media.seasons[season_index].episodes.keys():
                episode_metadata = season_metadata.episodes[episode_index]
                #episode_path = media.seasons[season_index].episodes[episode_index].items[0].parts[0].file
                #episode_file_name = os.path.basename(episode_path)
                #filtered_name = os.path.splitext(episode_file_name)[0].replace('S%sE%s - ' % (season_index, episode_index), '')
                #episode_name = '%s - %s' %(str(episode_index).zfill(2), filtered_name)

                filename = media.seasons[season_index].episodes[episode_index].items[0].parts[0].file
                seasonDirectory = os.path.dirname(filename)
                showDirectory = os.path.dirname(seasonDirectory)
                episode_info_data = LoadAnyJSON(os.path.splitext(filename)[0] + '.info.json')
                ApplyInfoToMetadata(episode_info_data,episode_metadata)
                #episode_metadata.title = episode_info_data.get("title")
                #episode_metadata.summary=episode_info_data.get("description")
                Log.Info("更新影片信息："+episode_metadata.title)

def LoadAnyJSON(directory, filenames=[]):
    result = False
    if len(filenames) > 0:
        for filename in filenames:
            filename = os.path.join(directory, filename)
            Log.Info("filename="+filename)
            if os.path.exists(filename):
                result = JSON.ObjectFromString(Core.storage.load(filename))
                break
    else:
        try:
            result = JSON.ObjectFromString(Core.storage.load(directory))
        except:
            pass
    return result


def any(hash, keys, default=''):
    for key in keys:
        if key in hash:
            return hash[key]
    return default


def trySet(object, key, value):
    try:
        setattr(object, key, value)
    except:
        pass


def ApplyInfoToMetadata(infoData, metadata):
    trySet(metadata, 'title', any(infoData, ['fulltitle', 'title', 'name']))
    trySet(metadata, 'name', any(infoData, ['name', 'fulltitle', 'title']))
    trySet(metadata, 'original_title', any(infoData, ['original_title', 'fulltitle', 'title', 'name']))
    trySet(metadata, 'duration', infoData['duration'])
    trySet(metadata, 'summary', any(infoData, ['description', 'summary']))
    date = any(infoData, ['upload_date', 'date', 'year'])
    if date:
        date = Datetime.ParseDate(str(date))
        trySet(metadata, 'originally_available_at', date.date())
        trySet(metadata, 'year', date.year)
    trySet(metadata, 'rating', infoData['average_rating'] * 2 if 'average_rating' in infoData else 10.0)
    trySet(metadata, 'content_rating', 0)
    try:
        metadata.directors.clear()
        meta_director = metadata.directors.new()
        meta_director.name = infoData['uploader'] if 'uploader' in infoData else infoData['extractor']
    except:
        pass
    return metadata

def Start():
  HTTP.CacheTime                  = CACHE_1MONTH
  HTTP.Headers['User-Agent'     ] = 'Mozilla/5.0 (iPad; CPU OS 7_0_4 like Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11B554a Safari/9537.54'
  HTTP.Headers['Accept-Language'] = 'en-us'
