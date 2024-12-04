from .classes import SqlModel, DeletedModel, Attachment, HashedModel, Default
from .errors import tert, vert, tressa
from .interfaces import MigrationProtocol, ModelProtocol
from .migration import Migration, Table
from datetime import datetime
from genericpath import isdir, isfile
from os import listdir, environ
from sys import argv
from types import ModuleType, NoneType, UnionType
from typing import Any, Type, get_args
import importlib.util
import re


def _import(path: str) -> ModuleType:
    """Import a module from a file path."""
    tressa(isfile(path), f"no file at path '{path}'")
    parsed = path.replace('.py', '').replace('/', '.')
    spec = importlib.util.spec_from_file_location(parsed, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def _pascalcase_to_snake_case(name: str) -> str:
    """Simple function to turn PascalCase to snake_case.
        Borrowed from https://stackoverflow.com/a/1176023
    """
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()

def _make_migration_src_start(ctx: tuple = None) -> str:
    src = "from sqloquent import Migration, Table\n"
    if type(ctx) in (tuple, list) and len(ctx) <= 2:
        tert(all([type(c) is str for c in ctx]), 'ctx must be (str,) or (str, str)')
        vert(len(ctx) in (1, 2), 'ctx must be (str,) or (str, str)')
        if len(ctx) == 2:
            src += f"from {ctx[1]} import {ctx[0]}\n"
    return f"{src}\n\n"

def make_migration_create(name: str, connection_string: str = '',
                          ctx: tuple = None) -> str:
    """Generate a migration scaffold from a table name to create a table."""
    src = _make_migration_src_start(ctx)
    table_name = _pascalcase_to_snake_case(name)
    src += f"def create_table_{table_name}() -> list[Table]:\n"
    src += f"    t = Table.create('{table_name}')\n"
    src += f"    t.text('id').unique()\n"
    src += f"    ...\n"
    src += f"    return [t]\n\n"
    src += f"def drop_table_{table_name}() -> list[Table]:\n"
    src += f"    return [Table.drop('{table_name}')]\n\n"
    src += f"def migration(connection_string: str = '{connection_string}') -> Migration:\n"
    if ctx:
        src += f"    migration = Migration(connection_string, {ctx[0]})\n"
    else:
        src += f"    migration = Migration(connection_string)\n"
    src += f"    migration.up(create_table_{table_name})\n"
    src += f"    migration.down(drop_table_{table_name})\n"
    src += f"    return migration"
    return src

def make_migration_alter(name: str, connection_string: str = '',
                         ctx: tuple = None) -> str:
    """Generate a migration scaffold from a table name to alter a table."""
    src = _make_migration_src_start(ctx)
    table_name = _pascalcase_to_snake_case(name)
    src += f"def alter_table_{table_name}() -> list[Table]:\n"
    src += f"    t = Table.alter('{table_name}')\n"
    src += f"    ...\n"
    src += f"    return [t]\n\n"
    src += f"def unalter_table_{table_name}() -> list[Table]:\n"
    src += f"    t = Table.alter('{table_name}')\n"
    src += f"    ...\n"
    src += f"    return [t]\n\n"
    src += f"def migration(connection_string: str = '{connection_string}') -> Migration:\n"
    if ctx:
        src += f"    migration = Migration(connection_string, {ctx[0]})\n"
    else:
        src += f"    migration = Migration(connection_string)\n"
    src += f"    migration.up(alter_table_{table_name})\n"
    src += f"    migration.down(unalter_table_{table_name})\n"
    src += f"    return migration"
    return src

def make_migration_drop(name: str, connection_string: str = '',
                        ctx: tuple = None) -> str:
    """Generate a migration scaffold from a table name to drop a table."""
    src = _make_migration_src_start(ctx)
    table_name = _pascalcase_to_snake_case(name)
    src += f"def drop_table_{table_name}() -> list[Table]:\n"
    src += f"    return [Table.drop('{table_name}')]\n\n"
    src += f"def recreate_table_{table_name}() -> list[Table]:\n"
    src += f"    t = Table.create('{table_name}')\n"
    src += f"    t.text('id').unique()\n"
    src += f"    ...\n"
    src += f"    return [t]\n\n"
    src += f"def migration(connection_string: str = '{connection_string}') -> Migration:\n"
    if ctx:
        src += f"    migration = Migration(connection_string, {ctx[0]})\n"
    else:
        src += f"    migration = Migration(connection_string)\n"
    src += f"    migration.up(drop_table_{table_name})\n"
    src += f"    migration.down(recreate_table_{table_name})\n"
    src += f"    return migration"
    return src

def make_migration_from_model_path(model_name: str, model_path: str,
                              connection_string: str = '',
                              ctx: tuple = None) -> str:
    """Generate a migration from a model name and path."""
    module = _import(model_path)
    tressa(hasattr(module, model_name),
            "module at given path does not have the specified model")
    model: ModelProtocol = getattr(module, model_name)
    tert(isinstance(model(), ModelProtocol),
            "specified model is invalid; must implement ModelProtocol")
    return make_migration_from_model(model, model_name, connection_string, ctx)

def _get_column_type_from_annotation(annotation: Any) -> tuple[str, bool]|tuple[str, bool, Any]:
    nullable = False
    has_default = False
    default = None
    if type(annotation) is UnionType:
        annotation = get_args(annotation)
        default_types = [
            arg
            for arg in annotation
            if getattr(arg, "__origin__", None) is Default
        ]
        if default_types:
            default = get_args(default_types[0])[0]
            has_default = True
        if NoneType in annotation:
            nullable = True
        if bytes in annotation:
            return ('blob', nullable, default) if has_default else ('blob', nullable)
        if int in annotation:
            return ('integer', nullable, default) if has_default else ('integer', nullable)
        if bool in annotation:
            return ('boolean', nullable, default) if has_default else ('boolean', nullable)
        if float in annotation:
            return ('real', nullable, default) if has_default else ('real', nullable)
        return ('text', nullable, default) if has_default else ('text', nullable)
    elif type(annotation) is type:
        if annotation is NoneType:
            nullable = True
        if annotation is bytes:
            return ('blob', nullable, default) if has_default else ('blob', nullable)
        if annotation is int:
            return ('integer', nullable, default) if has_default else ('integer', nullable)
        if annotation is bool:
            return ('boolean', nullable, default) if has_default else ('boolean', nullable)
        if annotation is float:
            return ('real', nullable, default) if has_default else ('real', nullable)
        return ('text', nullable, default) if has_default else ('text', nullable)
    else:
        if 'None' in annotation:
            nullable = True
        if 'Default' in annotation:
            default: str = annotation[annotation.index('Default') + 8:-1]
            if default.lower() == 'none':
                default = None
            elif default.lower() == 'true' and 'bool' in annotation:
                default = True
            elif default.lower() == 'false' and 'bool' in annotation:
                default = False
            elif default.isnumeric() and ('int' in annotation or 'float' in annotation):
                default = int(default)
            has_default = True
        if 'bytes' in annotation:
            return ('blob', nullable, default) if has_default else ('blob', nullable)
        if 'int' in annotation:
            return ('integer', nullable, default) if has_default else ('integer', nullable)
        if 'bool' in annotation:
            return ('boolean', nullable, default) if has_default else ('boolean', nullable)
        if 'float' in annotation:
            return ('real', nullable, default) if has_default else ('real', nullable)
        return ('text', nullable, default) if has_default else ('text', nullable)

def make_migration_from_model(model: ModelProtocol, model_name: str = None,
                               connection_string: str = '', ctx: tuple = None) -> str:
    """Generate a migration from a model."""
    table_name = model.table or _pascalcase_to_snake_case(model_name or model.__name__)
    types: dict[str, tuple[Type, bool]|tuple[str, bool, Any]] = {}
    if model.__annotations__:
        for column in model.columns:
            if column in model.__annotations__:
                annotation = model.__annotations__[column]
                types[column] = _get_column_type_from_annotation(annotation)
    src = _make_migration_src_start(ctx)
    src += f"def create_table_{table_name}() -> list[Table]:\n"
    src += f"    t = Table.create('{table_name}')\n"
    for column in model.columns:
        if column in types:
            src += f"    t.{types[column][0]}('{column}')"
            if len(types[column]) == 3:
                default = types[column][2]
                default = f"'{default}'" if type(default) is str else default
                src += f".default({default})"
            src += ".nullable()" if types[column][1] else ""
        else:
            src += f"    t.text('{column}')"
        src += ".unique()\n" if column == model.id_column else ".index()\n"
    src += "    ...\n"
    src += "    return [t]\n\n"
    src += f"def drop_table_{table_name}() -> list[Table]:\n"
    src += f"    return [Table.drop('{table_name}')]\n\n"
    src += f"def migration(connection_string: str = '{connection_string}') -> Migration:\n"
    if ctx:
        src += f"    migration = Migration(connection_string, {ctx[0]})\n"
    else:
        src += f"    migration = Migration(connection_string)\n"
    src += f"    migration.up(create_table_{table_name})\n"
    src += f"    migration.down(drop_table_{table_name})\n"
    src += f"    return migration"
    return src

def publish_migrations(path: str, connection_string: str = '', ctx: tuple = None):
    """Publish the migrations for the DeletedModel, HashedModel, and Attachment."""
    tert(type(path) is str, 'path must be str')
    tressa(isdir(path), 'path must be valid path to an existing directory')

    deleted_model_src = make_migration_from_model(
        DeletedModel, 'DeletedModel', connection_string, ctx)
    deleted_model_src = deleted_model_src.replace("t.text('record').index()", "t.blob('record')")
    deleted_model_src = deleted_model_src.replace('    ...\n', '')

    attachment_src = make_migration_from_model(
        Attachment, 'Attachment', connection_string, ctx)
    attachment_src = attachment_src.replace("t.text('details').index()", "t.blob('details')")
    attachment_src = attachment_src.replace('    ...\n', '')

    hashed_model_src = make_migration_from_model(
        HashedModel, 'HashedModel', connection_string, ctx)
    hashed_model_src = hashed_model_src.replace("t.text('details').index()", "t.blob('details')")
    hashed_model_src = hashed_model_src.replace('    ...\n', '')

    with open(f"{path}/deleted_model_migration.py", 'w') as f:
        f.write(deleted_model_src)
    with open(f"{path}/attachment_migration.py", 'w') as f:
        f.write(attachment_src)
    with open(f"{path}/hashed_model_migration.py", 'w') as f:
        f.write(hashed_model_src)


def make_model(name: str, base: str = 'SqlModel', columns: dict[str, str] = None,
               connection_string: str = '', sqb: tuple[str,str] = None,
               table: str = None) -> str:
    """Generate a model scaffold with the given name, columns, and
        connection_string. The columns parameter must be a dict mapping
        names to type annotation strings, which should each be one of
        ('str', 'int', 'bool', 'float', 'bytes', 'str|None', 'int|None',
        'bool|None', 'float|None', 'bytes|None') or be one of those with
        '|Default[value]' appended.
    """
    tert(type(name) is str, 'name must be str')
    vert(name.isalnum(), 'name must be alphanumeric')
    vert(base in ('SqlModel', 'HashedModel', 'AsyncSqlModel', 'AsyncHashedModel'),
         "base must be one of (SqlModel, HashedModel, AsyncSqlModel, " +
         f"AsyncHashedModel); {base} encountered")
    tert(columns is None or type(columns) is dict,'columns must be dict[str, str]')
    vert(columns is None or all([type(k) is type(v) is str for k,v in columns.items()]),
         'columns must be dict[str, str]')
    tert(sqb is None or type(sqb) in (tuple, list), "sqb must be (str,) or (str, str)")
    tert(sqb is None or all([type(s) is str for s in sqb]), "sqb must be (str,) or (str, str)")
    vert(sqb is None or 1 <= len(sqb) <= 2, "sqb must be (str,) or (str, str)")
    valid_types = (
        'str', 'int', 'bool', 'float', 'bytes',
        'str|None', 'int|None', 'bool|None', 'float|None', 'bytes|None',
    )
    table_name = table
    if not table_name:
        table_name = _pascalcase_to_snake_case(name)
        if table_name[-1:] == 's':
            table_name = f'{table_name}es'
        elif table_name[-1:] == 'y':
            table_name = f'{table_name[:-1]}ies'
        else:
            table_name = f'{table_name}s'
    src = ""
    src += f"class {name}({base}):\n"
    src += f"    connection_info: str = '{connection_string}'\n"
    if sqb:
        src += f"    query_builder_class: Type[QueryBuilderProtocol] = {sqb[0]}\n"
    src += f"    table: str = '{table_name}'\n"
    src += f"    id_column: str = 'id'\n"
    at_least_one_default = False
    if columns:
        src += f"    columns: tuple[str] = {tuple([name for name in columns])}\n"
        for name, datatype in columns.items():
            default = None
            if 'Default' in datatype:
                default = datatype[datatype.index('Default'):]
                datatype = datatype[:datatype.index('Default')-1]
                at_least_one_default = True
            vert(datatype in valid_types,
                 f'{datatype} is not a valid type annotation; must be one of {valid_types}')
            if default:
                src += f"    {name}: {datatype}|{default}\n"
            else:
                src += f"    {name}: {datatype}\n"
    else:
        src += f"    columns: tuple[str] = ('id',)\n"
    if "Async" in base:
        src_start = f"from sqloquent.asyncql import {base}"
        if at_least_one_default:
            src_start += "\nfrom sqloquent import Default"
    else:
        src_start = f"from sqloquent import {base}"
        if at_least_one_default:
            src_start += ", Default"
    if sqb and len(sqb) == 2:
        src_start += f"\nfrom {sqb[1]} import {sqb[0]}"
    return f"{src_start}\n\n\n{src}\n"


def _import_migration(path: str, connection_string: str = '') -> Migration:
    module = _import(path)
    tressa(hasattr(module, 'migration') and callable(module.migration),
           f"{path} is missing the `migration` function")
    migration = module.migration(connection_string)
    tert(isinstance(migration, MigrationProtocol),
         f"{path} invalid; migration() must return instance implementing MigrationProtocol")
    return migration

def migrate(path: str, connection_string: str = '') -> None:
    """Load and apply the specified migration."""
    migration = _import_migration(path, connection_string)
    migration.apply()
    print("Migrated.")

def rollback(path: str, connection_string: str = '') -> None:
    """Load and rollback the specified migration."""
    migration = _import_migration(path, connection_string)
    migration.undo()
    print("Rolled back.")

def refresh(path: str, connection_string: str = '') -> None:
    """Rollback and apply the specified migration."""
    rollback(path, connection_string)
    migrate(path, connection_string)

def examine(path: str) -> list[str]:
    """Examine the generated SQL from a migration."""
    migration = _import_migration(path)
    return [migration.get_apply_sql(), migration.get_undo_sql()]

def _get_migration_model(connection_string: str = '') -> Type[SqlModel]:
    """Generate a MigrationModel with the given connection_string."""
    class MigrationModel(SqlModel):
        connection_info: str = connection_string
        table: str = 'migrations'
        columns: tuple[str] = ('id', 'batch', 'date')
    return MigrationModel

def _make_migrations_table_migration(connection_string: str = '') -> Migration:
    """Creates and returns a migration for the migrations table."""
    def create_migrations_table() -> list[Table]:
        t = Table.create('migrations')
        t.text('id').unique()
        t.integer('batch')
        t.text('date')
        return [t]

    def drop_migrations_table() -> list[Table]:
        return [Table.drop('migrations')]

    migration = Migration(connection_string)
    migration.up(create_migrations_table)
    migration.down(drop_migrations_table)
    return migration

def automigrate(path: str, connection_string: str = '') -> None:
    """Enumerate the python files at the path, then connect to the db to
        read out the migrations table (creating it if it does not exist),
        then apply the migrations that have not been applied and add a
        record to the migrations table for each.
    """
    tressa(isdir(path), "must provide valid path to directory containing migrations")
    files = [f for f in listdir(path) if isfile(f"{path}/{f}") and f[-3:] == ".py"]
    files.sort()
    m = _import_migration(f"{path}/{files[0]}", connection_string)
    MigrationModel = _get_migration_model(connection_string)
    done: list[SqlModel] = []
    with m.context_manager(connection_string) as cursor:
        q = "select name from sqlite_master where type='table' and name='migrations'"
        if len(cursor.execute(q).fetchall()) == 0:
            _make_migrations_table_migration(connection_string).apply()
        else:
            done = MigrationModel.query().order_by('batch').get()

    batch_id = max([*[d.data['batch'] for d in done], 0]) + 1
    done_ids = [d.data['id'] for d in done]
    to_do = [f for f in files if f not in done_ids and f[:-3] not in done_ids]
    timestamp = str(datetime.today())

    for f in to_do:
        m = _import_migration(f"{path}/{f}", connection_string)
        m.apply()
        MigrationModel.insert({"id": f, "batch": batch_id, "date": timestamp})
        print(f"Applied migration {f}")

def autorollback(path: str, connection_string: str = '', all: bool = False) -> None:
    """Enumerate the python files at the path, then connect to the db to
        read out the migrations table (creating it if it does not exist),
        then rollback the previous batch of migrations that were applied
        and remove the records from the migrations table for each.
    """
    tressa(isdir(path), "must provide valid path to directory containing migrations")
    files = [f for f in listdir(path) if isfile(f"{path}/{f}") and f[-3:] == ".py"]
    files.sort()
    m = _import_migration(f"{path}/{files[0]}", connection_string)
    MigrationModel = _get_migration_model(connection_string)
    done: list[SqlModel] = []
    with m.context_manager(connection_string) as cursor:
        q = "select name from sqlite_master where type='table' and name='migrations'"
        if len(cursor.execute(q).fetchall()) == 0:
            _make_migrations_table_migration(m.connection_info).apply()
            print("Migration table was missing but has been created.")
            print("Cannot automatically rollback unrecorded migrations.")
            return
        else:
            done = MigrationModel.query().order_by('batch').get()
            if len(done) == 0:
                print("No migrations to rollback.")
                return
    migrations: list[ModelProtocol] = []
    if not all:
        batch_id = max([d.data['batch'] for d in done])
        migrations = MigrationModel.query({"batch":batch_id}).get()
        print(f"Rolling back batch {batch_id}...")
    else:
        migrations = MigrationModel.query().get()

    migrations.sort(key=lambda mm: (mm.data['batch'], mm.data['id']), reverse=True)
    for mm in migrations:
        f = mm.data['id']
        m = _import_migration(f"{path}/{f}", connection_string)
        m.undo()
        mm.delete()
        print(f"Rolled back {f}.")

def autorefresh(path: str, connection_string: str = '') -> None:
    """Rollback all migrations then apply all migrations in the folder
        at path.
    """
    autorollback(path, connection_string=connection_string, all=True)
    automigrate(path, connection_string=connection_string)


def help_cli(name: str) -> str:
    """Return the help string for the CLI tool."""
    name = name.split("/")[-1]
    """Produce and return the help text."""
    return f"""usage: {name} make migration --create name [--ctx name [--from package_name]]
    {name} make migration --alter name [--ctx name [--from package_name]]
    {name} make migration --drop name [--ctx name [--from package_name]]
    {name} make migration --model name path/to/model/file [--ctx name [--from package_name]]
    {name} make model name [--hashed] [--columns name1=type|None|Default[value],name2,etc] [--async] [--sqb name [--from package_name]] [--table table_name]
    {name} migrate path/to/migration/file
    {name} rollback path/to/migration/file
    {name} refresh path/to/migration/file
    {name} examine path/to/migration/file
    {name} automigrate path/to/migrations/folder
    {name} autorollback path/to/migrations/folder
    {name} autorefresh path/to/migrations/folder
    {name} publish path/to/migrations/folder [--ctx name [--from package_name]]\n\n""" + \
    "The `make` commands print the string source to std out for piping as\n" + \
    "desired. The `automigrate` command reads the files in the specified\n" + \
    "directory, then runs the managed migration tool which tracks migrations\n" + \
    "using a migrations table.\n\n" + \
    "The data types for the --columns param are (str, int, float, bytes).\n\n" + \
    "The `publish` command publishes migrations for the included DeletedModel,\n" +\
    "HashedModel, and Attachment classes. Use of these is optional.\n\n" + \
    "Include CONNECTION_STRING in a .env file or as an environment variable\n" + \
    "to set the connection string used by migration commands. Include\n" + \
    "MAKE_WITH_CONNSTRING in a .env file or as an environment variable to\n" + \
    "use the connection string with make commands."


def run_cli() -> None:
    """Run the CLI tool."""
    if len(argv) < 3:
        print(help_cli(argv[0]))
        return

    connection_string = environ.get('CONNECTION_STRING')
    use_connstring_for_make = environ.get('MAKE_WITH_CONNSTRING') is not None
    if not connection_string and isfile('.env'):
        with open('.env', 'r') as f:
            lines = f.readlines()
            for l in lines:
                if l[:18] == 'CONNECTION_STRING=':
                    connection_string = l[18:-1]
                elif l[:20] == 'MAKE_WITH_CONNSTRING':
                    use_connstring_for_make = l[20:-1].lower() not in ('false', '0')
    connection_string = connection_string or 'temp.db'
    connstring_for_make = connection_string if use_connstring_for_make else ''
    table = None

    mode = argv[1]
    if mode == "make":
        kind = argv[2]
        if kind == "migration":
            if len(argv) < 5:
                print("error: make migration missing parameters")
                print(help_cli(argv[0]))
                exit(1)
            param = argv[3]
            name = argv[4]
            ctx = None
            if "--ctx" in argv:
                argi = argv.index("--ctx")
                if len(argv) < argi + 2:
                    print(help_cli(argv[0]))
                    exit(1)
                ctx = [argv[argi + 1]]
                if "--from" in argv:
                    argi = argv.index("--from")
                    if len(argv) < argi + 2:
                        print(help_cli(argv[0]))
                        exit(1)
                    ctx.append(argv[argi + 1])
            if param == "--create":
                return print(make_migration_create(name, connstring_for_make, ctx))
            elif param == "--alter":
                return print(make_migration_alter(name, connstring_for_make, ctx))
            elif param == "--drop":
                return print(make_migration_drop(name, connstring_for_make, ctx))
            elif param == "--model":
                if len(argv) < 6:
                    print(f"error: `make migration --model {name}` missing path parameter")
                    print(help_cli(argv[0]))
                    exit(1)
                return print(make_migration_from_model_path(name, argv[5], connstring_for_make, ctx))
        elif kind == "model":
            if len(argv) < 4:
                print("make model missing parameter: name")
                print(help_cli(argv[0]))
                exit(1)
            name = argv[3]
            columns = {}
            base = "SqlModel"
            sqb = None
            if '--columns' in argv:
                colindex = argv.index('--columns')
                if len(argv) >= colindex + 2:
                    columns_str = argv[colindex+1]
                    columns_list = columns_str.split(',')
                    for s in columns_list:
                        if len(s.split('=')) > 1:
                            colname, datatype = s.split('=')
                            columns[colname] = datatype
                        else:
                            columns[s] = 'str'
            if "--hashed" in argv:
                base = 'HashedModel'
            if "--async" in argv:
                base = f"Async{base}"
            if "--sqb" in argv:
                argi = argv.index("--sqb")
                if len(argv) < argi + 2:
                    print(help_cli(argv[0]))
                    exit(1)
                sqb = [argv[argi + 1]]
                if "--from" in argv:
                    argi = argv.index("--from")
                    if len(argv) < argi + 2:
                        print(help_cli(argv[0]))
                        exit(1)
                    sqb.append(argv[argi + 1])
            if "--table" in argv:
                argi = argv.index("--table")
                if len(argv) < argi + 2:
                    print(help_cli(argv[0]))
                    exit(1)
                table = argv[argi + 1]

            return print(make_model(name, base, connection_string=connstring_for_make,
                                    columns=columns, sqb=sqb, table=table))
        else:
            print(f"unrecognized make kind: {kind}")
            exit(1)
    elif mode == "migrate":
        path = argv[2]
        migrate(path, connection_string)
    elif mode == "rollback":
        path = argv[2]
        rollback(path, connection_string)
    elif mode == "refresh":
        path = argv[2]
        refresh(path, connection_string)
    elif mode == "examine":
        path = argv[2]
        apply, undo = examine(path)
        print("/**** generated up/apply sql ****/\n" + apply)
        print("\n/**** generated down/undo sql ****/\n" + undo)
    elif mode == "automigrate":
        path = argv[2]
        automigrate(path, connection_string)
    elif mode == "autorollback":
        path = argv[2]
        autorollback(path, connection_string)
    elif mode == "autorefresh":
        path = argv[2]
        autorefresh(path, connection_string)
    elif mode == "publish":
        if len(argv) < 3:
            print("missing path")
            exit(1)
        ctx = None
        if "--ctx" in argv:
            argi = argv.index("--ctx")
            if len(argv) < argi + 2:
                print(help_cli(argv[0]))
                exit(1)
            ctx = [argv[argi + 1]]
            if "--from" in argv:
                argi = argv.index("--from")
                if len(argv) < argi + 2:
                    print(help_cli(argv[0]))
                    exit(1)
                ctx.append(argv[argi + 1])
        return publish_migrations(argv[2], connstring_for_make, ctx)
    else:
        print(f"unrecognized mode: {mode}")
        exit(1)


if __name__ == "__main__":
    run_cli()
