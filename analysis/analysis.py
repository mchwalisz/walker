
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

    result['Client'] = raw_data['title'].split(' ')[3]
    result['Access Point'] = raw_data['title'].split(' ')[1]
    result['Kernel'] = raw_data['start']['system_info'].split(' ')[2]

    result['Timestamp'] = raw_data['start']['timestamp']['time']
    result['System Info'] = raw_data['start']['system_info']
    result['Protocol'] = raw_data['start']['test_start']['protocol']

    result['Connection'] = ['{0[0]} \& {0[1]}'.format(sorted(elem))
        for elem in zip(result['Access Point'], result['Client'])]

    result['file'] = source.stem

    result.columns = [x.replace('_', ' ') for x in result.columns]
    result = result.rename(columns={
        'bits per second': 'Throughput [Mbps]',
    })

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
    return '{:1.0f}'.format(x * 1e-6)


bitrate_formatter = FuncFormatter(bitrate)
