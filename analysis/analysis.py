
import json
import pandas as pd
from pathlib import Path
import logging
from matplotlib.ticker import FuncFormatter


def get_iperf(source: Path) -> pd.DataFrame:
    with source.open('r') as f:
        raw_data = json.load(f)

    intervals = [x['streams'][0] for x in raw_data['intervals']]
    if not intervals:
        raise ValueError('Missing data')

    result = pd.DataFrame(intervals)

    result['client'] = raw_data['title'].split(' ')[3]
    result['server'] = raw_data['title'].split(' ')[1]
    result['kernel'] = raw_data['start']['system_info'].split(' ')[2]

    result['timestamp'] = raw_data['start']['timestamp']['time']
    result['system_info'] = raw_data['start']['system_info']
    result['protocol'] = raw_data['start']['test_start']['protocol']

    result['file'] = source.stem

    return result


def get_iperf_folder(source: Path, recursive: bool = False) -> pd.DataFrame:
    dfl = []
    if recursive:
        file_list = source.rglob('*.json')
    else:
        file_list = source.glob('*.json')

    for fname in file_list:
        logging.debug(f'loading {fname}')
        try:
            df1 = get_iperf(fname)
            dfl.append(df1)
        except ValueError:
            continue
    df = pd.concat(dfl)
    return df


def bitrate(x, pos):
    'The two args are the value and tick position'
    if x >= 1e6:
        return '{:1.0f}M'.format(x * 1e-6)
    return '{:1.0f}K'.format(x * 1e-3)


bitrate_formatter = FuncFormatter(bitrate)
