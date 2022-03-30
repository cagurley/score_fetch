"""
Based on a sample script provided by NRCCUA:
https://github.com/nrccua/file_export_sample
"""

import datetime as dt
import json
import os
import requests
from pathlib import PurePath
from support import *
from zeep import Client
from zeep.exceptions import Error as ZeepError


def fetch(start, today):
    """
    :param start: A date to be saved after a successful fetch
    :param today: Today's date
    :return: None
    """
    try:
        if 'HOME' in os.environ:
            hpath = PurePath(os.environ['HOME'])
        else:
            hpath = PurePath(os.environ['HOMEDRIVE'] + os.environ['HOMEPATH'])
        hpath = hpath.joinpath('.score_fetch', 'toefl.json')
        with open(hpath) as file:
            hdata = json.load(file)
        if not validate_keys(hdata, ('dest_dir',
                                     'username',
                                     'password')):
            raise KeyError('JSON file malformed; provide necessary header data exactly.')
    except (KeyError, OSError, json.JSONDecodeError) as e:
        plog(repr(e))
    else:
        try:
            # Service registration
            end = today - dt.timedelta(days=1)
            log(f"TOEFL service registration begun")
            client = Client('toefl.wsdl')

            # Request records
            log(f"Request for undelivered records begun")
            data = client.service.getScorelinkDataByReportDate(
                userName=hdata['username'],
                password=hdata['password'],
                reportstartdate=start.strftime('%m/%d/%Y'),
                reportenddate=end.strftime('%m/%d/%Y')
            )

            # Retrieve records
            if not data:
                log('No undelivered records found')
            else:
                filepath = Path(hdata['dest_dir']).joinpath(f"toefl_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.txt")
                data = [line for line in data.splitlines()]
                for i, line in enumerate(data):
                    lead = line[:42]
                    names = [line[42:72], line[72:102], line[102:132]]
                    trail = line[132:]
                    for n, name in enumerate(names):
                        if name in [name.upper(), name.lower()]:
                            names[n] = name.title()
                    data[i] = b''.join([lead, *names, trail, b'\n'])
                with open(filepath, 'wb') as f:
                    f.writelines(data)
                plog(f"Wrote new records to {filepath}")

            with open('toefl.dat', 'w') as file:
                file.write(dt.datetime.strftime(today, '%Y-%m-%d') + '\n')
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
                MissingResponseError,
                ZeepError) as e:
            plog(repr(e))
    finally:
        return None
