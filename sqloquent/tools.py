from .errors import tert, vert, tressa
from .interfaces import ModelProtocol
from sys import argv
import re


def _pascalcase_to_snake_case(name: str) -> str:
    """Simple function to turn PascalCase to snake_case.
        Borrowed from https://stackoverflow.com/a/1176023
    """
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()

def _make_migration_src_start() -> str:
    return "from sqloquent import Migration, Table\n\n\n" + \
        "CONNECTION_STRING = 'temp.db'\n\n\n"

def make_migration_create(name: str) -> str:
    """Generate a migration scaffold from a table name to create a table."""
    src = _make_migration_src_start()
    table_name = _pascalcase_to_snake_case(name)
    src += f"def create_table_{table_name}() -> list[Table]:\n"
    src += f"    t = Table.create('{table_name}')\n"
    src += f"    t.text('id').unique()\n"
    src += f"    ...\n"
    src += f"    return [t]\n\n"
    src += f"def drop_table_{table_name}() -> list[Table]:\n"
    src += f"    return [Table.drop('{table_name}')]\n\n\n"
    src += "migration = Migration(CONNECTION_STRING)\n"
    src += f"migration.up(create_table_{table_name})\n"
    src += f"migration.down(drop_table_{table_name})\n"
    return src

def make_migration_alter(name: str) -> str:
    """Generate a migration scaffold from a table name to alter a table."""
    src = _make_migration_src_start()
    table_name = _pascalcase_to_snake_case(name)
    src += f"def alter_table_{table_name}() -> list[Table]:\n"
    src += f"    t = Table.alter('{table_name}')\n"
    src += f"    ...\n"
    src += f"    return [t]\n\n"
    src += f"def unalter_table_{table_name}() -> list[Table]:\n"
    src += f"    t = Table.alter('{table_name}')\n"
    src += f"    ...\n"
    src += f"    return [t]\n\n\n"
    src += "migration = Migration(CONNECTION_STRING)\n"
    src += f"migration.up(alter_table_{table_name})\n"
    src += f"migration.down(unalter_table_{table_name})\n"
    return src

def make_migration_drop(name: str) -> str:
    """Generate a migration scaffold from a table name to drop a table."""
    src = _make_migration_src_start()
    table_name = _pascalcase_to_snake_case(name)
    src += f"def drop_table_{table_name}() -> list[Table]:\n"
    src += f"    return [Table.drop('{table_name}')]\n\n"
    src += f"def recreate_table_{table_name}() -> list[Table]:\n"
    src += f"    t = Table.create('{table_name}')\n"
    src += f"    t.text('id').unique()\n"
    src += f"    ...\n"
    src += f"    return [t]\n\n\n"
    src += "migration = Migration(CONNECTION_STRING)\n"
    src += f"migration.up(drop_table_{table_name})\n"
    src += f"migration.down(recreate_table_{table_name})\n"
    return src

def make_migration_from_model(model_name: str, model_path: str) -> str:
    """Generate a migration scaffold from a model."""
    model_path = model_path.replace("/", ".")
    model_path = model_path[:-3] if model_path[-3:] == ".py" else model_path
    module = __import__(model_path)
    tressa(hasattr(module, model_name),
            "module at given path does not have the specified model")
    model: ModelProtocol = getattr(module, model_name)
    tert(isinstance(model(), ModelProtocol),
            "specified model is invalid; must implement ModelProtocol")

    table_name = _pascalcase_to_snake_case(model_name)
    src = _make_migration_src_start()
    src += f"def create_table_{table_name}() -> list[Table]:\n"
    src += f"    t = Table.create('{table_name}')\n"
    for field in model.fields:
        src += f"    t.text('{field}')"
        src += ".unique()\n" if field == model.id_field else ".index()\n"
    src += "    ...\n"
    src += "    return [t]\n\n"

    src += f"def drop_table_{table_name}() -> list[Table]:\n"
    src += f"    return [Table.drop('{table_name}')]\n\n\n"

    src += "migration = Migration(CONNECTION_STRING)\n"
    src += f"migration.up(create_table_{table_name})\n"
    src += f"migration.down(drop_table_{table_name})\n"

    return src


def help_cli(name: str) -> str:
    name = name.split("/")[-1]
    """Produce and return the help text."""
    return f"""usage: {name} make migration --create name
    {name} make migration --alter name
    {name} make migration --drop name
    {name} make migration --model name path/to/model/file
    {name} make model name [--sqlite|--sql] (inherits SqliteModel by default)
    {name} migrate path/to/migration/file
    {name} rollback path/to/migration/file
    {name} refresh path/to/migration/file
    {name} automigrate path/to/migrations/folder
    {name} autorollback path/to/migrations/folder
    {name} autorefresh path/to/migrations/folder\n\n""" + \
    "The `make` commands print the string source to std out for piping as\n" + \
    "desired. The `automigrate` command reads the files in the specified\n" + \
    "directory, then runs the managed migration tool which tracks migrations\n" + \
    "using a migrations table."


def run_cli() -> None:
    if len(argv) < 3:
        print(help_cli(argv[0]))
        return

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
            if param == "--create":
                return print(make_migration_create(name))
            elif param == "--alter":
                return print(make_migration_alter(name))
            elif param == "--drop":
                return print(make_migration_drop(name))
            elif param == "--model":
                if len(argv) < 6:
                    print(f"error: `make migration --model {name}` missing path parameter")
                    print(help_cli(argv[0]))
                    exit(1)
                return print(make_migration_from_model(name, argv[5]))
        elif kind == "model":
            ...
        else:
            print(f"unrecognized make kind: {kind}")
            exit(1)
    elif mode == "migrate":
        path = argv[2]
        ...
    elif mode == "rollback":
        path = argv[2]
        ...
    elif mode == "automigrate":
        path = argv[2]
        ...
    else:
        print(f"unrecognized mode: {mode}")
        exit(1)


if __name__ == "__main__":
    run_cli()
