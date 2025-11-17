from asyncio import run
from secrets import token_bytes
from context import async_classes, errors, async_interfaces, interfaces
from genericpath import isfile
from hashlib import sha256
from types import AsyncGeneratorType
import aiosqlite
import os
import packify
import unittest


DB_FILEPATH = 'test.db'


class ExampleModel(async_classes.AsyncSqlModel):
    connection_info = DB_FILEPATH
    table = 'example_models'
    columns = (
        'id', 'field1', 'field2', 'field3', 'field4', 'field5',
        'field1n', 'field2n', 'field3n', 'field4n', 'field5n',
        'field1d', 'field2d', 'field3d', 'field4d', 'field5d',
        'field1nd', 'field2nd', 'field3nd', 'field4nd', 'field5nd'
    )
    field1: str
    field2: int
    field3: bool
    field4: bytes
    field5: float
    field1n: str|None
    field2n: int|None
    field3n: bool|None
    field4n: bytes|None
    field5n: float|None
    field1d: str|async_classes.Default['foobar']
    field2d: int|async_classes.Default[123]
    field3d: bool|async_classes.Default[True]
    field4d: bytes|async_classes.Default[b'123']
    field5d: float|async_classes.Default[1.23]
    field1nd: str|None|async_classes.Default['foobar']
    field2nd: int|None|async_classes.Default[123]
    field3nd: bool|None|async_classes.Default[True]
    field4nd: bytes|None|async_classes.Default[b'123']
    field5nd: float|None|async_classes.Default[1.23]

class ExampleHashedModel(async_classes.AsyncHashedModel):
    connection_info = DB_FILEPATH
    table = 'example_hashed_models'
    columns = (
        'id', 'field1', 'field2', 'field3', 'field4', 'field5',
        'field1n', 'field2n', 'field3n', 'field4n', 'field5n',
        'field1d', 'field2d', 'field3d', 'field4d', 'field5d',
        'field1nd', 'field2nd', 'field3nd', 'field4nd', 'field5nd'
    )
    field1: str
    field2: int
    field3: bool
    field4: bytes
    field5: float
    field1n: str|None
    field2n: int|None
    field3n: bool|None
    field4n: bytes|None
    field5n: float|None
    field1d: str|async_classes.Default['foobar']
    field2d: int|async_classes.Default[123]
    field3d: bool|async_classes.Default[True]
    field4d: bytes|async_classes.Default[b'123']
    field5d: float|async_classes.Default[1.23]
    field1nd: str|None|async_classes.Default['foobar']
    field2nd: int|None|async_classes.Default[123]
    field3nd: bool|None|async_classes.Default[True]
    field4nd: bytes|None|async_classes.Default[b'123']
    field5nd: float|None|async_classes.Default[1.23]


async def connect(path):
    return await aiosqlite.connect(path)


class TestAsyncClasses(unittest.TestCase):
    db: aiosqlite.Connection = None
    cursor: aiosqlite.Cursor = None

    def setUp(self) -> None:
        """Set up the test database."""
        try:
            if isfile(DB_FILEPATH):
                os.remove(DB_FILEPATH)
        except:
            ...
        self.db = run(connect(DB_FILEPATH))
        self.cursor = run(self.db.cursor())
        run(self.cursor.execute('create table deleted_records (id text not null, ' +
            'model_class text not null, record_id text not null, ' +
            'record blob not null, timestamp text not null)'))
        run(self.cursor.execute('create table example (id text, name text)'))
        run(self.cursor.execute('create table hashed_records (id text, details text)'))
        run(self.cursor.execute('create table hashed_subclass (id text, column1 text, column2 text)'))
        run(self.cursor.execute('create table attachments (id text, ' +
            'related_model text, related_id text, details blob)'))
        run(self.cursor.execute('create table example_models (id text, ' +
            'field1 text, field2 integer, field3 boolean, field4 blob, ' +
            'field5 real, field1n text nullable, field2n integer nullable, ' +
            'field3n boolean nullable, field4n blob nullable, field5n real nullable, ' +
            "field1d text default 'foobar', field2d integer default 123, " +
            "field3d boolean default true, field4d blob default (x'313233'), " +
            'field5d real default 1.23, field1nd text nullable default ''foobar'', ' +
            'field2nd integer nullable default 123, field3nd boolean nullable default true, ' +
            "field4nd blob nullable default (x'313233'), field5nd real nullable default 1.23)"))
        run(self.cursor.execute('create table example_hashed_models (id text, ' +
            'field1 text, field2 integer, field3 boolean, field4 blob, ' +
            'field5 real, field1n text nullable, field2n integer nullable, ' +
            'field3n boolean nullable, field4n blob nullable, field5n real nullable, ' +
            'field1d text default ''foobar'', field2d integer default 123, ' +
            'field3d boolean default true, field4d blob default X''313233'', ' +
            'field5d real default 1.23, field1nd text nullable default ''foobar'', ' +
            'field2nd integer nullable default 123, field3nd boolean nullable default true, ' +
            'field4nd blob nullable default X''313233'', field5nd real nullable default 1.23)'))

        return super().setUp()

    def setUpClass() -> None:
        """Couple these models to db_filepath for testing purposes."""
        async_classes.AsyncSqlModel.connection_info = DB_FILEPATH
        async_classes.AsyncDeletedModel.connection_info = DB_FILEPATH
        async_classes.AsyncHashedModel.connection_info = DB_FILEPATH
        async_classes.AsyncAttachment.connection_info = DB_FILEPATH

    def tearDown(self) -> None:
        """Close cursor and delete test database."""
        async_classes.AsyncSqlModel.clear_hooks()
        async_classes.AsyncHashedModel.clear_hooks()
        async_classes.AsyncDeletedModel.clear_hooks()
        async_classes.AsyncAttachment.clear_hooks()
        q = "select name from sqlite_master where type='table'"
        run(self.cursor.execute(q))
        results = run(self.cursor.fetchall())
        for result in results:
            q = f"drop table if exists {result[0]};"
            try:
                run(self.cursor.execute(q))
            except BaseException as e:
                print(e)
        run(self.cursor.close())
        run(self.db.close())
        try:
            os.remove(DB_FILEPATH)
        except:
            ...
        return super().tearDown()

    # general tests
    def test_classes_contains_correct_classes_and_functions(self):
        assert hasattr(async_classes, 'AsyncSqliteContext')
        assert type(async_classes.AsyncSqliteContext) is type
        assert hasattr(async_classes, 'AsyncSqlModel')
        assert type(async_classes.AsyncSqlModel) is type
        assert hasattr(async_classes, 'async_dynamic_sqlmodel')
        assert callable(async_classes.async_dynamic_sqlmodel)
        assert hasattr(async_classes, 'AsyncSqlQueryBuilder')
        assert type(async_classes.AsyncSqlQueryBuilder) is type
        assert hasattr(async_classes, 'AsyncDeletedModel')
        assert type(async_classes.AsyncDeletedModel) is type
        assert hasattr(async_classes, 'AsyncHashedModel')
        assert type(async_classes.AsyncHashedModel) is type
        assert hasattr(async_classes, 'AsyncAttachment')
        assert type(async_classes.AsyncAttachment) is type


    # context manager tests
    def test_AsyncSqliteContext_implements_DBContextProtocol(self):
        assert issubclass(async_classes.AsyncSqliteContext, async_interfaces.AsyncDBContextProtocol)

    def test_AsyncSqliteContext_raises_errors_for_invalid_use(self):
        with self.assertRaises(TypeError) as e:
            with async_classes.AsyncSqliteContext({}):
                ...

        with self.assertRaises(TypeError) as e:
            with async_classes.AsyncSqliteContext(str):
                ...

        with self.assertRaises(TypeError) as e:
            with async_classes.AsyncSqliteContext([]):
                ...
        assert 'connection_info' in str(e.exception), str(e.exception)
        assert 'must be str' in str(e.exception)


    # AsyncSqlModel tests
    def test_AsyncSqlModel_implements_AsyncModelProtocol(self):
        assert isinstance(async_classes.AsyncSqlModel(), async_interfaces.AsyncModelProtocol)

    def test_AsyncSqlModel_columns_are_set_as_properties(self):
        model = async_classes.AsyncSqlModel({'id': '123', 'name': 'Bob'})
        assert hasattr(model, 'id') and model.id == '123'
        assert hasattr(model, 'name') and model.name == 'Bob'
        model.name = 'Alice'
        assert model.data['name'] == 'Alice'

    def test_AsyncSqlModel_column_property_mapping_disabled_for_colliding_names(self):
        class Derived(async_classes.AsyncSqlModel):
            columns: tuple[str] = ('id', 'name', 'save', 'data')
        model = Derived({'id': '123', 'name': 'Bob', 'save': 'to-do', 'data': '321'})
        assert hasattr(model, 'save') and callable(model.save)
        assert 'save' in model.data and model.data['save'] == 'to-do'
        assert 'data' in model.data and model.data['data'] == '321'

    def test_AsyncSqlModel_post_init_hooks_are_called(self):
        class TestModel(async_classes.AsyncSqlModel):
            ...

        signals = {}
        def test1(_):
            signals['test1'] = 1

        TestModel._post_init_hooks = {
            'test1': test1
        }
        _ = TestModel()

        assert 'test1' in signals

    def test_AsyncSqlModel_init_raises_errors_for_invalid_post_init_hooks(self):
        class TestModel(async_classes.AsyncSqlModel):
            ...

        TestModel._post_init_hooks = []
        with self.assertRaises(TypeError) as e:
            _ = TestModel()
        assert str(e.exception) == '_post_init_hooks must be a dict mapping names to Callables'

        TestModel._post_init_hooks = {'name': 'not callable'}
        with self.assertRaises(ValueError) as e:
            _ = TestModel()
        assert str(e.exception) == '_post_init_hooks must be a dict mapping names to Callables'

    def test_AsyncSqlModel_encode_value_raises_packify_UsageError_for_unrecognized_type(self):
        with self.assertRaises(packify.UsageError) as e:
            async_classes.AsyncSqlModel.encode_value(async_classes.AsyncSqlModel)

    def test_AsyncSqlModel_encode_value_encodes_values_properly(self):
        bstr = b'123'
        assert async_classes.AsyncSqlModel.encode_value(bstr) == packify.pack(bstr).hex()

        list_of_bytes = [b'123', b'321']
        expected = packify.pack(list_of_bytes).hex()
        assert async_classes.AsyncSqlModel.encode_value(list_of_bytes) == expected

        tuple_of_bytes = (b'123', b'321')
        expected = packify.pack(tuple_of_bytes).hex()
        assert async_classes.AsyncSqlModel.encode_value(tuple_of_bytes) == expected

        unencoded_dict = {b'123': b'321', 1: '123'}
        expected = packify.pack(unencoded_dict).hex()
        assert async_classes.AsyncSqlModel.encode_value(unencoded_dict) == expected

    def test_AsyncSqlModel_insert_raises_TypeError_for_nondict_input(self):
        with self.assertRaises(TypeError) as e:
            run(async_classes.AsyncSqlModel.insert('not a dict'))
        assert str(e.exception) == 'data must be dict'

    def test_AsyncSqlModel_insert_many_raises_TypeError_for_nonlist_of_dict_input(self):
        with self.assertRaises(TypeError) as e:
            run(async_classes.AsyncSqlModel.insert_many('not a list'))
        assert str(e.exception) == 'items must be type list[dict]'

        with self.assertRaises(TypeError) as e:
            run(async_classes.AsyncSqlModel.insert_many(['not a dict']))
        assert str(e.exception) == 'items must be type list[dict]'

    def test_AsyncSqlModel_update_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            run(async_classes.AsyncSqlModel().update('not a dict'))
        assert str(e.exception) == 'updates must be dict'

        with self.assertRaises(TypeError) as e:
            run(async_classes.AsyncSqlModel().update({}, 'not a dict'))
        assert str(e.exception) == 'conditions must be dict or None'

        with self.assertRaises(ValueError) as e:
            run(async_classes.AsyncSqlModel().update({}))
        assert str(e.exception) == f'instance must have id or conditions defined'

    def test_AsyncSqlModel_insert_and_find(self):
        # e2e test
        inserted = run(async_classes.AsyncSqlModel.insert({'name': 'test1'}))
        assert isinstance(inserted, async_classes.AsyncSqlModel), \
            'insert() must return AsyncSqlModel instance'
        assert async_classes.AsyncSqlModel.id_column in inserted.data, \
            'insert() return value must have id'

        found = run(async_classes.AsyncSqlModel.find(
            inserted.data[async_classes.AsyncSqlModel.id_column]
        ))
        assert isinstance(found, async_classes.AsyncSqlModel), \
            'find() must return AsyncSqlModel instance'

        assert inserted == found, \
            'inserted must equal found'

    def test_AsyncSqlModel_update_save_and_delete(self):
        # e2e test
        inserted = run(async_classes.AsyncSqlModel.insert({'name': 'test1'}))
        updated = run(inserted.update({'name': 'test2'}))
        assert isinstance(updated, async_classes.AsyncSqlModel), \
            'update() must return AsyncSqlModel instance'
        assert updated.data['name'] == 'test2', 'value must be updated'
        assert updated == inserted, 'must be equal'
        found = run(async_classes.AsyncSqlModel.find(inserted.data[inserted.id_column]))
        assert updated == found, 'must be equal'

        updated.data['name'] = 'test3'
        saved = run(updated.save())
        assert isinstance(saved, async_classes.AsyncSqlModel), \
            'save() must return AsyncSqlModel instance'
        assert saved == updated, 'must be equal'
        found = run(async_classes.AsyncSqlModel.find(inserted.data[inserted.id_column]))
        assert saved == found, 'must be equal'

        run(updated.delete())
        found = run(async_classes.AsyncSqlModel.find(inserted.data[inserted.id_column]))
        assert found is None, 'found must be None'

    def test_AsyncSqlModel_insert_many_and_count(self):
        # e2e test
        inserted = run(async_classes.AsyncSqlModel.insert_many([
            {'name': 'test1'},
            {'name': 'test2'},
        ]))
        assert type(inserted) is int, 'insert_many() must return int'
        assert inserted == 2, 'insert_many() should return 2'

        found = run(async_classes.AsyncSqlModel.query().count())
        assert found == 2

    def test_AsyncSqlModel_reload_reads_values_from_db(self):
        model = run(async_classes.AsyncSqlModel.insert({'name': 'Tarzan'}))
        run(model.query({'id':model.data['id']}).update({'name': 'Jane'}))
        assert model.data['name'] == 'Tarzan'
        run(model.reload())
        assert model.data['name'] == 'Jane'

    def test_AsyncSqlModel_add_hook_remove_hook_and_invoke_hooks(self):
        log = []
        def addlog(*args, **kwargs):
            log.append((args, kwargs))
        async_classes.AsyncSqlModel.add_hook('test', addlog)
        assert len(log) == 0
        run(async_classes.AsyncSqlModel.invoke_hooks('test', 1, 2, three=3))
        assert len(log) == 1, log
        assert log[0][0] == (async_classes.AsyncSqlModel, 1, 2), log
        assert log[0][1] == {'event': 'test', 'three': 3}, log
        async_classes.AsyncSqlModel.remove_hook('test', addlog)
        log.pop()
        run(async_classes.AsyncSqlModel.invoke_hooks('test', 'abc', foo='bar'))
        assert len(log) == 0, log

    def test_AsyncSqlModel_hooks_fire_on_relevant_methods(self):
        log = []
        def addlog(*args, **kwargs):
            log.append((args, kwargs))
        # insert
        assert len(log) == 0
        run(async_classes.AsyncSqlModel.insert({'name': 'foobar'}))
        assert len(log) == 0, log
        async_classes.AsyncSqlModel.add_hook('before_insert', addlog)
        async_classes.AsyncSqlModel.add_hook('after_insert', addlog)
        run(async_classes.AsyncSqlModel.insert({'name': 'foobar'}))
        assert len(log) == 2, log
        run(async_classes.AsyncSqlModel.insert({'name': 'foobar'}, suppress_events = True))
        assert len(log) == 2, log
        log.clear()
        async_classes.AsyncSqlModel.remove_hook('before_insert', addlog)
        async_classes.AsyncSqlModel.remove_hook('after_insert', addlog)

        # insert_many
        run(async_classes.AsyncSqlModel.insert_many([{'name': 'foobar'}]))
        assert len(log) == 0, log
        async_classes.AsyncSqlModel.add_hook('before_insert_many', addlog)
        async_classes.AsyncSqlModel.add_hook('after_insert_many', addlog)
        run(async_classes.AsyncSqlModel.insert_many([{'name': 'foobar'}]))
        assert len(log) == 2, log
        run(async_classes.AsyncSqlModel.insert_many([{'name': 'foobar'}], suppress_events = True))
        assert len(log) == 2, log
        log.clear()
        async_classes.AsyncSqlModel.remove_hook('before_insert_many', addlog)
        async_classes.AsyncSqlModel.remove_hook('after_insert_many', addlog)

        # update
        item = run(async_classes.AsyncSqlModel.query().first())
        run(item.update({'name': 'foodbar'}))
        assert len(log) == 0, log
        async_classes.AsyncSqlModel.add_hook('before_update', addlog)
        async_classes.AsyncSqlModel.add_hook('after_update', addlog)
        run(item.update({'name': 'foobar'}))
        assert len(log) == 2, log
        run(item.update({'name': 'foobar'}, suppress_events = True))
        assert len(log) == 2, log
        log.clear()
        async_classes.AsyncSqlModel.remove_hook('before_update', addlog)
        async_classes.AsyncSqlModel.remove_hook('after_update', addlog)

        # delete
        item = run(async_classes.AsyncSqlModel.query().first())
        run(item.delete())
        assert len(log) == 0, log
        item = run(async_classes.AsyncSqlModel.query().first())
        async_classes.AsyncSqlModel.add_hook('before_delete', addlog)
        async_classes.AsyncSqlModel.add_hook('after_delete', addlog)
        run(item.delete())
        assert len(log) == 2, log
        run(item.delete(suppress_events = True))
        assert len(log) == 2, log
        log.clear()
        async_classes.AsyncSqlModel.remove_hook('before_delete', addlog)
        async_classes.AsyncSqlModel.remove_hook('after_delete', addlog)

        # reload
        item = run(async_classes.AsyncSqlModel.query().first())
        run(item.reload())
        assert len(log) == 0, log
        item = run(async_classes.AsyncSqlModel.query().first())
        async_classes.AsyncSqlModel.add_hook('before_reload', addlog)
        async_classes.AsyncSqlModel.add_hook('after_reload', addlog)
        run(item.reload())
        assert len(log) == 2, log
        run(item.reload(suppress_events = True))
        assert len(log) == 2, log
        log.clear()
        async_classes.AsyncSqlModel.remove_hook('before_reload', addlog)
        async_classes.AsyncSqlModel.remove_hook('after_reload', addlog)

    def test_AsyncSqlModel_tracks_changes_properly(self):
        sm = run(async_classes.AsyncSqlModel.insert({'name': 'test'}))
        assert sm.data_original['name'] == sm.data['name'] == 'test'
        sm.name = 'Test'
        assert sm.data_original['name'] == 'test'
        assert sm.data['name'] == 'Test'
        run(sm.save())
        assert sm.data_original['name'] == sm.name == 'Test'

    # async_dynamic_sqlmodel test
    def test_async_dynamic_sqlmodel_returns_type_ModelProtocol(self):
        filepath = "some/path/to/file.db"
        tablename = "some_table"
        columns = ('id', 'name', 'etc')
        modelclass = async_classes.async_dynamic_sqlmodel(filepath, tablename, columns)
        assert type(modelclass) is type
        assert issubclass(modelclass, async_classes.AsyncSqlModel)
        model = modelclass()
        assert isinstance(model, async_interfaces.AsyncModelProtocol)
        assert hasattr(model, "connection_info") and model.connection_info == filepath
        assert hasattr(model, "table") and model.table == tablename
        assert hasattr(model, "columns") and model.columns == columns

        modelclass = async_classes.async_dynamic_sqlmodel("some/path/to/file.db")
        assert type(modelclass) is type
        assert issubclass(modelclass, async_classes.AsyncSqlModel)
        model = modelclass()
        assert isinstance(model, async_interfaces.AsyncModelProtocol)
        assert hasattr(model, "connection_info") and model.connection_info == filepath
        assert model.table == ""
        assert model.columns == ()


    # AsyncSqlQueryBuilder tests
    def test_AsyncSqlQueryBuilder_implements_QueryBuilderProtocol(self):
        assert isinstance(async_classes.AsyncSqlQueryBuilder, async_interfaces.AsyncQueryBuilderProtocol)

    def test_AsyncSqlQueryBuilder_rejects_invalid_model(self):
        with self.assertRaises(TypeError) as e:
            sqb = async_classes.AsyncSqlQueryBuilder(model=dict)

        with self.assertRaises(TypeError) as e:
            sqb = async_classes.AsyncSqlQueryBuilder(model='ssds')

    def test_AsyncSqlQueryBuilder_is_null_raises_TypeError_for_nonstr_column(self):
        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).is_null(b'not a str', '')

    def test_AsyncSqlQueryBuilder_is_null_adds_correct_clause(self):
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.is_null('name')
        assert len(sqb.clauses) == 1, 'equal() must append to clauses'
        assert len(sqb.params) == 0, 'equal() must not append to params'
        assert sqb.clauses[0] == '"name" is null'

        sqb = sqb.reset()
        assert len(sqb.clauses) == 0, len(sqb.clauses)
        sqb.is_null(['etc', 'thing'])
        assert len(sqb.clauses) == 2, len(sqb.clauses)
        assert len(sqb.params) == 0, len(sqb.params)
        assert sqb.clauses[0] == '"etc" is null'
        assert sqb.clauses[1] == '"thing" is null'

    def test_AsyncSqlQueryBuilder_not_null_raises_TypeError_for_nonstr_column(self):
        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).not_null(b'not a str', '')

    def test_AsyncSqlQueryBuilder_not_null_adds_correct_clause(self):
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.not_null('name')
        assert len(sqb.clauses) == 1, 'equal() must append to clauses'
        assert len(sqb.params) == 0, 'equal() must not append to params'
        assert sqb.clauses[0] == '"name" is not null'

        sqb = sqb.reset()
        assert len(sqb.clauses) == 0, len(sqb.clauses)
        sqb.not_null(['etc', 'thing'])
        assert len(sqb.clauses) == 2, len(sqb.clauses)
        assert len(sqb.params) == 0, len(sqb.params)
        assert sqb.clauses[0] == '"etc" is not null'
        assert sqb.clauses[1] == '"thing" is not null'

    def test_AsyncSqlQueryBuilder_equal_raises_TypeError_for_nonstr_column(self):
        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).equal(b'not a str', '')

    def test_AsyncSqlQueryBuilder_equal_adds_correct_clause_and_param(self):
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.equal('name', 'test')
        assert len(sqb.clauses) == 1, 'equal() must append to clauses'
        assert len(sqb.params) == 1, 'equal() must append to params'
        assert sqb.clauses[0] == '"name" = ?'
        assert sqb.params[0] == 'test'

        sqb = sqb.reset()
        assert len(sqb.clauses) == 0, len(sqb.clauses)
        sqb.equal(name='test', etc='test2')
        assert len(sqb.clauses) == 2, len(sqb.clauses)
        assert len(sqb.params) == 2, len(sqb.params)
        assert sqb.clauses[0] == '"name" = ?'
        assert sqb.clauses[1] == '"etc" = ?'
        assert sqb.params[0] == 'test'
        assert sqb.params[1] == 'test2'

    def test_AsyncSqlQueryBuilder_not_equal_raises_TypeError_for_nonstr_column(self):
        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).not_equal(b'not a str', '')
        assert str(e.exception) == 'column must be str'

    def test_AsyncSqlQueryBuilder_not_equal_adds_correct_clause_and_param(self):
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.not_equal('name', 'test')
        assert len(sqb.clauses) == 1, 'not_equal() must append to clauses'
        assert len(sqb.params) == 1, 'not_equal() must append to params'
        assert sqb.clauses[0] == '"name" != ?'
        assert sqb.params[0] == 'test'

        sqb = sqb.reset()
        assert len(sqb.clauses) == 0, len(sqb.clauses)
        sqb.not_equal(name='test', etc='test2')
        assert len(sqb.clauses) == 2, len(sqb.clauses)
        assert len(sqb.params) == 2, len(sqb.params)
        assert sqb.clauses[0] == '"name" != ?'
        assert sqb.clauses[1] == '"etc" != ?'
        assert sqb.params[0] == 'test'
        assert sqb.params[1] == 'test2'

    def test_AsyncSqlQueryBuilder_less_raises_TypeError_for_nonstr_column(self):
        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).less(b'not a str', '')
        assert str(e.exception) == 'column must be str'

    def test_AsyncSqlQueryBuilder_less_adds_correct_clause_and_param(self):
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.less('name', '123')
        assert len(sqb.clauses) == 1, 'less() must append to clauses'
        assert len(sqb.params) == 1, 'less() must append to params'
        assert sqb.clauses[0] == '"name" < ?'
        assert sqb.params[0] == '123'

        sqb = sqb.reset()
        assert len(sqb.clauses) == 0, len(sqb.clauses)
        sqb.less(name='123', etc='456')
        assert len(sqb.clauses) == 2, len(sqb.clauses)
        assert len(sqb.params) == 2, len(sqb.params)
        assert sqb.clauses[0] == '"name" < ?'
        assert sqb.clauses[1] == '"etc" < ?'
        assert sqb.params[0] == '123'
        assert sqb.params[1] == '456'

    def test_AsyncSqlQueryBuilder_less_or_equal_raises_TypeError_for_nonstr_column(self):
        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).less_or_equal(b'not a str', '')
        assert str(e.exception) == 'column must be str'

    def test_AsyncSqlQueryBuilder_less_or_equal_adds_correct_clause_and_param(self):
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.less_or_equal('name', '123')
        assert len(sqb.clauses) == 1, 'less_or_equal() must append to clauses'
        assert len(sqb.params) == 1, 'less_or_equal() must append to params'
        assert sqb.clauses[0] == '"name" <= ?'
        assert sqb.params[0] == '123'

        sqb = sqb.reset()
        assert len(sqb.clauses) == 0, len(sqb.clauses)
        sqb.less_or_equal(name='123', etc='456')
        assert len(sqb.clauses) == 2, len(sqb.clauses)
        assert len(sqb.params) == 2, len(sqb.params)
        assert sqb.clauses[0] == '"name" <= ?'
        assert sqb.clauses[1] == '"etc" <= ?'
        assert sqb.params[0] == '123'
        assert sqb.params[1] == '456'

    def test_AsyncSqlQueryBuilder_greater_raises_TypeError_for_nonstr_column(self):
        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).greater(b'not a str', '')
        assert str(e.exception) == 'column must be str'

    def test_AsyncSqlQueryBuilder_greater_adds_correct_clause_and_param(self):
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.greater('name', '123')
        assert len(sqb.clauses) == 1, 'greater() must append to clauses'
        assert len(sqb.params) == 1, 'greater() must append to params'
        assert sqb.clauses[0] == '"name" > ?'
        assert sqb.params[0] == '123'

        sqb = sqb.reset()
        assert len(sqb.clauses) == 0, len(sqb.clauses)
        sqb.greater(name='123', etc='456')
        assert len(sqb.clauses) == 2, len(sqb.clauses)
        assert len(sqb.params) == 2, len(sqb.params)
        assert sqb.clauses[0] == '"name" > ?'
        assert sqb.clauses[1] == '"etc" > ?'
        assert sqb.params[0] == '123'
        assert sqb.params[1] == '456'

    def test_AsyncSqlQueryBuilder_greater_or_equal_raises_TypeError_for_nonstr_column(self):
        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).greater_or_equal(b'not a str', '')
        assert str(e.exception) == 'column must be str'

    def test_AsyncSqlQueryBuilder_greater_or_equal_adds_correct_clause_and_param(self):
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.greater_or_equal('name', '123')
        assert len(sqb.clauses) == 1, 'greater_or_equal() must append to clauses'
        assert len(sqb.params) == 1, 'greater_or_equal() must append to params'
        assert sqb.clauses[0] == '"name" >= ?'
        assert sqb.params[0] == '123'

        sqb = sqb.reset()
        assert len(sqb.clauses) == 0, len(sqb.clauses)
        sqb.greater_or_equal(name='123', etc='456')
        assert len(sqb.clauses) == 2, len(sqb.clauses)
        assert len(sqb.params) == 2, len(sqb.params)
        assert sqb.clauses[0] == '"name" >= ?'
        assert sqb.clauses[1] == '"etc" >= ?'
        assert sqb.params[0] == '123'
        assert sqb.params[1] == '456'

    def test_AsyncSqlQueryBuilder_like_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).like(b'not a str', '', '')
        assert str(e.exception) == 'column must be str'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).like('', b'not a str', '')
        assert str(e.exception) == 'pattern must be str'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).like('', '', b'not a str')
        assert str(e.exception) == 'data must be str'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).like('', 'sds', '')
        assert str(e.exception) == 'column cannot be empty'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).like('sds', '', '')
        assert str(e.exception) == 'pattern cannot be empty'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).like('sds', '%?', '')
        assert str(e.exception) == 'data cannot be empty'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel).like(name='thing')
        assert str(e.exception) == 'each value must be tuple or list with 2 elements: pattern, data'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel).like(name=('thing',))
        assert str(e.exception) == 'each value must be tuple or list with 2 elements: pattern, data'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel).like(name=(b'not a str', 'test'))
        assert 'pattern must be str' in str(e.exception), str(e.exception)

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel).like(name=('thing', b'not a str'))
        assert 'data must be str' in str(e.exception), str(e.exception)

    def test_AsyncSqlQueryBuilder_like_adds_correct_clause_and_param(self):
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.like('name', '?%', '123')
        assert len(sqb.clauses) == 1, 'like() must append to clauses'
        assert len(sqb.params) == 1, 'like() must append to params'
        assert sqb.clauses[0] == '"name" like ?'
        assert sqb.params[0] == '123%'

        sqb = sqb.reset()
        assert len(sqb.clauses) == 0, len(sqb.clauses)
        sqb.like(name=('?%?', '123'), other=('?%?', '456'))
        assert len(sqb.clauses) == 2, sqb.clauses
        assert len(sqb.params) == 2, sqb.params
        assert sqb.clauses[0] == '"name" like ?', sqb.clauses
        assert sqb.params[0] == '123%123', sqb.params
        assert sqb.clauses[1] == '"other" like ?', sqb.clauses
        assert sqb.params[1] == '456%456', sqb.params

    def test_AsyncSqlQueryBuilder_not_like_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).not_like(b'not a str', '', '')
        assert str(e.exception) == 'column must be str'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).not_like('', b'not a str', '')
        assert str(e.exception) == 'pattern must be str'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).not_like('', '', b'not a str')
        assert str(e.exception) == 'data must be str'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).not_like('', 'sds', '')
        assert str(e.exception) == 'column cannot be empty'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).not_like('sds', '', '')
        assert str(e.exception) == 'pattern cannot be empty'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).not_like('sds', '%?', '')
        assert str(e.exception) == 'data cannot be empty'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).not_like(name='thing')
        assert str(e.exception) == 'each value must be tuple or list with 2 elements: pattern, data'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).not_like(name=('thing',))
        assert str(e.exception) == 'each value must be tuple or list with 2 elements: pattern, data'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).not_like(name=(b'not a str', 'test'))
        assert str(e.exception) == 'each pattern must be str'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).not_like(name=('thing', b'not a str'))
        assert str(e.exception) == 'each data must be str'

    def test_AsyncSqlQueryBuilder_not_like_adds_correct_clause_and_param(self):
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.not_like('name', '?%', '123')
        assert len(sqb.clauses) == 1, 'not_like() must append to clauses'
        assert len(sqb.params) == 1, 'not_like() must append to params'
        assert sqb.clauses[0] == '"name" not like ?'
        assert sqb.params[0] == '123%'

        sqb = sqb.reset()
        assert len(sqb.clauses) == 0, len(sqb.clauses)
        sqb.not_like(name=('?%?', '123'), other=('?%?', '456'))
        assert len(sqb.clauses) == 2, sqb.clauses
        assert len(sqb.params) == 2, sqb.params
        assert sqb.clauses[0] == '"name" not like ?', sqb.clauses
        assert sqb.params[0] == '123%123', sqb.params
        assert sqb.clauses[1] == '"other" not like ?', sqb.clauses
        assert sqb.params[1] == '456%456', sqb.params

    def test_AsyncSqlQueryBuilder_starts_with_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).starts_with(b'not a str', '')
        assert str(e.exception) == 'column must be str'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).starts_with('', b'not a str')
        assert str(e.exception) == 'data must be str'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).starts_with('', 'sds')
        assert str(e.exception) == 'column cannot be empty'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).starts_with('sds', '')
        assert str(e.exception) == 'data cannot be empty'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).starts_with(name=b'not a str')
        assert str(e.exception) == 'data must be str'

    def test_AsyncSqlQueryBuilder_starts_with_adds_correct_clause_and_param(self):
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.starts_with('name', '123')
        assert len(sqb.clauses) == 1, 'starts_with() must append to clauses'
        assert len(sqb.params) == 1, 'starts_with() must append to params'
        assert sqb.clauses[0] == '"name" like ?'
        assert sqb.params[0] == '123%'

        sqb = sqb.reset()
        assert len(sqb.clauses) == 0, len(sqb.clauses)
        sqb.starts_with(name='123', other='misc')
        assert len(sqb.clauses) == 2, sqb.clauses
        assert len(sqb.params) == 2, sqb.params
        assert sqb.clauses[0] == '"name" like ?', sqb.clauses
        assert sqb.params[0] == '123%', sqb.params
        assert sqb.clauses[1] == '"other" like ?', sqb.clauses
        assert sqb.params[1] == 'misc%', sqb.params

    def test_AsyncSqlQueryBuilder_does_not_start_with_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).does_not_start_with(b'not a str', '')
        assert str(e.exception) == 'column must be str'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).does_not_start_with('', b'not a str')
        assert str(e.exception) == 'data must be str'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).does_not_start_with('', 'sds')
        assert str(e.exception) == 'column cannot be empty'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).does_not_start_with('sds', '')
        assert str(e.exception) == 'data cannot be empty'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).does_not_start_with(name=b'not a str')
        assert str(e.exception) == 'data must be str'

    def test_AsyncSqlQueryBuilder_does_not_start_with_adds_correct_clause_and_param(self):
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.does_not_start_with('name', '123')
        assert len(sqb.clauses) == 1, 'does_not_start_with() must append to clauses'
        assert len(sqb.params) == 1, 'does_not_start_with() must append to params'
        assert sqb.clauses[0] == '"name" not like ?'
        assert sqb.params[0] == '123%'

        sqb = sqb.reset()
        assert len(sqb.clauses) == 0, len(sqb.clauses)
        sqb.does_not_start_with(name='123', other='misc')
        assert len(sqb.clauses) == 2, sqb.clauses
        assert len(sqb.params) == 2, sqb.params
        assert sqb.clauses[0] == '"name" not like ?', sqb.clauses
        assert sqb.params[0] == '123%', sqb.params
        assert sqb.clauses[1] == '"other" not like ?', sqb.clauses
        assert sqb.params[1] == 'misc%', sqb.params

    def test_AsyncSqlQueryBuilder_contains_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).contains(b'not a str', '')
        assert str(e.exception) == 'column must be str'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).contains('', b'not a str')
        assert str(e.exception) == 'data must be str'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).contains('', 'sds')
        assert str(e.exception) == 'column cannot be empty'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).contains('sds', '')
        assert str(e.exception) == 'data cannot be empty'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).contains(name=b'not a str')
        assert str(e.exception) == 'data must be str'

    def test_AsyncSqlQueryBuilder_contains_adds_correct_clause_and_param(self):
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.contains('name', '123')
        assert len(sqb.clauses) == 1, 'contains() must append to clauses'
        assert len(sqb.params) == 1, 'contains() must append to params'
        assert sqb.clauses[0] == '"name" like ?'
        assert sqb.params[0] == '%123%'

        sqb = sqb.reset()
        assert len(sqb.clauses) == 0, len(sqb.clauses)
        sqb.contains(name='123', other='misc')
        assert len(sqb.clauses) == 2, sqb.clauses
        assert len(sqb.params) == 2, sqb.params
        assert sqb.clauses[0] == '"name" like ?', sqb.clauses
        assert sqb.params[0] == '%123%', sqb.params
        assert sqb.clauses[1] == '"other" like ?', sqb.clauses
        assert sqb.params[1] == '%misc%', sqb.params

    def test_AsyncSqlQueryBuilder_excludes_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).excludes(b'not a str', '')
        assert str(e.exception) == 'column must be str'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).excludes('', b'not a str')
        assert str(e.exception) == 'data must be str'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).excludes('', 'sds')
        assert str(e.exception) == 'column cannot be empty'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).excludes('sds', '')
        assert str(e.exception) == 'data cannot be empty'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).excludes(name=b'not a str')
        assert str(e.exception) == 'data must be str'

    def test_AsyncSqlQueryBuilder_excludes_adds_correct_clause_and_param(self):
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.excludes('name', '123')
        assert len(sqb.clauses) == 1, 'excludes() must append to clauses'
        assert len(sqb.params) == 1, 'excludes() must append to params'
        assert sqb.clauses[0] == '"name" not like ?'
        assert sqb.params[0] == '%123%'

        sqb = sqb.reset()
        assert len(sqb.clauses) == 0, len(sqb.clauses)
        sqb.excludes(name='123', other='misc')
        assert len(sqb.clauses) == 2, sqb.clauses
        assert len(sqb.params) == 2, sqb.params
        assert sqb.clauses[0] == '"name" not like ?', sqb.clauses
        assert sqb.params[0] == '%123%', sqb.params
        assert sqb.clauses[1] == '"other" not like ?', sqb.clauses
        assert sqb.params[1] == '%misc%', sqb.params

    def test_AsyncSqlQueryBuilder_ends_with_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).ends_with(b'not a str', '')
        assert str(e.exception) == 'column must be str'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).ends_with('', b'not a str')
        assert str(e.exception) == 'data must be str'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).ends_with('', 'sds')
        assert str(e.exception) == 'column cannot be empty'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).ends_with('sds', '')
        assert str(e.exception) == 'data cannot be empty'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).ends_with(name=b'not a str')
        assert str(e.exception) == 'data must be str'

    def test_AsyncSqlQueryBuilder_ends_with_adds_correct_clause_and_param(self):
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.ends_with('name', '123')
        assert len(sqb.clauses) == 1, 'ends_with() must append to clauses'
        assert len(sqb.params) == 1, 'ends_with() must append to params'
        assert sqb.clauses[0] == '"name" like ?'
        assert sqb.params[0] == '%123'

        sqb = sqb.reset()
        assert len(sqb.clauses) == 0, len(sqb.clauses)
        sqb.ends_with(name='123', other='misc')
        assert len(sqb.clauses) == 2, sqb.clauses
        assert len(sqb.params) == 2, sqb.params
        assert sqb.clauses[0] == '"name" like ?', sqb.clauses
        assert sqb.params[0] == '%123', sqb.params
        assert sqb.clauses[1] == '"other" like ?', sqb.clauses
        assert sqb.params[1] == '%misc', sqb.params

    def test_AsyncSqlQueryBuilder_does_not_end_with_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).does_not_end_with(b'not a str', '')
        assert str(e.exception) == 'column must be str'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).does_not_end_with('', b'not a str')
        assert str(e.exception) == 'data must be str'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).does_not_end_with('', 'sds')
        assert str(e.exception) == 'column cannot be empty'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).does_not_end_with('sds', '')
        assert str(e.exception) == 'data cannot be empty'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).does_not_end_with(name=b'not a str')
        assert str(e.exception) == 'data must be str'

    def test_AsyncSqlQueryBuilder_does_not_end_with_adds_correct_clause_and_param(self):
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.does_not_end_with('name', '123')
        assert len(sqb.clauses) == 1, 'does_not_end_with() must append to clauses'
        assert len(sqb.params) == 1, 'does_not_end_with() must append to params'
        assert sqb.clauses[0] == '"name" not like ?'
        assert sqb.params[0] == '%123'

        sqb = sqb.reset()
        assert len(sqb.clauses) == 0, len(sqb.clauses)
        sqb.does_not_end_with(name='123', other='misc')
        assert len(sqb.clauses) == 2, sqb.clauses
        assert len(sqb.params) == 2, sqb.params
        assert sqb.clauses[0] == '"name" not like ?', sqb.clauses
        assert sqb.params[0] == '%123', sqb.params
        assert sqb.clauses[1] == '"other" not like ?', sqb.clauses
        assert sqb.params[1] == '%misc', sqb.params

    def test_AsyncSqlQueryBuilder_is_in_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).is_in(b'not a str', 'not list')
        assert str(e.exception) == 'column must be str'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).is_in('', 'not a list')
        assert str(e.exception) == 'data must be tuple or list'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).is_in('', ['sds'])
        assert str(e.exception) == 'column cannot be empty'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).is_in('sds', [])
        assert str(e.exception) == 'data cannot be empty'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).is_in(name='not a list')
        assert 'data must be tuple or list' in str(e.exception), str(e.exception)

    def test_AsyncSqlQueryBuilder_is_in_adds_correct_clause_and_param(self):
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.is_in('name', ('123', '321'))
        assert len(sqb.clauses) == 1, 'is_in() must append to clauses'
        assert len(sqb.params) == 2, 'is_in() must extend params'
        assert sqb.clauses[0] == '"name" in (?,?)'
        assert sqb.params[0] == '123'
        assert sqb.params[1] == '321'

        sqb = sqb.reset()
        assert len(sqb.clauses) == 0, len(sqb.clauses)
        sqb.is_in(name=('123', '321'), other=('456', '654'))
        assert len(sqb.clauses) == 2, sqb.clauses
        assert len(sqb.params) == 4, sqb.params
        assert sqb.clauses[0] == '"name" in (?,?)', sqb.clauses
        assert sqb.params[0] == '123', sqb.params
        assert sqb.params[1] == '321', sqb.params
        assert sqb.clauses[1] == '"other" in (?,?)', sqb.clauses
        assert sqb.params[2] == '456', sqb.params
        assert sqb.params[3] == '654', sqb.params

    def test_AsyncSqlQueryBuilder_not_in_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).not_in(b'not a str', 'not list')
        assert str(e.exception) == 'column must be str'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).not_in('', 'not a list')
        assert str(e.exception) == 'data must be tuple or list'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).not_in('', ['sds'])
        assert str(e.exception) == 'column cannot be empty'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).not_in('sds', [])
        assert str(e.exception) == 'data cannot be empty'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).not_in(name='not a list')
        assert 'data must be tuple or list' in str(e.exception), str(e.exception)

    def test_AsyncSqlQueryBuilder_not_in_adds_correct_clause_and_param(self):
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.not_in('name', ('123', '321'))
        assert len(sqb.clauses) == 1, 'not_in() must append to clauses'
        assert len(sqb.params) == 2, 'not_in() must extend params'
        assert sqb.clauses[0] == '"name" not in (?,?)'
        assert sqb.params[0] == '123'
        assert sqb.params[1] == '321'

        sqb = sqb.reset()
        assert len(sqb.clauses) == 0, len(sqb.clauses)
        sqb.not_in(name=('123', '321'), other=('456', '654'))
        assert len(sqb.clauses) == 2, sqb.clauses
        assert len(sqb.params) == 4, sqb.params
        assert sqb.clauses[0] == '"name" not in (?,?)', sqb.clauses
        assert sqb.params[0] == '123', sqb.params
        assert sqb.params[1] == '321', sqb.params
        assert sqb.clauses[1] == '"other" not in (?,?)', sqb.clauses
        assert sqb.params[2] == '456', sqb.params
        assert sqb.params[3] == '654', sqb.params

    def test_SqlQueryBuilder_where_raises_errors_for_invalid_input(self):
        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).where(not_a_condition='should not work')
        assert 'unrecognized condition type' in str(e.exception)

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel
            ).where(equal=b'not a dict')
        assert 'must be dict' in str(e.exception)

    def test_SqlQueryBuilder_where_adds_correct_clauses_and_params(self):
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        sqb.where(
            is_null=['other'],
            not_null=['name'],
            equal={'id': 123},
            not_equal={'name': 'foo'},
            less={'age': 18},
            less_or_equal={'age': 17},
            greater={'age': 30},
            greater_or_equal={'age': 31},
            like={'name': ('?%', 'foo')},
            not_like={'name': ('?%', 'foo'), 'other': ('?%', 'misc')},
            starts_with={'name': 'foo'},
            does_not_start_with={'name': 'foo'},
            contains={'name': 'foo'},
            excludes={'name': 'foo'},
            ends_with={'name': 'foo'},
            does_not_end_with={'name': 'foo'},
            is_in={'name': ('123', '321')},
            not_in={'name': ('123', '321')},
        )
        assert len(sqb.clauses) == 19, sqb.clauses
        assert len(sqb.params) == 19, sqb.params

        # helpers for indexing properly
        _cidx, _pidx = 0, 0
        def cidx(inc: int = 1) -> int:
            nonlocal _cidx
            _cidx += inc
            return _cidx
        def pidx(inc: int = 1) -> int:
            nonlocal _pidx
            _pidx += inc
            return _pidx

        # is_null
        assert sqb.clauses[cidx(0)] == '"other" is null', sqb.clauses[cidx(0)]

        # not_null
        assert sqb.clauses[cidx()] == '"name" is not null', sqb.clauses[cidx(0)]

        # equal
        assert sqb.clauses[cidx()] == '"id" = ?', sqb.clauses[cidx(0)]
        assert sqb.params[pidx(0)] == 123, sqb.params[pidx(0)]

        # not_equal
        assert sqb.clauses[cidx()] == '"name" != ?', sqb.clauses[cidx(0)]
        assert sqb.params[pidx()] == 'foo', sqb.params[pidx(0)]

        # less
        assert sqb.clauses[cidx()] == '"age" < ?', sqb.clauses[cidx(0)]
        assert sqb.params[pidx()] == 18, sqb.params[pidx(0)]

        # less_or_equal
        assert sqb.clauses[cidx()] == '"age" <= ?', sqb.clauses[cidx(0)]
        assert sqb.params[pidx()] == 17, sqb.params[pidx(0)]

        # greater
        assert sqb.clauses[cidx()] == '"age" > ?', sqb.clauses[cidx(0)]
        assert sqb.params[pidx()] == 30, sqb.params[pidx(0)]

        # greater_or_equal
        assert sqb.clauses[cidx()] == '"age" >= ?', sqb.clauses[cidx(0)]
        assert sqb.params[pidx()] == 31, sqb.params[pidx(0)]

        # like
        assert sqb.clauses[cidx()] == '"name" like ?', sqb.clauses[cidx(0)]
        assert sqb.params[pidx()] == 'foo%', sqb.params[pidx(0)]

        # not_like
        assert sqb.clauses[cidx()] == '"name" not like ?', sqb.clauses[cidx(0)]
        assert sqb.params[pidx()] == 'foo%', sqb.params[pidx(0)]
        assert sqb.clauses[cidx()] == '"other" not like ?', sqb.clauses[cidx(0)]
        assert sqb.params[pidx()] == 'misc%', sqb.params[pidx(0)]

        # starts_with
        assert sqb.clauses[cidx()] == '"name" like ?', sqb.clauses[cidx(0)]
        assert sqb.params[pidx()] == 'foo%', sqb.params[pidx(0)]

        # does_not_start_with
        assert sqb.clauses[cidx()] == '"name" not like ?', sqb.clauses[cidx(0)]
        assert sqb.params[pidx()] == 'foo%', sqb.params[pidx(0)]

        # contains
        assert sqb.clauses[cidx()] == '"name" like ?', sqb.clauses[cidx(0)]
        assert sqb.params[pidx()] == '%foo%', sqb.params[pidx(0)]

        # excludes
        assert sqb.clauses[cidx()] == '"name" not like ?', sqb.clauses[cidx(0)]
        assert sqb.params[pidx()] == '%foo%', sqb.params[pidx(0)]

        # ends_with
        assert sqb.clauses[cidx()] == '"name" like ?', sqb.clauses[cidx(0)]
        assert sqb.params[pidx()] == '%foo', sqb.params[pidx(0)]

        # does_not_end_with
        assert sqb.clauses[cidx()] == '"name" not like ?', sqb.clauses[cidx(0)]
        assert sqb.params[pidx()] == '%foo', sqb.params[pidx(0)]

        # is_in
        assert sqb.clauses[cidx()] == '"name" in (?,?)', sqb.clauses[cidx(0)]
        assert sqb.params[pidx()] == '123', sqb.params[pidx(0)]
        assert sqb.params[pidx()] == '321', sqb.params[pidx(0)]

        # not_in
        assert sqb.clauses[cidx()] == '"name" not in (?,?)', sqb.clauses[cidx(0)]
        assert sqb.params[pidx()] == '123', sqb.params[pidx(0)]
        assert sqb.params[pidx()] == '321', sqb.params[pidx(0)]

    def test_AsyncSqlQueryBuilder_order_by_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).order_by(b'not a str', 'asc')
        assert str(e.exception) == 'column must be str'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).order_by('', b'not a str')
        assert str(e.exception) == 'direction must be str'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).order_by('', '')
        assert 'unrecognized column' in str(e.exception)

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).order_by('id', 'not asc or desc')
        assert str(e.exception) == 'direction must be asc or desc'

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).order_by(name=b'not a str')
        assert str(e.exception) == 'direction must be str'

    def test_AsyncSqlQueryBuilder_order_by_sets_order_column_and_order_dir(self):
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        assert sqb.order_column is None, 'order_column must initialize as None'
        assert sqb.order_dir == 'desc', 'order_dir must initialize as desc'
        sqb.order_by('name', 'asc')
        assert sqb.order_column == '"name"', 'order_column must become name'
        assert sqb.order_dir == 'asc', 'order_dir must become asc'

    def test_AsyncSqlQueryBuilder_skip_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).skip('not an int')
        assert str(e.exception) == 'offset must be positive int'

        with self.assertRaises(ValueError) as e:
            async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).skip(-1)
        assert str(e.exception) == 'offset must be positive int'

    def test_AsyncSqlQueryBuilder_skip_sets_offset(self):
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        assert sqb.offset is None, 'offset must initialize as None'
        assert sqb.skip(5).offset == 5, 'offset must become 5'

    def test_AsyncSqlQueryBuilder_insert_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            run(async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).insert('not a dict'))
        assert str(e.exception) == 'data must be dict'

        model_id = run(async_classes.AsyncSqlModel.insert({})).data['id']

        with self.assertRaises(ValueError) as e:
            run(async_classes.AsyncSqlQueryBuilder(
                async_classes.AsyncSqlModel,
                async_classes.AsyncSqliteContext
            ).insert({'id': model_id}))
        assert str(e.exception) == 'record with this id already exists'

    def test_AsyncSqlQueryBuilder_insert_inserts_record_into_database(self):
        sqb = async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel, async_classes.AsyncSqliteContext)
        model_id = '32123'
        run(sqb.insert({'id': model_id, 'name': 'test'}))

        assert run(sqb.find(model_id))

    def test_AsyncSqlQueryBuilder_insert_many_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            run(async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).insert_many('not a list'))
        assert str(e.exception) == 'items must be list[dict]'

        with self.assertRaises(TypeError) as e:
            run(async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).insert_many(['not a dict']))
        assert str(e.exception) == 'items must be list[dict]'

    def test_AsyncSqlQueryBuilder_take_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            run(async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).take('not an int'))
        assert str(e.exception) == 'limit must be positive int'

        with self.assertRaises(ValueError) as e:
            run(async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).take(0))
        assert str(e.exception) == 'limit must be positive int'

    def test_AsyncSqlQueryBuilder_chunk_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            sqb = async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel, async_classes.AsyncSqliteContext)
            run(sqb.chunk('not an int'))
        assert str(e.exception) == 'number must be int > 0'

        with self.assertRaises(ValueError) as e:
            run(async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).chunk(0))
        assert str(e.exception) == 'number must be int > 0'

    def test_AsyncSqlQueryBuilder_update_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            run(async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).update('not a dict'))
        assert str(e.exception) == 'updates must be dict'

        with self.assertRaises(TypeError) as e:
            run(async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).update({}, 'not a dict'))
        assert str(e.exception) == 'conditions must be dict'

    def test_AsyncSqlQueryBuilder_to_sql_returns_correct_sql_str(self):
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        assert type(sqb.to_sql()) is str, 'to_sql() must return str'
        assert sqb.to_sql() == ' where ', sqb.to_sql()

        sqb.equal('name', 'foo')
        assert sqb.to_sql() == ' where "name" = \'foo\'', sqb.to_sql()

        sqb.order_by('id')
        assert sqb.to_sql() == ' where "name" = \'foo\' order by "id" desc', sqb.to_sql()

        sqb.skip(3)
        assert sqb.to_sql() == ' where "name" = \'foo\' order by "id" desc', sqb.to_sql()

        sqb.offset = None
        sqb.limit = 5
        assert sqb.to_sql() == ' where "name" = \'foo\' order by "id" desc limit 5', sqb.to_sql()

        sqb.skip(3)
        assert sqb.to_sql() == ' where "name" = \'foo\' order by "id" desc limit 5 offset 3', sqb.to_sql()

    def test_AsyncSqlQueryBuilder_to_sql_without_interpolate_params_returns_str_and_list(self):
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        assert type(sqb.to_sql(interpolate_params=False)) is tuple, \
            'to_sql(interpolate_params=False) must return tuple(str, list)'
        assert len(sqb.to_sql(interpolate_params=False)) == 2, \
            'to_sql(interpolate_params=False) must return tuple(str, list)'
        assert type(sqb.to_sql(interpolate_params=False)[0]) is str, \
            'to_sql(interpolate_params=False) must return tuple(str, list)'
        assert type(sqb.to_sql(interpolate_params=False)[1]) is list, \
            'to_sql(interpolate_params=False) must return tuple(str, list)'
        assert sqb.to_sql(interpolate_params=False)[0] == ' where '

        sqb.equal('name', 'foo')
        assert sqb.to_sql(interpolate_params=False)[0] == ' where "name" = ?'
        assert sqb.to_sql(interpolate_params=False)[1] == ['foo']

        sqb.order_by('id')
        assert sqb.to_sql(interpolate_params=False)[0] == ' where "name" = ? order by "id" desc', \
            sqb.to_sql(interpolate_params=False)[0]
        assert sqb.to_sql(interpolate_params=False)[1] == ['foo']

        sqb.skip(3)
        assert sqb.to_sql(interpolate_params=False)[0] == ' where "name" = ? order by "id" desc'
        assert sqb.to_sql(interpolate_params=False)[1] == ['foo']

        sqb.offset = None
        sqb.limit = 5
        assert sqb.to_sql(interpolate_params=False)[0] == ' where "name" = ? order by "id" desc limit 5'
        assert sqb.to_sql(interpolate_params=False)[1] == ['foo']

        sqb.skip(3)
        assert sqb.to_sql(interpolate_params=False)[0] == ' where "name" = ? order by "id" desc limit 5 offset 3'
        assert sqb.to_sql(interpolate_params=False)[1] == ['foo']

    def test_AsyncSqlQueryBuilder_reset_returns_fresh_instance(self):
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        sql1 = sqb.to_sql()
        sql2 = sqb.equal('name', 'thing').to_sql()
        assert sql1 != sql2
        assert sqb.reset().to_sql() == sql1

    def test_AsyncSqlQueryBuilder_execute_raw_raises_TypeError_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            run(async_classes.AsyncSqlQueryBuilder(async_classes.AsyncSqlModel).execute_raw(b'not str'))
        assert str(e.exception) == 'sql must be str'

    def test_AsyncSqlQueryBuilder_insert_inserts_record_into_datastore(self):
        # e2e test
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        assert run(sqb.count()) == 0, 'count() must return 0'
        inserted = run(sqb.insert({'name': 'test1'}))
        assert isinstance(inserted, sqb.model), \
            'insert() must return instance of sqb.model'
        assert inserted.id_column not in inserted.data, \
            'insert() must not assign id'
        assert run(sqb.count()) == 1, 'count() must return 1'
        inserted = run(sqb.insert({'name': 'test2', 'id': '321'}))
        assert run(sqb.find('321')) is not None, \
            'find() must return a record that was inserted'

    def test_AsyncSqlQueryBuilder_insert_many_inserts_records_into_datastore(self):
        # e2e test
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        assert run(sqb.count()) == 0, 'count() must return 0'
        inserted = run(sqb.insert_many([
            {'name': 'test1', 'id': '123'},
            {'name': 'test1', 'id': '321'},
        ]))
        assert type(inserted) is int, 'insert_many() must return int'
        assert inserted == 2, 'insert_many() should return 2'
        assert run(sqb.count()) == 2, 'count() must return 2'
        inserted = run(sqb.insert_many([{'name': 'test3', 'id': 'abc'}]))
        assert inserted == 1
        assert run(sqb.count()) == 3, 'count() must return 3'
        assert run(sqb.find('321')) is not None, \
            'find() must return a record that was inserted'

    def test_AsyncSqlQueryBuilder_get_returns_all_matching_records(self):
        # e2e test
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        run(sqb.insert({'name': 'test1', 'id': '123'}))
        run(sqb.insert({'name': 'test2', 'id': '321'}))
        run(sqb.insert({'name': 'other', 'id': 'other'}))

        results = run(sqb.get())
        assert len(results) == 3
        for result in results:
            assert result.data['id'] in ('123', '321', 'other')
            assert result.data['name'] in ('test1', 'test2', 'other')

        results = run(sqb.starts_with('name', 'test').get())
        assert len(results) == 2
        for result in results:
            assert result.data['id'] in ('123', '321')
            assert result.data['name'] in ('test1', 'test2')

        results = run(sqb.reset().excludes('name', '1').get())
        assert len(results) == 2
        for result in results:
            assert result.data['id'] in ('321', 'other')
            assert result.data['name'] in ('test2', 'other')

    def test_AsyncSqlQueryBuilder_count_returns_correct_number(self):
        # e2e test
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        run(sqb.insert({'name': 'test1', 'id': '123'}))
        run(sqb.insert({'name': 'test2', 'id': '321'}))
        run(sqb.insert({'name': 'other', 'id': 'other'}))

        assert run(sqb.count()) == 3
        assert run(sqb.starts_with('name', 'test').count()) == 2
        assert run(sqb.reset().excludes('name', '1').count()) == 2
        assert run(sqb.reset().is_in('name', ['other']).count()) == 1

    def test_AsyncSqlQueryBuilder_skip_skips_records(self):
        # e2e test
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        run(sqb.insert({'name': 'test1', 'id': '123'}))
        run(sqb.insert({'name': 'test2', 'id': '321'}))
        run(sqb.insert({'name': 'other', 'id': 'other'}))

        list1 = run(sqb.take(2))
        assert list1 == run(sqb.take(2)), 'same limit/offset should return same results'
        list2 = run(sqb.skip(1).take(2))
        assert list1 != list2, 'different offsets should return different results'

    def test_AsyncSqlQueryBuilder_take_limits_results(self):
        # e2e test
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        run(sqb.insert({'name': 'test1', 'id': '123'}))
        run(sqb.insert({'name': 'test2', 'id': '321'}))
        run(sqb.insert({'name': 'other', 'id': 'other'}))

        assert run(sqb.count()) == 3
        assert len(run(sqb.take(1))) == 1
        assert len(run(sqb.take(2))) == 2
        assert len(run(sqb.take(3))) == 3
        assert len(run(sqb.take(5))) == 3

    def test_AsyncSqlQueryBuilder_chunk_returns_generator_that_yields_list_of_SqlModel(self):
        # e2e test
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        dicts = [{'name': i, 'id': i} for i in range(0, 25)]
        expected = [i for i in range(0, 25)]
        observed = []
        run(sqb.insert_many(dicts))

        assert run(sqb.count()) == 25
        assert isinstance(sqb.chunk(10), AsyncGeneratorType), 'chunk must return generator'
        async def iterate():
            async for results in sqb.chunk(10):
                assert type(results) is list
                for record in results:
                    assert isinstance(record, async_classes.AsyncSqlModel)
                    observed.append(int(record.data['id']))
        run(iterate())
        assert observed == expected

    def test_AsyncSqlQueryBuilder_first_returns_one_record(self):
        # e2e test
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        inserted = run(sqb.insert({'name': 'test1', 'id': '123'}))
        run(sqb.insert({'name': 'test2', 'id': '321'}))
        first = run(sqb.first())
        assert isinstance(first, sqb.model), 'first() must return instance of sqb.model'
        first = run(sqb.order_by('id', 'asc').first())
        assert first == inserted, 'first() must return correct instance'

    def test_AsyncSqlQueryBuilder_update_changes_record(self):
        # e2e test
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        run(sqb.insert({'name': 'test1', 'id': '123'}))
        assert run(sqb.find('123')).data['name'] == 'test1'
        updates = run(sqb.update({'name': 'test2'}, {'id': '123'}))
        assert type(updates) is int
        assert updates == 1
        assert run(sqb.find('123')).data['name'] == 'test2'

    def test_AsyncSqlQueryBuilder_delete_removes_record(self):
        # e2e test
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        run(sqb.insert({'name': 'test1', 'id': '123'}))
        assert run(sqb.find('123')) is not None
        deleted = run(sqb.equal('id', '123').delete())
        assert type(deleted) is int
        assert deleted == 1
        assert run(sqb.reset().find('123')) is None

    def test_AsyncSqlQueryBuilder_execute_raw_executes_raw_SQL(self):
        # e2e test
        sqb = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncSqlModel)
        assert run(sqb.count()) == 0, 'count() must return 0'
        result = run(sqb.execute_raw("insert into example (id, name) values ('123', '321')"))
        assert type(result) is tuple, 'execute_raw must return tuple'
        assert result[0] == 1, 'execute_raw returns wrong rowcount'
        assert type(result[1]) is list
        result = run(sqb.execute_raw("insert into example (id, name) values ('321', '123'), ('abc', 'cba')"))
        assert result[0] == 2, 'execute_raw returns wrong rowcount'
        assert run(sqb.count()) == 3, 'count() must return 3'

        result = run(sqb.execute_raw("select * from example"))
        assert type(result) is tuple, 'execute_raw must return tuple'
        assert len(result[1]) == 3, 'execute_raw did not return all rows'

    def test_AsyncSqlQueryBuilder_join_returns_JoinedModel(self):
        model1 = run(async_classes.AsyncSqlModel.insert({"name": "model 1"}))
        model2 = async_classes.AsyncAttachment({"details": "attachment 1"})
        model2.attach_to(model1)
        model2 = run(model2.save())

        query = async_classes.AsyncSqlModel.query()
        query.join(async_classes.AsyncAttachment, ["id", "related_id"], "inner")
        result = run(query.get())
        assert type(result) is list
        assert len(result) == 1
        result = result[0]
        assert isinstance(result, interfaces.JoinedModelProtocol)
        result
        assert model1.table in result.data and model2.table in result.data
        assert model1.data == result.data[model1.table]
        assert model2.data == result.data[model2.table]

    def test_AsyncSqlQueryBuilder_chunk_works_with_joins(self):
        hm = run(async_classes.AsyncHashedModel.insert({'details': 123}))
        for i in range(10):
            run(async_classes.AsyncAttachment({'details': i}).attach_to(hm).save())
        sqb = async_classes.AsyncSqlQueryBuilder(async_classes.AsyncHashedModel).join(
            async_classes.AsyncAttachment, ['id', 'related_id'])

        async def iterate():
            results = []
            async for chunk in sqb.chunk(5):
                assert all([type(a) is async_classes.AsyncJoinedModel for a in chunk])
                results.extend(chunk)
            return results
        results = run(iterate())
        assert len(results) == 10

    def test_AsyncSqlQueryBuilder_select_restrains_columns_selected(self):
        # without a join
        names = ['model1', 'model2']
        models = [run(async_classes.AsyncSqlModel.insert({"name": name})) for name in names]
        results = run(async_classes.AsyncSqlModel.query().select(["id"]).get())
        assert type(results) is list
        assert len(results) == 2
        assert all(["id" in r.data for r in results])
        assert all(["name" not in r.data for r in results])

        # with a join
        for model in models:
            attachment = async_classes.AsyncAttachment({"details": f"test for {model.data['name']}"})
            run(attachment.attach_to(model).save())
        sqb = async_classes.AsyncSqlModel.query()
        sqb.join(async_classes.AsyncAttachment, ["id", "related_id"])
        sqb.select(["example.name", "attachments.id"])
        results = run(sqb.get())
        assert type(results) is list
        assert len(results) == 2
        assert all(["example" in r.data and "attachments" in r.data for r in results])
        assert all([list(dict.keys(r.data["example"])) == ["name"] for r in results])
        assert all([list(dict.keys(r.data["attachments"])) == ["id"] for r in results])

    def test_AsyncSqlQueryBuilder_group_groups_results(self):
        names = ['model1', 'model2']
        models = [run(async_classes.AsyncSqlModel.insert({"name": name})) for name in names]
        for model in models:
            for i in range(5):
                attachment = async_classes.AsyncAttachment({"details": f"test data {i}"})
                run(attachment.attach_to(model).save())
        sqb = async_classes.AsyncAttachment.query().group("related_id")
        sqb.select(["count(*)", "related_id"])
        results = run(sqb.get())
        assert type(results) is list
        assert all([isinstance(r, async_classes.Row) for r in results])
        assert all([list(dict.keys(r.data)) == ["count(*)", "related_id"] for r in results])

    def test_AsyncSqlQueryBuilder_group_works_with_join(self):
        names = ['model1', 'model2']
        models = [run(async_classes.AsyncSqlModel.insert({"name": name})) for name in names]
        for model in models:
            for i in range(5):
                attachment = async_classes.AsyncAttachment({"details": f"test data {i}"})
                run(attachment.attach_to(model).save())
        sqb = async_classes.AsyncSqlModel.query().join(
            async_classes.AsyncAttachment, ['id', 'related_id']
        ).group("attachments.related_id").select(["count(*)", "name", "related_id"])
        results = run(sqb.get())
        assert type(results) is list
        assert all([isinstance(r, async_classes.Row) for r in results])
        assert all([list(dict.keys(r.data)) == ["count(*)", "name", "related_id"] for r in results])

    def test_AsyncSqlQueryBuilder_works_with_table_or_model(self):
        sqb1 = async_classes.AsyncSqlQueryBuilder(model=async_classes.AsyncHashedModel)
        assert sqb1.model is async_classes.AsyncHashedModel
        assert sqb1.table is async_classes.AsyncHashedModel.table
        assert run(sqb1.count()) == 0
        sqb2 = async_classes.AsyncSqlQueryBuilder(table=async_classes.AsyncHashedModel.table,
                                       columns=async_classes.AsyncHashedModel.columns,
                                       connection_info=DB_FILEPATH)
        assert run(sqb2.count()) == 0
        assert sqb1.table == sqb2.table
        assert type(sqb2.model) is type and issubclass(sqb2.model, async_classes.AsyncSqlModel)


    # connection_info injection/binding tests
    def test_AsyncSqliteContext_works_with_connection_info_bound(self):
        class SqliteCXMBad(async_classes.AsyncSqliteContext):
            ...

        class SqliteCXMGood(async_classes.AsyncSqliteContext):
            connection_info = DB_FILEPATH

        async def test():
            with self.assertRaises(errors.UsageError):
                async with SqliteCXMBad() as cursor:
                    ...

            async with SqliteCXMGood() as cursor:
                ...
            cxm = SqliteCXMGood()
            assert cxm.connection_info == DB_FILEPATH
        run(test())

    def test_AsyncSqlModel_works_with_connection_info_bound(self):
        class SqlModelBad(async_classes.AsyncSqlModel):
            connection_info = ''
        class SqlModelGood(async_classes.AsyncSqlModel):
            connection_info = DB_FILEPATH

        with self.assertRaises(errors.UsageError):
            run(SqlModelBad.query().count())

        assert run(SqlModelGood.query().count()) == 0

    def test_AsyncSqlQueryBuilder_works_with_connection_info_bound(self):
        class SQBUnbound(async_classes.AsyncSqlQueryBuilder):
            connection_info = ''
        class SQBBound(async_classes.AsyncSqlQueryBuilder):
            connection_info = DB_FILEPATH

        with self.assertRaises(errors.UsageError):
            run(SQBUnbound('example', columns=('id')).count())

        # no error when injected or bound
        assert run(SQBUnbound(
            'example', connection_info=DB_FILEPATH, columns=('id')
        ).count()) == 0
        assert run(SQBBound('example', columns=('id')).count()) == 0


    # AsyncHashedModel tests
    def test_AsyncHashedModel_issubclass_of_SqlModel(self):
        assert issubclass(async_classes.AsyncHashedModel, async_classes.AsyncSqlModel)

    def test_AsyncHashedModel_preimage_returns_packified_data(self):
        data = { 'details': token_bytes(8).hex() }
        observed = async_classes.AsyncHashedModel.preimage(data)
        expected = packify.pack(data)
        assert observed == expected, 'wrong preimage encountered'

    def test_AsyncHashedModel_generated_id_is_sha256_of_preimage(self):
        data = { 'details': token_bytes(8).hex() }
        observed = async_classes.AsyncHashedModel.generate_id(data)
        expected = sha256(async_classes.AsyncHashedModel.preimage(data)).digest().hex()
        assert observed == expected, 'wrong hash encountered'

    def test_AsyncHashedModel_insert_raises_TypeError_for_nondict_input(self):
        with self.assertRaises(TypeError) as e:
            run(async_classes.AsyncHashedModel.insert('not a dict'))
        assert str(e.exception) == 'data must be dict'

    def test_AsyncHashedModel_insert_generates_id_and_makes_record(self):
        data = { 'details': token_bytes(8).hex() }
        inserted = run(async_classes.AsyncHashedModel.insert(data))
        assert isinstance(inserted, async_classes.AsyncHashedModel)
        assert 'details' in inserted.data
        assert inserted.data['details'] == data['details']
        assert async_classes.AsyncHashedModel.id_column in inserted.data
        assert type(inserted.data[async_classes.AsyncHashedModel.id_column]) == str
        assert len(inserted.data[async_classes.AsyncHashedModel.id_column]) == 64
        assert len(bytes.fromhex(inserted.data[async_classes.AsyncHashedModel.id_column])) == 32

        found = run(async_classes.AsyncHashedModel.find(
            inserted.data[async_classes.AsyncHashedModel.id_column]))
        assert isinstance(found, async_classes.AsyncHashedModel)
        assert found == inserted

    def test_AsyncHashedModel_insert_many_raises_TypeError_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            run(async_classes.AsyncHashedModel.insert_many('not a list'))
        assert str(e.exception) == 'items must be type list[dict]'

        with self.assertRaises(TypeError) as e:
            run(async_classes.AsyncHashedModel.insert_many(['not a dict']))
        assert str(e.exception) == 'items must be type list[dict]'

    def test_AsyncHashedModel_insert_many_generates_ids_and_makes_records(self):
        data1 = { 'details': token_bytes(8).hex() }
        data2 = { 'details': token_bytes(8).hex() }
        inserted = run(async_classes.AsyncHashedModel.insert_many([data1, data2]))
        assert type(inserted) == int
        assert inserted == 2

        items = run(async_classes.AsyncHashedModel.query().get())
        assert type(items) is list
        assert len(items) == 2
        for item in items:
            assert item.data['details'] in (data1['details'], data2['details'])
            assert async_classes.AsyncHashedModel.id_column in item.data
            assert type(item.data[async_classes.AsyncHashedModel.id_column]) == str
            assert len(item.data[async_classes.AsyncHashedModel.id_column]) == 64
            assert len(bytes.fromhex(item.data[async_classes.AsyncHashedModel.id_column])) == 32

    def test_AsyncHashedModel_update_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            run(async_classes.AsyncHashedModel({}).update('not a dict'))
        assert str(e.exception) == 'updates must be dict'

        with self.assertRaises(ValueError) as e:
            run(async_classes.AsyncHashedModel({}).update({'badcolumn': '123'}))
        assert str(e.exception) == 'unrecognized column: badcolumn'

    def test_AsyncHashedModel_save_and_update_delete_original_and_makes_new_record(self):
        data1 = { 'details': token_bytes(8).hex() }
        data2 = { 'details': token_bytes(8).hex() }
        data3 = { 'details': token_bytes(8).hex() }

        inserted = run(async_classes.AsyncHashedModel.insert(data1))
        id1 = inserted.data['id']
        assert run(async_classes.AsyncDeletedModel.query().count()) == 0

        updated = run(inserted.update(data2))
        assert run(async_classes.AsyncDeletedModel.query().count()) == 1
        assert updated.data == inserted.data
        assert updated.data['id'] != id1

        updated.data['details'] = data3['details']
        id2 = updated.data['id']
        saved = run(updated.save())
        assert run(async_classes.AsyncDeletedModel.query().count()) == 2
        assert saved.data['id'] not in (id1, id2)

    def test_AsyncHashedModel_subclass_commits_to_empty_columns(self):
        class HashedSubclass(async_classes.AsyncHashedModel):
            table = 'hashed_subclass'
            columns = ('id', 'column1', 'column2')
            column1: str
            column2: str

        original = run(HashedSubclass.insert({'column1': 'stuff'}))
        expected_id = sha256(
            packify.pack({'column1': 'stuff', 'column2': None})
        ).digest().hex()
        assert original.id == expected_id
        deleted = run(original.delete())
        restored = run(deleted.restore({'HashedSubclass': HashedSubclass}))
        assert restored.id == original.id

    def test_AsyncHashedModel_subclass_does_not_commit_to_excluded_columns(self):
        class HashedSubclass(async_classes.AsyncHashedModel):
            table = 'hashed_subclass'
            columns = ('id', 'column1', 'column2')
            columns_excluded_from_hash = ('column2',)
            column1: str
            column2: str

        original = run(HashedSubclass.insert({'column1': 'stuff', 'column2': 'something'}))
        expected_id = sha256(
            packify.pack({'column1': 'stuff'})
        ).digest().hex()
        assert original.id == expected_id
        deleted = run(original.delete())
        restored = run(deleted.restore({'HashedSubclass': HashedSubclass}))
        assert restored.id == original.id

    def test_AsyncHashedModel_subclass_does_not_commit_to_excluded_columns(self):
        class HashedSubclass(async_classes.AsyncHashedModel):
            table = 'hashed_subclass'
            columns = ('id', 'column1', 'column2')
            columns_excluded_from_hash = ('column2',)
            column1: str
            column2: str

        original = run(HashedSubclass.insert({'column1': 'stuff', 'column2': 'something'}))
        run(original.update({'column2': 'something else'}))
        same = run(HashedSubclass.find(original.id))
        assert same.column2 == 'something else', same

    def test_AsyncHashedModel_event_hooks(self):
        log = []
        def addlog(*args, **kwargs):
            log.append((args, kwargs))
        count = 0
        def next_details():
            nonlocal count
            count += 1
            return f'test {count}'

        class HashedSubclass(async_classes.AsyncHashedModel):
            table = 'hashed_subclass'
            columns = ('id', 'column1', 'column2')
            column1: str
            column2: str

        # insert; no event on subclass
        async_classes.AsyncHashedModel.add_hook('before_insert', addlog)
        async_classes.AsyncHashedModel.add_hook('after_insert', addlog)
        assert len(log) == 0, 'invalid test precondition'
        run(async_classes.AsyncHashedModel.insert({'details': next_details()}))
        assert len(log) == 2
        run(async_classes.AsyncHashedModel.insert({'details': next_details()}, suppress_events=True))
        assert len(log) == 2
        run(HashedSubclass.insert({'column1': next_details()}))
        assert len(log) == 2, len(log)
        async_classes.AsyncHashedModel.clear_hooks('before_insert')
        async_classes.AsyncHashedModel.clear_hooks('after_insert')
        run(async_classes.AsyncHashedModel.insert({'details': next_details()}))
        assert len(log) == 2
        log.clear()

        # insert; event on subclass only
        HashedSubclass.add_hook('before_insert', addlog)
        HashedSubclass.add_hook('after_insert', addlog)
        assert len(log) == 0, 'invalid test precondition'
        run(async_classes.AsyncHashedModel.insert({'column1': next_details()}))
        assert len(log) == 0
        run(HashedSubclass.insert({'column1': next_details()}))
        assert len(log) == 2
        run(HashedSubclass.insert({'column1': next_details()}, suppress_events=True))
        assert len(log) == 2
        HashedSubclass.clear_hooks('before_insert')
        HashedSubclass.clear_hooks('after_insert')
        run(HashedSubclass.insert({'column1': next_details()}))
        assert len(log) == 2
        log.clear()

        # insert many
        async_classes.AsyncHashedModel.add_hook('before_insert_many', addlog)
        async_classes.AsyncHashedModel.add_hook('after_insert_many', addlog)
        assert len(log) == 0, 'invalid test precondition'
        run(async_classes.AsyncHashedModel.insert_many([{'details': next_details()}]))
        assert len(log) == 2
        run(async_classes.AsyncHashedModel.insert_many([{'details': next_details()}], suppress_events=True))
        assert len(log) == 2
        async_classes.AsyncHashedModel.clear_hooks('before_insert_many')
        async_classes.AsyncHashedModel.clear_hooks('after_insert_many')
        run(async_classes.AsyncHashedModel.insert_many([{'details': next_details()}]))
        assert len(log) == 2
        log.clear()

        # update
        model = run(async_classes.AsyncHashedModel.query().order_by('details').first())
        async_classes.AsyncHashedModel.add_hook('before_update', addlog)
        async_classes.AsyncHashedModel.add_hook('after_update', addlog)
        assert len(log) == 0, 'invalid test precondition'
        model = run(model.update({'details': next_details()}))
        assert len(log) == 2, len(log)
        model = run(model.update({'details': next_details()}, suppress_events=True))
        assert len(log) == 2, len(log)
        async_classes.AsyncHashedModel.clear_hooks('before_update')
        async_classes.AsyncHashedModel.clear_hooks('after_update')
        model = run(model.update({'details': next_details()}))
        assert len(log) == 2, len(log)
        log.clear()

        # delete
        async_classes.AsyncHashedModel.add_hook('before_delete', addlog)
        async_classes.AsyncHashedModel.add_hook('after_delete', addlog)
        assert len(log) == 0, 'invalid test precondition'
        run(run(async_classes.AsyncHashedModel.query().first()).delete())
        assert len(log) == 2, len(log)
        run(run(async_classes.AsyncHashedModel.query().first()).delete(suppress_events=True))
        assert len(log) == 2, len(log)
        async_classes.AsyncHashedModel.clear_hooks()
        run(run(async_classes.AsyncHashedModel.query().first()).delete())
        assert len(log) == 2, len(log)


    # AsyncDeletedModel tests
    def test_AsyncDeletedModel_issubclass_of_SqlModel(self):
        assert issubclass(async_classes.AsyncDeletedModel, async_classes.AsyncSqlModel)

    def test_AsyncDeletedModel_created_when_HashedModel_is_deleted(self):
        item = run(async_classes.AsyncHashedModel.insert({'data': '123'}))
        deleted = run(item.delete())
        assert isinstance(deleted, async_classes.AsyncDeletedModel)
        assert type(deleted.data[deleted.id_column]) is str
        assert run(async_classes.AsyncDeletedModel.find(deleted.data[deleted.id_column])) != None

    def test_AsyncDeletedModel_restore_returns_SqlModel_and_deleted_records_row(self):
        item = run(async_classes.AsyncHashedModel.insert({'data': '123'}))

        deleted = run(item.delete())
        assert run(async_classes.AsyncDeletedModel.find(deleted.data[deleted.id_column])) is not None
        assert run(async_classes.AsyncHashedModel.find(item.data[item.id_column])) is None

        restored = run(deleted.restore())
        assert isinstance(restored, async_classes.AsyncSqlModel)
        assert run(async_classes.AsyncDeletedModel.find(deleted.data[deleted.id_column])) is None
        assert run(async_classes.AsyncHashedModel.find(restored.data[restored.id_column])) is not None

    def test_AsyncDeletedModel_restore_raises_errors_for_invalid_target_record(self):
        class NotValidClass:
            ...

        async_classes.NotValidClass = NotValidClass

        deleted = run(async_classes.AsyncDeletedModel.query().insert({
            'id': async_classes.AsyncDeletedModel.generate_id(),
            'model_class': 'sdskdj',
            'record_id': 'dsdisjd',
            'record': 'codework',
            'timestamp': 123,
        }))

        with self.assertRaises(ValueError) as e:
            run(deleted.restore())
        assert str(e.exception) == 'model_class must be accessible'

        deleted = run(async_classes.AsyncDeletedModel.query().insert({
            'id': async_classes.AsyncDeletedModel.generate_id(),
            'model_class': NotValidClass.__name__,
            'record_id': 'dsdisjd',
            'record': '{"January": "is a decent song"}',
            'timestamp': 123,
        }))

        with self.assertRaises(TypeError) as e:
            run(deleted.restore())
        assert str(e.exception) == 'related_model must inherit from AsyncSqlModel'

    def test_AsyncDeletedModel_event_hooks(self):
        log = []
        def make_handler(name):
            def addlog(cls, *args, **kwargs):
                log.append((name, args, kwargs))
            return addlog

        # insert
        async_classes.AsyncDeletedModel.add_hook('before_insert', make_handler('before_insert'))
        async_classes.AsyncDeletedModel.add_hook('after_insert', make_handler('after_insert'))
        model = run(async_classes.AsyncHashedModel.insert({'details': 'test'}))
        assert len(log) == 0, 'invalid test precondition'
        deleted = run(model.delete())
        assert len(log) == 2, '\n'.join([repr(l) for l in log])
        model: async_classes.AsyncHashedModel = run(deleted.restore())
        deleted = run(model.delete(suppress_events=True))
        assert len(log) == 2, '\n'.join([repr(l) for l in log])
        model = run(deleted.restore())
        async_classes.AsyncDeletedModel.clear_hooks()
        deleted = run(model.delete())
        assert len(log) == 2, '\n'.join([repr(l) for l in log])
        log.clear()

        # restore
        async_classes.AsyncDeletedModel.add_hook('before_restore', make_handler('before_restore'))
        async_classes.AsyncDeletedModel.add_hook('after_restore', make_handler('after_restore'))
        assert len(log) == 0, 'invalid test precondition'
        model = run(deleted.restore())
        assert len(log) == 2
        deleted = run(model.delete())
        model = run(deleted.restore(suppress_events=True))
        assert len(log) == 2
        deleted = run(model.delete())
        async_classes.AsyncDeletedModel.clear_hooks()
        model = run(deleted.restore())
        assert len(log) == 2
        async_classes.AsyncDeletedModel.clear_hooks()


    # AsyncAttachment tests
    def test_AsyncAttachment_issubclass_of_HashedModel(self):
        assert issubclass(async_classes.AsyncAttachment, async_classes.AsyncHashedModel)

    def test_AsyncAttachment_attach_to_raises_TypeError_for_invalid_input(self):
        class NotValidClass:
            ...

        with self.assertRaises(TypeError) as e:
            async_classes.AsyncAttachment({'details': 'should fail'}).attach_to(NotValidClass())
        assert str(e.exception) == 'related must inherit from AsyncSqlModel'

    def test_AsyncAttachment_attach_to_sets_related_model_and_related_id(self):
        data = { 'data': token_bytes(8).hex() }
        hashedmodel = run(async_classes.AsyncHashedModel.insert(data))
        attachment = async_classes.AsyncAttachment()
        attachment.attach_to(hashedmodel)

        assert 'related_model' in attachment.data
        assert attachment.data['related_model'] == hashedmodel.__class__.__name__
        assert 'related_id' in attachment.data
        assert attachment.data['related_id'] == hashedmodel.data['id']

    def test_AsyncAttachment_set_details_packs_and_details_unpacks(self):
        details = {'123': 'some information'}
        attachment = async_classes.AsyncAttachment()

        assert 'details' not in attachment.data

        attachment.set_details(details)
        assert 'details' in attachment.data
        assert type(attachment.data['details']) is bytes

        assert type(attachment.get_details()) is dict
        assert attachment.get_details(True) == details

    def test_AsyncAttachment_related_raises_TypeError_for_invalid_related_model(self):
        class NotValidClass:
            ...

        async_classes.NotValidClass = NotValidClass

        attachment = run(async_classes.AsyncAttachment.insert({
            'related_model': 'not even a real class name',
            'related_id': '321',
            'details': 'chill music is nice to listen to while coding'
        }))
        with self.assertRaises(ValueError) as e:
            run(attachment.related())
        assert str(e.exception) == 'model_class must be accessible'

        attachment = run(async_classes.AsyncAttachment.insert({
            'related_model': NotValidClass.__name__,
            'related_id': '321',
            'details': 'fail whale incoming'
        }))
        with self.assertRaises(TypeError) as e:
            run(attachment.related())
        assert str(e.exception) == 'related_model must inherit from AsyncSqlModel'

    def test_AsyncAttachment_related_returns_SqlModel_instance(self):
        data = { 'data': token_bytes(8).hex() }
        hashedmodel = run(async_classes.AsyncHashedModel.insert(data))
        details = {'123': 'some information'}
        attachment = async_classes.AsyncAttachment({'details': packify.pack(details)})
        attachment.attach_to(hashedmodel)
        run(attachment.save())

        related = run(attachment.related(True))
        assert isinstance(related, async_classes.AsyncSqlModel)

    def test_AsyncAttachment_insert_event_hook(self):
        log = []
        def make_handler(name):
            def addlog(cls, *args, **kwargs):
                log.append((name, args, kwargs))
            return addlog

        async_classes.AsyncAttachment.add_hook('before_insert', make_handler('before_insert'))
        async_classes.AsyncAttachment.add_hook('after_insert', make_handler('before_insert'))
        assert len(log) == 0, 'invalid test precondition'
        run(async_classes.AsyncAttachment.insert({
            'related_model': 'HashedModel',
            'related_id': 'abcdef',
            'details': 'something testy'
        }))
        assert len(log) == 2, len(log)
        run(async_classes.AsyncAttachment.insert({
            'related_model': 'HashedModel',
            'related_id': 'abcdef',
            'details': 'something testy2'
        }, suppress_events=True))
        assert len(log) == 2, len(log)
        async_classes.AsyncAttachment.clear_hooks()
        run(async_classes.AsyncAttachment.insert({
            'related_model': 'HashedModel',
            'related_id': 'abcdef',
            'details': 'something testy3'
        }))
        assert len(log) == 2, len(log)


    # ExampleModel and ExampleHashedModel tests
    def test_ExampleModel_and_ExampleHashedModel_e2e(self):
        em: ExampleModel = run(ExampleModel.insert({
            'field1': 'value1',
            'field2': 2,
            'field3': False,
            'field4': b'321',
            'field5': 3.21,
            'field1nd': None,
        }))
        em = run(em.reload())
        assert em.field1 == 'value1', em.field1
        assert em.field2 == 2, em.field2
        assert em.field3 == False, em.field3
        assert em.field4 == b'321', em.field4
        assert em.field5 == 3.21, em.field5
        assert em.field1n is None, em.field1n
        assert em.field2n is None, em.field2n
        assert em.field3n is None, em.field3n
        assert em.field4n is None, em.field4n
        assert em.field5n is None, em.field5n
        assert em.field1d == 'foobar', em.field1d
        assert em.field2d == 123, em.field2d
        assert em.field3d == True, em.field3d
        assert em.field4d == b'123', em.field4d
        assert em.field5d == 1.23, em.field5d
        assert em.field1nd is None, em.field1nd
        assert em.field2nd == 123, em.field2nd
        assert em.field3nd == True, em.field3nd
        assert em.field4nd == b'123', em.field4nd
        assert em.field5nd == 1.23, em.field5nd

        ehm: ExampleHashedModel = run(ExampleHashedModel.insert({
            'field1': 'value1',
            'field2': 2,
            'field3': False,
            'field4': b'321',
            'field5': 3.21,
            'field1nd': None,
        }))
        ehm = run(ehm.reload())
        assert ehm.field1 == 'value1', ehm.field1
        assert ehm.field2 == 2, ehm.field2
        assert ehm.field3 == False, ehm.field3
        assert ehm.field4 == b'321', ehm.field4
        assert ehm.field5 == 3.21, ehm.field5
        assert ehm.field1n is None, ehm.field1n
        assert ehm.field2n is None, ehm.field2n
        assert ehm.field3n is None, ehm.field3n
        assert ehm.field4n is None, ehm.field4n
        assert ehm.field5n is None, ehm.field5n
        assert ehm.field1d == 'foobar', ehm.field1d
        assert ehm.field2d == 123, ehm.field2d
        assert ehm.field3d == True, ehm.field3d
        assert ehm.field4d == b'123', ehm.field4d
        assert ehm.field5d == 1.23, ehm.field5d
        assert ehm.field1nd is None, ehm.field1nd
        assert ehm.field2nd == 123, ehm.field2nd
        assert ehm.field3nd == True, ehm.field3nd
        assert ehm.field4nd == b'123', ehm.field4nd
        assert ehm.field5nd == 1.23, ehm.field5nd

        query = ExampleModel.query().join(ExampleHashedModel, ['field1', 'field1'])
        result = run(query.get())
        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], async_classes.AsyncJoinedModel)
        em = ExampleModel(result[0].data[ExampleModel.table])
        ehm = ExampleHashedModel(result[0].data[ExampleHashedModel.table])
        assert em.field1 == 'value1', em.field1
        assert type(em.field3) is bool, (em.field3, em.data)
        assert em.field3n is None, em.field3n
        assert type(em.field3d) is bool, em.field3d
        assert type(em.field3nd) is bool, em.field3nd
        assert ehm.field1 == 'value1', ehm.field1
        assert type(ehm.field3) is bool, ehm.field3
        assert ehm.field3n is None, ehm.field3n
        assert type(ehm.field3d) is bool, ehm.field3d
        assert type(ehm.field3nd) is bool, ehm.field3nd


if __name__ == '__main__':
    unittest.main()
