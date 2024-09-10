This documentation pertains to this project: https://github.com/kai-ucsb/Gantry

# Getting started: Connecting to the local DB
1. Under `UCSB-Gantry-HEP-main/Assembly Data/Database Config/type_at_institutions`, verify that the correct types of modules are present for you institution.
2. Under `UCSB-Gantry-HEP-main/Assembly Data/Database Config/`, open `conn.txt` preferably in Excel or VS Code. Set database connection info in the following order while carefully avoiding trailing spaces.
     1. database IP address
     2.  database name (default: `hgcdb`)
     3.  user (`gantry_user`)
     4.  password
### Example for `conn.txt`
```
dbase.phys.school.edu
hgcdb
gantry_user
user_password
```


3. Under `UCSB-Gantry-HEP-main/Assembly Data/Controllers`:
  - Verify the region numbers in `Regions.txt`.
  - Edit `Institution.txt` with the abbreviation of your institution (`CMU`, `IHEP`, `NTU`, `TTU`, `TIFR`, `UCSB`).
  - Save the CERN IDs of your technicians in `Operators.txt` one person per line with no trailing spaces.
  - Set the Python 3 version under `Python.txt`.
    - You will require Python 3.6 and greater.
    - Please install [`asyncpg`](https://pypi.org/project/asyncpg/) for this python version.
    - Please read the instructions on [Automatic Protomodule Naming](https://github.com/cmu-hgc-mac/HGC_DB_postgres/blob/main/documentation/gantry/README.md#Automatic-Protomodule-Naming) when using for the first time.
  

# Using the database
- Open the project
- Under `Main VIs`, open `Manual Assembly DB.vi`.

![image](https://github.com/user-attachments/assets/ecb34a19-4e8a-4fb5-a8d2-d61a54c10104)

![image](https://github.com/user-attachments/assets/7cf8146d-eb93-4480-a4f5-45348839fc6d)

![image](https://github.com/user-attachments/assets/143eae7c-d0d5-4435-97d6-c84926c5100c)

# Automatic Protomodule Naming

# More Documentation
- Database queries are in `UCSB-Gantry-HEP-main/Main VIs/python_db/postgres_tools.py`.
- Protomodules and modules are declared with `Stack.lvclass` and database entries are tracked with `Database Entry.lvclass`.
- [Developer notes here - Google Slides](https://docs.google.com/presentation/d/1HBvVTkyuiU_mZnNuGw4U_Wn2-F3KMbM-lAi5Qyut9t0/edit#slide=id.p)

# Test connection
- **Test connection**: Run the following in `python3` on the gantry python installation with the appropriate **database hostname and password**.
<pre>
import asyncpg, asyncio
conn = asyncio.run(asyncpg.connect(
        host=<b>'db_hostname.phys.school.edu'</b>,
        password=<b>'gantry_user_password'</b>,
        database='hgcdb',
        user='gantry_user'))
print('Connection successful!')
</pre>
- **Test connection with LabVIEW**: Run `Main VIs/python_db/check_db_conn.vi` to troubleshoot python, database, and LabVIEW interconnection.

# Debugging
- Run `Database Entry.lvclass:Initiate Assembly.vi` with `Database Entry.lvclass:Write to DB.vi` open. The error will be displayed in `error out py` in the latter's front panel.
- Additional debugging tools present for tables in `Main VIs/python_db/upload_data_db.vi`.


