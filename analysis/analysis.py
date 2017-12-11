
import json
import pandas as pd


def get_iperf_data(source_file, import_all: bool = False) -> pd.DataFrame:
    with open(source_file, 'r') as f:
        raw_data = json.load(f)
    raw_data_frame = [x['streams'][0] for x in raw_data['intervals']]
    if not raw_data_frame:
        raise ValueError('Missing data')
    df = pd.DataFrame(raw_data_frame)
    if not import_all:
        df = df[['bits_per_second', 'bytes', 'start', 'packets']]

    try:
        raw_data_server = [x['streams'][0] for x in raw_data['server_output_json']['intervals']]
    except KeyError:
        raise ValueError('Missing data')
    df_server = pd.DataFrame(raw_data_server)
    if not import_all:
        df_server = df_server[['bits_per_second', 'bytes', 'start', 'packets', 'jitter_ms', 'lost_packets']]
    df_server.columns = ['server_' + x for x in df_server.columns]
    result = pd.concat([df, df_server], axis=1)
    # df_server = df_server.set_index('start')

    server = raw_data['server_output_json']['start']['system_info'].split(' ')[1]
    client = raw_data['start']['system_info'].split(' ')[1]
    conn = sorted([client, server])
    result['cookie'] = raw_data['start']['cookie']
    result['timestamp'] = raw_data['start']['timestamp']['time']
    result['server'] = server
    result['client'] = client
    result['connection'] = ' '.join(conn)
    result['mode'] = 'Access Point' if conn[0] == server else 'Client'

    # df.columns = ['bits per sec', 'bytes']
    return result
