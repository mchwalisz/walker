
import json
import pandas as pd
from pathlib import Path
import logging
from matplotlib.ticker import FuncFormatter


def get_iperf(source: Path) -> pd.DataFrame:
    with source.open('r') as f:
        raw_data = json.load(f)
    raw_data_frame = [x['streams'][0] for x in raw_data['intervals']]
    if not raw_data_frame:
        raise ValueError('Missing data')
    df = pd.DataFrame(raw_data_frame)

    try:
        raw_data_server = [x['streams'][0]
            for x in raw_data['server_output_json']['intervals']]
    except KeyError:
        raise ValueError('Missing data')
    df_server = pd.DataFrame(raw_data_server)

    df_server.columns = ['server_' + x for x in df_server.columns]
    result = pd.concat([df, df_server], axis=1)
    # df_server = df_server.set_index('start')

    server = (raw_data['server_output_json']
        ['start']['system_info']).split(' ')[1]
    client = raw_data['start']['system_info'].split(' ')[1]
    conn = sorted([client, server])
    result['cookie'] = raw_data['start']['cookie']
    result['timestamp'] = raw_data['start']['timestamp']['time']
    result['server'] = server
    result['system_info'] = raw_data['start']['system_info']
    # result['server_system_info'] = raw_data['start']['system_info']
    result['kernel'] = raw_data['start']['system_info'].split(' ')[2]
    result['client'] = client
    result['connection'] = ' '.join(conn)
    result['traffic'] = raw_data['start']['test_start']['protocol']
    try:
        result['title'] = raw_data['title']
        key_values = raw_data['title'].split(',')
        if len(key_values) > 2:
            for kv in key_values:
                kv = kv.split(':')
                result[kv[0]] = kv[1]
    except KeyError:
        pass
    result['mode'] = 'Access Point' if conn[0] == server else 'Client'
    result['file'] = source.stem
    result.columns = [x.replace('_', ' ') for x in result.columns]

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
