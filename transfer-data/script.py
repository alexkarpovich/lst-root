
import psycopg2
from psycopg2 import Error
import json
import codecs
from collections import defaultdict
import traceback
import sys

sets_map = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: dict)))))))
expression_map = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: dict)))
translation_map = defaultdict(lambda: defaultdict(lambda: dict))
transcription_map = defaultdict(lambda: defaultdict(lambda: dict))


def transfer_sets_expressions(connection):
    text = codecs.open('./full_set.json', 'r', 'utf-8-sig')
    data = json.load(text)    

    for i in data:
        node_name = i['x.name'].strip()
        evalue = i['t.value'].strip()
        tvalue = i['tt.value'].strip()
        tsc = i['tr.transcription'].strip()
        details = i['tr.details'].strip()
        
        sets_map[node_name]['x'][evalue]['tr'][tvalue]['comment'] = details
        expression_map[evalue]['lang'] = 'zh'
        expression_map[tvalue]['lang'] = 'ru'

        if len(tsc) > 0:
            sets_map[node_name]['x'][evalue]['tr'][tvalue]['tsc'][tsc] = True
            expression_map[evalue]['tsc'][tsc] = True
            transcription_map[tsc]['id'] = None
        
        # print('{} {} {} ({}, {})'.format(i['x.name'], i['t.value'], i['tt.value'], i['tr.transcription'], i['tr.details']))

    for tvalue in list(transcription_map.keys()):
        with connection.cursor() as cursor:
            tsc_id = None
            cursor.execute("""INSERT INTO transcriptions (type, value) VALUES(%s, %s) ON CONFLICT (type, value) DO NOTHING RETURNING id""", [30, tvalue])
            res = cursor.fetchone()
            
            if res:
                tsc_id = res[0]
            else:
                cursor.execute("SELECT id FROM transcriptions WHERE type=%s AND value=%s", [30, tvalue])
                tsc_id = cursor.fetchone()[0]

            transcription_map[tvalue]['id'] = tsc_id    
    
    for evalue, edata in expression_map.items():
        print(evalue)
        with connection.cursor() as cursor:
            cursor.execute("""INSERT INTO expressions (value, lang) VALUES(%s, %s) ON CONFLICT (value, lang) DO NOTHING RETURNING id""", [evalue, edata['lang']])
            res = cursor.fetchone()
            e_id = None

            if res:
                e_id = res[0]
            else:
                cursor.execute("SELECT id FROM expressions WHERE value=%s AND lang=%s", [evalue, edata['lang']])
                e_id = cursor.fetchone()[0]

            expression_map[evalue]['id'] = e_id

            if edata['lang'] == 'ru':
                continue
            
            print(list(edata['tsc'].keys()))
            for tvalue in list(edata['tsc'].keys()):
                tsc_id = transcription_map[tvalue]['id']
                cursor.execute("""INSERT INTO expression_transcription (expression_id, transcription_id) VALUES(%s, %s) ON CONFLICT (expression_id, transcription_id) DO NOTHING""", [e_id, tsc_id])

    for sname, svalue in sets_map.items():
        if "id" not in svalue:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO nodes (type, name, visibility) 
                    VALUES(%s,%s,%s) RETURNING id
                """, [1, sname, 1])
                node_id = cursor.fetchone()[0]

                cursor.execute("INSERT INTO group_node (group_id, node_id, path) VALUES(%s, %s, %s)", [1, node_id, ""])
                sets_map[sname]['id'] = node_id

        for evalue, edata in svalue['x'].items():
            if 'id' not in edata:
                e_id = None

                with connection.cursor() as cursor:
                    args = [evalue, 'zh']
                    cursor.execute("""SELECT id FROM expressions WHERE value=%s AND lang=%s""", args)
                    res = cursor.fetchone()
                    e_id = res[0]                   

                    cursor.execute("""INSERT INTO node_expression (node_id, expression_id) VALUES(%s, %s) ON CONFLICT (node_id, expression_id) DO NOTHING""", [sets_map[sname]['id'], e_id])          
                sets_map[sname]['x'][evalue]['id'] = e_id
                expression_map[evalue]['id'] = e_id

            for tvalue, tdata in edata['tr'].items():
                if 'id' not in tdata:
                    t_id = None
                    te_id = None
                    e_id = expression_map[evalue]['id']
                    te_id = expression_map[tvalue]['id'] 

                    with connection.cursor() as cursor:
                        cursor.execute("""SELECT id FROM translations WHERE type=%s AND target_id=%s AND native_id=%s""", [1, e_id, te_id])
                        res = cursor.fetchone()
                        if res:
                            t_id = res[0]
                        else:
                            cursor.execute("""INSERT INTO translations (type, target_id, native_id, comment) VALUES(%s, %s, %s, %s) RETURNING id""", [1, e_id, te_id, tdata['comment']])
                            t_id = cursor.fetchone()[0] 

                        cursor.execute("""INSERT INTO node_translation (node_id, translation_id) VALUES(%s, %s) ON CONFLICT (node_id, translation_id) DO NOTHING""", [sets_map[sname]['id'], t_id]) 
                        print('{} {} {} {}'.format(sname, evalue, tvalue, list(tdata['tsc'].keys())))
                        for tsc in list(tdata['tsc'].keys()):
                            tsc_id = transcription_map[tsc]['id']
                            cursor.execute("""INSERT INTO translation_transcription (translation_id, transcription_id) VALUES(%s, %s) ON CONFLICT (translation_id, transcription_id) DO NOTHING""", [t_id, tsc_id])               
                        

try:
    connection = psycopg2.connect(user="postgres",
                                  password="postgres",
                                  host="127.0.0.1",
                                  port="5432",
                                  database="dev")

    transfer_sets_expressions(connection)

    connection.commit()

except (Exception, Error) as error:
    print(traceback.format_exc())
finally:
    if connection:
        # connection.rollback()
        connection.close()