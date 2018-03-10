#!/usr/bin/env python3

import glob
import http.cookiejar
import json
import os
import re
import subprocess
import requests

USERNAME = ''
PASSWORD = ''
STORAGE = os.path.expanduser('~/src/circle/videos')
COOKIES = os.path.expanduser('~/src/circle/cookies')

def mkdir(*args):
    try:
        os.mkdir(*args)
    except FileExistsError:
        pass

def main():
    s = requests.Session()
    s.cookies = http.cookiejar.MozillaCookieJar()
    s.post('https://video.logi.com/api/accounts/authorization',
           json={'email': USERNAME, 'password': PASSWORD})
    s.cookies.save(COOKIES)
    try:
        os.mkdir(STORAGE)
    except FileExistsError:
        pass
    accessories = s.get('https://video.logi.com/api/accessories').json()
    for accessory in accessories:
        accessoryId = accessory['accessoryId']
        print(accessoryId)

        mkdir(os.path.join(STORAGE, accessoryId))

        startActivityId = None
        while True:
            data = {'operator': '<=',
                    'limit': 100,
                    'filter': 'relevanceLevel = 0 OR relevanceLevel >= 1',
                    'scanDirectionNewer': True}
            if startActivityId:
                data['startActivityId'] = startActivityId
            activities = s.post(f'https://video.logi.com/api/accessories/{accessoryId}/activities', json=data).json()

            for activity in activities['activities']:
                activityId = activity['activityId']
                relevanceLevel = str(activity['relevanceLevel'])

                storage_day = os.path.join(STORAGE, accessoryId, activityId[0:8])
                storage = os.path.join(storage_day, relevanceLevel)

                if glob.glob(os.path.join(storage_day, '*', f'{activityId}.mp4')):
                    continue
                print(activity)

                mkdir(storage_day)
                mkdir(storage)

                subprocess.run([
                    'youtube-dl',
                    '--no-warnings',
                    '--cookies', COOKIES,
                    f'https://video.logi.com/api/accessories/{accessoryId}/activities/{activityId}/mpd',
                    '-o', os.path.join(storage, f'{activityId}.mp4')
                ], check=True)

                mpd = s.get(f'https://video.logi.com/api/accessories/{accessoryId}/activities/{activityId}/mpd').text
                caption = re.search(r'<BaseURL>(.+?\.vtt)</BaseURL>', mpd).group(1)
                with open(os.path.join(storage, f'{activityId}.vtt'), 'wb') as f:
                    f.write(s.get(caption).content)

                subprocess.run([
                    'ffmpeg',
                    '-loglevel', 'error',
                    '-hide_banner',
                    '-stats',
                    '-i', os.path.join(storage, f'{activityId}.mp4'),
                    '-i', os.path.join(storage, f'{activityId}.vtt'),
                    '-map', '0',
                    '-c', 'copy',
                    '-map', '-0:s',
                    '-c:s', 'mov_text',
                    '-map', '1:0',
                    '-metadata:s:s:0', 'language=en',
                    os.path.join(storage, f'{activityId}.temp.mp4')
                ], check=True)
                os.rename(os.path.join(storage, f'{activityId}.temp.mp4'),
                          os.path.join(storage, f'{activityId}.mp4'))
                os.unlink(os.path.join(storage, f'{activityId}.vtt'))

                glacier = json.loads(subprocess.run([
                    'aws', 'glacier', 'upload-archive',
                    '--profile', 'circle',
                    '--account-id', '-',
                    '--vault-name', f'circle-{accessoryId}',
                    '--body', os.path.join(storage, f'{activityId}.mp4'),
                    '--archive-description', f'{activityId}.mp4'
                ], stdout=subprocess.PIPE, check=True).stdout)['archiveId']
                with open(os.path.join(STORAGE, accessoryId, 'glacier'), 'a') as f:
                    print(f'{activityId}\t{glacier}', file=f)

            if 'nextStartTime' in activities:
                startActivityId = activities['nextStartTime']
                continue
            break



if __name__ == '__main__':
    main()
