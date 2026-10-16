import hashlib
import re
from psycopg.rows import dict_row
from .migrations import MIGRATIONS,MIGRATION_NAMESPACE
from psycopg.types.json import Jsonb
class Conflict(Exception):pass

def identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r'[a-z][a-z0-9_.-]{0,63}',value):raise ValueError('Invalid identifier')
    return value

def subject(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_:@.-]{1,128}',value):raise ValueError('Invalid subject')
    return value

class FlagStore:
    def __init__(self,database):self.db=database
    def put(self,workspace,name,enabled,rollout,subjects,version):
        identifier(name)
        if type(enabled) is not bool or type(rollout) is not int or not 0<=rollout<=10000:raise ValueError('Invalid flag')
        if not isinstance(subjects,list) or len(subjects)>100:raise ValueError('Invalid subjects')
        subjects=sorted(set(subject(x) for x in subjects))
        if version is not None and (type(version) is not int or version<1):raise Conflict()
        with self.db.transaction(workspace) as conn, conn.cursor(row_factory=dict_row) as c:
            if version is None:
                row=c.execute('INSERT INTO feature_flags(workspace_id,name,enabled,rollout,subjects) VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING name,enabled,rollout,subjects,version',(workspace,name,enabled,rollout,Jsonb(subjects))).fetchone()
            else:
                row=c.execute('UPDATE feature_flags SET enabled=%s,rollout=%s,subjects=%s,version=version+1 WHERE name=%s AND version=%s RETURNING name,enabled,rollout,subjects,version',(enabled,rollout,Jsonb(subjects),name,version)).fetchone()
            if row is None:raise Conflict()
            return row
    def get(self,workspace,name):
        identifier(name)
        with self.db.transaction(workspace) as conn, conn.cursor(row_factory=dict_row) as c:
            return c.execute('SELECT name,enabled,rollout,subjects,version FROM feature_flags WHERE name=%s',(name,)).fetchone()
    def list(self,workspace,limit=100,after=''):
        if not 1<=limit<=100:raise ValueError('Invalid limit')
        with self.db.transaction(workspace) as conn, conn.cursor(row_factory=dict_row) as c:
            return c.execute('SELECT name,enabled,rollout,subjects,version FROM feature_flags WHERE name>%s ORDER BY name LIMIT %s',(after,limit)).fetchall()
    def delete(self,workspace,name,version):
        identifier(name)
        with self.db.transaction(workspace) as c:
            if not c.execute('DELETE FROM feature_flags WHERE name=%s AND version=%s RETURNING name',(name,version)).fetchone():raise Conflict()
    def evaluate(self,workspace,name,value):
        subject(value);row=self.get(workspace,name)
        if not row or not row['enabled']:return False
        bucket=int.from_bytes(hashlib.sha256(f'{workspace}:{name}:{value}'.encode()).digest()[:8],'big')%10000
        return value in row['subjects'] or bucket<row['rollout']
    def ready(self):
        with self.db.transaction(__import__('uuid').UUID(int=0)) as c:
            # Check every operation individually: a comma privilege list means ANY.
            required_permissions=c.execute("""SELECT has_schema_privilege(current_user,'public','USAGE')
                AND has_table_privilege(current_user,'public.platform_schema_migrations','SELECT')
                AND has_table_privilege(current_user,'public.feature_flags','SELECT')
                AND has_table_privilege(current_user,'public.feature_flags','INSERT')
                AND has_table_privilege(current_user,'public.feature_flags','UPDATE')
                AND has_table_privilege(current_user,'public.feature_flags','DELETE')""").fetchone()[0]
            if not required_permissions:return False
            history=c.execute('SELECT version,checksum FROM platform_schema_migrations WHERE namespace=%s ORDER BY version',(MIGRATION_NAMESPACE,)).fetchall()
            if history!=[(m.version,m.checksum) for m in MIGRATIONS]:return False
            row=c.execute("SELECT relrowsecurity AND relforcerowsecurity FROM pg_class WHERE oid=to_regclass('feature_flags')").fetchone()
            c.execute('SELECT name,version FROM feature_flags LIMIT 0')
            return bool(row and row[0])
