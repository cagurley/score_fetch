"""
Based on a sample script provided by NRCCUA:

https://github.com/nrccua/file_export_sample
"""

import datetime as dt
import json
import os
import re
import requests
from pathlib import Path, PurePath
from time import sleep
from urllib.parse import urlparse, unquote


class MissingResponseError(Exception):
    def __init__(*args, **kwargs):
        super().__init__(*args, **kwargs)
        return None


def get_valid_filename(s):
    s = str(s).strip().replace(" ", "_")
    return re.sub(r"[^-\w.]", "", s)


def log(line):
    try:
        with open(Path.cwd().joinpath('fetch.log'), 'a') as log:
            line += '\n'
            log.write(line)
    except OSError:
        print('Log file could not be accessed.')
    finally:
        return None


def plog(line):
    print(line)
    log(line)
    return None


def validate_keys(src, keys=tuple()):
    """
    Return whether keys in src exactly match supplied keys argument.

    src should be a Container, keys should be an Iterable
    """
    for key in keys:
        if key not in src:
            return False
    for key in src:
        if key not in keys:
            return False
    return True


def main():
    try:
        log(f'Fetcher booted from disk at {dt.datetime.now()}')
        while True:
            current = dt.datetime.now().astimezone()
            current = current + dt.timedelta(days=-7)
            next_start = current + dt.timedelta(hours=1)
            plog(f'Cycle begun at {current}')
            try:
                hpath = None
                hdata = None
                if 'HOME' in os.environ:
                    hpath = PurePath(os.environ['HOME'])
                else:
                    hpath = PurePath(os.environ['HOMEDRIVE'] + os.environ['HOMEPATH'])
                hpath = hpath.joinpath('.score_fetch', 'sat.json')
                with open(hpath) as file:
                    hdata = json.load(file)
                if not validate_keys(hdata, ('url',
                                             'dest_dir',
                                             'username',
                                             'password')):
                    raise KeyError('JSON file malformed; provide necessary header data exactly.')
            except (KeyError, OSError, json.JSONDecodeError) as e:
                plog(repr(e))
            else:
                try:
                    # Login and authorization
                    log(f"Login to {hdata['url']} begun")
                    payload = {'username': hdata['username'], 'password': hdata['password']}
                    session = requests.Session()
                    session.headers.update({'Accept': 'application/json', 'Content-Type': 'application/json'})

                    # Determine files to download
                    log(f"Request for undelivered files begun")
                    response_json = session.post(f"{hdata['url']}/files/list",
                                                 data=json.dumps(payload),
                                                 params={'fromDate': f"{dt.datetime.strftime(current, '%Y-%m-%dT%H:%M:%S%z')}"}).json()
                    files_to_download = []
                    if response_json['files']:
                        download_url = f"{hdata['url']}/file"
                        for file in response_json['files']:
                            download_response_json = session.post(download_url,
                                                                  data=json.dumps(payload),
                                                                  params={'filename': file['fileName']}).json()
                            if "fileUrl" in download_response_json:
                                files_to_download.append(download_response_json["fileUrl"])


                    # Download files
                    if len(files_to_download) == 0:
                        log('No undelivered files to download found')
                    else:
                        for file in files_to_download:
                            # Get the file name from the url, unescape it, and then replace whitespace with underscore
                            filename = urlparse(file)
                            filename = get_valid_filename(unquote(PurePath(filename.path).name))
                            download_path = PurePath(hdata['dest_dir']).joinpath(filename)
                            plog(f"Downloading file from url {file}")
                            # DON'T USE THE SESSION HERE
                            download_response = requests.get(file, allow_redirects=True, stream=True)
                            if download_response.ok:
                                print(f"Writing file to {download_path}.")
                                with open(download_path, "wb") as f:
                                    for chunk in download_response.iter_content(chunk_size=1024):
                                        if chunk:
                                            f.write(chunk)
                                log(f'Download to {download_path} successful')
                            else:
                                raise requests.RequestException(f"There was an error retrieving {file} with status code {download_response.status_code}.\n{download_response.content}")
                except (OSError,
                        json.JSONDecodeError,
                        requests.RequestException,
                        requests.ConnectionError,
                        requests.HTTPError,
                        requests.URLRequired,
                        requests.TooManyRedirects,
                        requests.ConnectTimeout,
                        requests.ReadTimeout,
                        requests.Timeout,
                        MissingResponseError) as e:
                    plog(repr(e))
                finally:
                    session.close()
            current = dt.datetime.now().astimezone()
            sleep_interval = (next_start - current).seconds
            if sleep_interval > 0:
                plog(f'Cycle ended and sleep begun at {current}')
                print(f'Next cycle will begin at {next_start}')
                sleep(sleep_interval)
            else:
                plog('Cycle took longer than one hour to complete')
            if os.name == 'nt':
                os.system('cls')
            else:
                os.system('clear')
    except KeyboardInterrupt:
        plog(f'Fetcher terminated via keyboard interrupt at {dt.datetime.now()}')


if __name__ == '__main__':
    main()