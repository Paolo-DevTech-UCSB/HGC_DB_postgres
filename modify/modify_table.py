import csv
import os
import asyncio
import asyncpg
sys.path.append('../')
from HGC_DB_postgres.src.utils import connect_db

'''
logic:
1. extract the existing table schema
2. read the updated schema from csv File
3. Compare 1 and 2
4. Apply the changes
'''

# 1. extract the existing table schema
async def get_existing_table_schema(conn, table_name: str):
    query = f"""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = '{table_name}';
    """
    rows = await conn.fetch(query)
    existing_schema = {row['column_name']: row['data_type'] for row in rows}
    return existing_schema

# 2. read the updated schema from csv File
def get_desired_table_schema_from_csv(csv_file_path: str):
    desired_schema = {}
    with open(csv_file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            column_name = row[0]
            data_type = row[1]
            desired_schema[column_name] = data_type
    return desired_schema

# 3. Compare 1 and 2
def compare_schemas(existing_schema: dict, desired_schema: dict):
    changes = []
    existing_columns = set(existing_schema.keys())
    desired_columns = set(desired_schema.keys())

    renamed_columns = []
    for existing_col in existing_columns:
        existing_type = existing_schema[existing_col]
        for desired_col in desired_columns:
            if existing_type == desired_schema[desired_col] and existing_col != desired_col:
                renamed_columns.append((existing_col, desired_col))
                existing_columns.remove(existing_col)
                desired_columns.remove(desired_col)
                break
    
    for old_col, new_col in renamed_columns:
        changes.append(('rename_column', old_col, new_col))

    for column, new_type in desired_schema.items():
        if column in existing_schema:
            old_type = existing_schema[column]
            if old_type != new_type:
                changes.append(('datatype', column, old_type, new_type))
        else:
            changes.append(('new_column', column, None, new_type))
    
    for column in existing_schema:
        if column not in desired_schema:
            changes.append(('remove_column', column, existing_schema[column], None))
    
    return changes

# 4. Apply the changes - datatype
async def change_column_datatype(conn, table_name: str, column_name: str, old_datatype: str, new_datatype: str):
    alter_query = f"""
    ALTER TABLE {table_name}
    ALTER COLUMN {column_name} TYPE {new_datatype}
    USING {column_name}::{new_datatype};
    """
    await conn.execute(alter_query)
    print(f"Column {column_name} in table {table_name} changed from {old_datatype} to {new_datatype}.")

# 4. Apply the changes - rename column
async def change_column_name(conn, table_name: str, old_col_name: str, new_col_name: str):
    alter_query = f"""
    ALTER TABLE {table_name}
    RENAME COLUMN {old_col_name} TO {new_col_name};
    """
    await conn.execute(alter_query)
    print(f"Column {old_col_name} in table {table_name} renamed to {new_col_name}.")

# 4. Apply the changes
async def apply_changes(conn, table_name: str, changes):
    for change in changes:
        if change[0] == 'datatype':
            _, column, old_type, new_type = change
            await change_column_datatype(conn, table_name, column, old_type, new_type)
        elif change[0] == 'new_column':
            _, column, _, new_type = change
            alter_query = f"ALTER TABLE {table_name} ADD COLUMN {column} {new_type};"
            await conn.execute(alter_query)
            print(f"Column {column} added to table {table_name}.")
        elif change[0] == 'remove_column':
            _, column, _, _ = change
            alter_query = f"ALTER TABLE {table_name} DROP COLUMN {column};"
            await conn.execute(alter_query)
            print(f"Column {column} removed from table {table_name}.")
        elif change[0] == 'rename_column':
            _, old_col_name, new_col_name = change
            await change_column_name(conn, table_name, old_col_name, new_col_name)

async def main():
    conn = connect_db()
    
    csv_directory = 'HGC_DB_postgres/dbase_info/'
    for filename in os.listdir(csv_directory):
        if filename.endswith('.csv'):
            csv_file_path = os.path.join(csv_directory, filename)
            table_name = os.path.splitext(filename)[0]  # Assuming table name is the same as CSV file name
            existing_schema = await get_existing_table_schema(conn, table_name)
            desired_schema = get_desired_table_schema_from_csv(csv_file_path)
            changes = compare_schemas(existing_schema, desired_schema)
            await apply_changes(conn, table_name, changes)
    
    await conn.close()

asyncio.run(main())
