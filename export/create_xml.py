import csv
import asyncio
import asyncpg
import xml.etree.ElementTree as ET
import yaml
import sys
sys.path.append('../')
import os
import ast

async def load_mapping_from_csv(csv_file):
    mapping = {}
    with open(csv_file, mode='r', encoding='utf-8-sig') as file:
        reader = csv.reader(file)
        for row in reader:
            xml_tag = row[0]
            try:
                db_columns = ast.literal_eval(row[1]) if row[1] else []  # Safely convert string representation of list to actual list
            except ValueError:
                db_columns = [row[1]]  # Handle single string without list
            table_name = row[2] if row[2] else None  # Handle NaN
            if table_name and db_columns:
                mapping[xml_tag] = (db_columns, table_name)
    return mapping

async def fetch_val(conn, column, table):
    query = f"SELECT {column} FROM {table}"
    result = await conn.fetchval(query)
    return result

async def fetch_institution(conn, id_column, id_table, name_column, name_val):
    if id_table in ['baseplate', 'sensor']:
        query = f"""
            SELECT mi.institution
            FROM {id_table}
            JOIN proto_assembly pa ON {id_table}.proto_no = pa.proto_no
            JOIN module_info mi ON pa.module_no = mi.module_no
            WHERE {id_table}.{name_column} = $1
        """

    elif id_table in ['proto_assembly', 'module_assembly', 'hexaboard', 'module_iv_test']:
        query = f"""
            SELECT institution
            FROM module_info
            INNER JOIN {id_table}
            ON {id_table}.module_no = module_info.module_no
            WHERE {id_table}.{id_column} = $1
            """
    
    result = await conn.fetchval(query, name_val)
    return result

async def fetch_value(conn, table, columns):
    if len(columns) == 1:
        query = f"SELECT {columns[0]} FROM {table}"
        result = await conn.fetchval(query)
        return result
    elif len(columns) > 1:
        query = f"SELECT {', '.join(columns)} FROM {table}"
        result = await conn.fetchrow(query)
        if result:
            return {col: result[col] for col in columns}
        else:
            return {col: None for col in columns}

async def insert_values_into_xml(xml_file, mapping, conn, name_column, id_column, id_table, output_dir):
    '''
    name_column: ex. bp_name, proto_name, etc...
    '''
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    # Fetch id and institution
    id = await fetch_val(conn, id_column, id_table)
    name_val = await fetch_val(conn, name_column, id_table)
    institution = await fetch_institution(conn, id_column, id_table, name_column, name_val)
    
    # Placeholder values to replace
    placeholders = {'ID': name_val, 'LOCATION': institution}

    for xml_tag, info in mapping.items():
        columns = info[0]
        table = info[1]

        if xml_tag not in placeholders:
            if len(columns) > 1 and xml_tag in ['RUN_BEGIN_TIMESTAMP_', 'RUN_END_TIMESTAMP_', 'KIND_OF_PART', 'CURE_BEGIN_TIMESTAMP_', 'CURE_END_TIMESTAMP_']:
                # Special handling for combined columns
                value = await fetch_value(conn, table, columns)
                if xml_tag == 'RUN_BEGIN_TIMESTAMP_' or 'RUN_END_TIMESTAMP_':
                    placeholders[xml_tag] = f"{value[columns[0]]}T{value[columns[1]]}"
                elif xml_tag == 'KIND_OF_PART':
                    if id_table == 'module_assembly':
                        placeholders[xml_tag] = f"{value[columns[0]]} Si Module {value[columns[1]]} {value[columns[2]]}"
                    else:    
                        placeholders[xml_tag] = f"{value[columns[0]]}_{value[columns[1]]}"
    
                elif xml_tag == 'CURE_BEGIN_TIMESTAMP_':
                    placeholders[xml_tag] = f"{value[columns[0]]}T{value[columns[1]]}"
                elif xml_tag == 'CURE_END_TIMESTAMP_':
                    placeholders[xml_tag] = f"{value[columns[0]]}T{value[columns[1]]}"
            else:
                value = await fetch_value(conn, table, columns)
                placeholders[xml_tag] = value if not isinstance(value, dict) else value

    # print the retreived data
    print(f"you are going to export the following data to xml file")
    print("-"*10)
    print(placeholders)
    print("-"*10)

   # Insert values into XML by replacing placeholders
    for element in root.iter():
        if element.text:
            for xml_tag, value in placeholders.items():
                if isinstance(value, dict):
                    for col, val in value.items():
                        placeholder = f"{{{{ {col} }}}}"
                        if placeholder in element.text:
                            element.text = element.text.replace(placeholder, str(val) if val is not None else '')
                else:
                    placeholder_lower = f"{{{{ {xml_tag.lower()} }}}}"
                    placeholder_upper = f"{{{{ {xml_tag.upper()} }}}}"
                    placeholder = f"{{{{ {xml_tag} }}}}"
                    
                    if placeholder_lower in element.text:
                        element.text = element.text.replace(placeholder_lower, str(value) if value is not None else '')
                    if placeholder_upper in element.text:
                        element.text = element.text.replace(placeholder_upper, str(value) if value is not None else '')
                    if placeholder in element.text:
                        element.text = element.text.replace(placeholder, str(value) if value is not None else '')

    # Save the updated XML to the directory
    os.makedirs(output_dir, exist_ok=True)
    output_xml_filename = name_val + '_' + xml_file.split('/')[-1]## generated xml file = id + xml filename
    output_file = os.path.join(output_dir, os.path.basename(output_xml_filename))
    tree.write(output_file)
    print(f'Successfully created {output_file}')

async def main():
    id_table = input(f'Choose one from proto_assembly/baseplate/module_assembly/sensor/hxb/module_iv_test -- ')
    xml_type = ['build_upload', 'cond_upload', 'assembly_upload', 'module_iv']
    _xml_type = input(f'Choose one from {xml_type} -- ')
    assert _xml_type in xml_type, 'Invalid xml type.'

    if id_table == 'proto_assembly':
        ## test protomodule/cond_upload.xml
        params = {'id_table': 'proto_assembly', 
                'id_column': 'proto_name',
                'name_column': 'proto_name',
                'csv_path': f'protomodule/{_xml_type}.csv',
                'xml_temp_path': f'protomodule/{_xml_type}.xml',
                'xml_output_path': 'protomodule'}
    elif id_table == 'baseplate':
        ## test baseplate/cond_upload.xml
        params = {'id_table': 'baseplate', 
                'id_column': 'bp_no',
                'name_column': 'bp_name',
                'xml_temp_path': f'baseplate/{_xml_type}.xml',
                'csv_path': f'baseplate/{_xml_type}.csv',
                'xml_output_path': 'baseplate'}
    elif id_table == 'module_assembly':
        ## test module/cond_upload.xml
        params = {'id_table': 'module_assembly', 
                'id_column': 'module_name',
                'name_column': 'module_name',
                'csv_path': f'module/{_xml_type}.csv',
                'xml_temp_path': f'module/{_xml_type}.xml',
                'xml_output_path': 'module'}
    elif id_table == 'sensor':
        ## test module/cond_upload.xml
        params = {'id_table': 'sensor', 
                'id_column': 'sen_no',
                'name_column': 'sen_name',
                'csv_path': f'sensor/{_xml_type}.csv',
                'xml_temp_path': f'sensor/{_xml_type}.xml',
                'xml_output_path': 'sensor'}
    elif id_table == 'hxb':
        ## test module/cond_upload.xml
        params = {'id_table': 'hexaboard', 
                'id_column': 'hxb_no',
                'name_column': 'hxb_name',
                'csv_path': f'hxb/{_xml_type}.csv',
                'xml_temp_path': f'hxb/{_xml_type}.xml',
                'xml_output_path': 'hxb'}
    elif id_table == 'module_iv_test':
        ## test protomodule/cond_upload.xml
        params = {'id_table': 'module_iv_test', 
                'id_column': 'module_no',
                'name_column': 'module_name',
                'csv_path': f'testing/{_xml_type}.csv',
                'xml_temp_path': f'testing/{_xml_type}.xml',
                'xml_output_path': 'testing'}

    # Load mapping
    mapping = await load_mapping_from_csv(f"../export/var_match_up/{params['csv_path']}")## worked. 

    # Connect to PostgreSQL
    loc = '../dbase_info/'
    yaml_file = f'{loc}tables.yaml'
    db_params = {
        'database': yaml.safe_load(open(yaml_file, 'r'))['dbname'],
        'user': 'postgres',   
        # 'password': input('Set superuser password: '),
        'password': 'hgcal',
        'host': yaml.safe_load(open(yaml_file, 'r'))['db_hostname'],  
        'port': yaml.safe_load(open(yaml_file, 'r'))['port']        
    }

    # establish a connection with database
    conn = await asyncpg.connect(user=db_params['user'], 
                                password=db_params['password'], 
                                host=db_params['host'], 
                                database=db_params['database'],
                                port=db_params['port'])
    
    xml_temp_dir = '../export/template_examples/' + params['xml_temp_path']
    output_dir = 'converted_xml/' + params['xml_output_path']## change this on database computer to the different dir

    try:
        await insert_values_into_xml(xml_temp_dir, mapping, conn, params['name_column'], params['id_column'], params['id_table'], output_dir)
    finally:
        await conn.close()
if __name__ == '__main__':
    asyncio.run(main())
