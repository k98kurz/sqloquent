from secrets import token_bytes
from context import classes, interfaces
from genericpath import isfile
from hashlib import sha256
from types import GeneratorType
import os
import packify
import sqlite3
import unittest


class TestClasses(unittest.TestCase):
    db_filepath: str = 'test.db'
    db: sqlite3.Connection = None
    cursor: sqlite3.Cursor = None

    def setUp(self) -> None:
        """Set up the test database."""
        try:
            if isfile(self.db_filepath):
                os.remove(self.db_filepath)
        except:
            ...
        self.db = sqlite3.connect(self.db_filepath)
        self.cursor = self.db.cursor()
        self.cursor.execute('create table deleted_records (id text not null, ' +
            'model_class text not null, record_id text not null, record blob not null)')
        self.cursor.execute('create table example (id text, name text)')
        self.cursor.execute('create table hashed_records (id text, details text)')
        self.cursor.execute('create table attachments (id text, ' +
            'related_model text, related_id text, details blob)')

        return super().setUp()

    def setUpClass() -> None:
        """Couple these models to sqlite for testing purposes."""
        classes.SqliteModel.file_path = TestClasses.db_filepath

        classes.DeletedModel.file_path = TestClasses.db_filepath
        classes.DeletedModel.query_builder_class = classes.SqliteQueryBuilder

        classes.HashedModel.file_path = TestClasses.db_filepath
        classes.HashedModel.query_builder_class = classes.SqliteQueryBuilder

        classes.Attachment.file_path = TestClasses.db_filepath
        classes.Attachment.query_builder_class = classes.SqliteQueryBuilder

    def tearDown(self) -> None:
        """Close cursor and delete test database."""
        self.cursor.close()
        self.db.close()
        os.remove(self.db_filepath)
        return super().tearDown()

    # general tests
    def test_classes_contains_correct_classes_and_functions(self):
        assert hasattr(classes, 'SqliteContext')
        assert type(classes.SqliteContext) is type
        assert hasattr(classes, 'SqlModel')
        assert type(classes.SqlModel) is type
        assert hasattr(classes, 'SqliteModel')
        assert type(classes.SqliteModel) is type
        assert hasattr(classes, 'JoinedModel')
        assert type(classes.JoinedModel) is type
        assert hasattr(classes, 'JoinSpec')
        assert type(classes.JoinSpec) is type
        assert hasattr(classes, 'Row')
        assert type(classes.Row) is type
        assert hasattr(classes, 'dynamic_sqlite_model')
        assert callable(classes.dynamic_sqlite_model)
        assert hasattr(classes, 'SqlQueryBuilder')
        assert type(classes.SqlQueryBuilder) is type
        assert hasattr(classes, 'SqliteQueryBuilder')
        assert type(classes.SqliteQueryBuilder) is type
        assert hasattr(classes, 'DeletedModel')
        assert type(classes.DeletedModel) is type
        assert hasattr(classes, 'HashedModel')
        assert type(classes.HashedModel) is type
        assert hasattr(classes, 'Attachment')
        assert type(classes.Attachment) is type


    # context manager tests
    def test_SqliteContext_implements_DBContextProtocol(self):
        assert issubclass(classes.SqliteContext, interfaces.DBContextProtocol)

    def test_SqliteContext_raises_errors_for_invalid_use(self):
        with self.assertRaises(TypeError) as e:
            with classes.SqliteContext('not a SqliteModel'):
                ...
        assert str(e.exception) == 'model must be child class of SqlModel'

        with self.assertRaises(TypeError) as e:
            with classes.SqliteContext(str):
                ...
        assert str(e.exception) == 'model must be child class of SqlModel'

        with self.assertRaises(TypeError) as e:
            class InvalidModel(classes.SqliteModel):
                file_path = []
            with classes.SqliteContext(InvalidModel):
                ...
        assert 'model.file_path' in str(e.exception)
        assert 'must be str or bytes' in str(e.exception)


    # SqlModel tests
    def test_SqlModel_implements_ModelProtocol(self):
        assert isinstance(classes.SqlModel(), interfaces.ModelProtocol)

    def test_SqlModel_columns_are_set_as_properties(self):
        model = classes.SqlModel({'id': '123', 'name': 'Bob'})
        assert hasattr(model, 'id') and model.id == '123'
        assert hasattr(model, 'name') and model.name == 'Bob'
        model.name = 'Alice'
        assert model.data['name'] == 'Alice'

    def test_SqlModel_column_property_mapping_can_be_disabled(self):
        class Disabled(classes.SqlModel):
            disable_column_property_mapping: bool = True
        model = Disabled({'id': '123', 'name': 'Bob'})
        assert not hasattr(model, 'id') and model.data['id'] == '123'
        assert not hasattr(model, 'name') and model.data['name'] == 'Bob'

    def test_SqlModel_column_property_mapping_disabled_for_colliding_names(self):
        class Derived(classes.SqlModel):
            columns: tuple[str] = ('id', 'name', 'save', 'data')
        model = Derived({'id': '123', 'name': 'Bob', 'save': 'to-do', 'data': '321'})
        assert hasattr(model, 'save') and callable(model.save)
        assert 'save' in model.data and model.data['save'] == 'to-do'
        assert 'data' in model.data and model.data['data'] == '321'

    def test_SqlModel_post_init_hooks_are_called(self):
        class TestModel(classes.SqlModel):
            ...

        signals = {}
        def test1(_):
            signals['test1'] = 1

        TestModel._post_init_hooks = {
            'test1': test1
        }
        _ = TestModel()

        assert 'test1' in signals

    def test_SqlModel_init_raises_errors_for_invalid_post_init_hooks(self):
        class TestModel(classes.SqlModel):
            ...

        TestModel._post_init_hooks = []
        with self.assertRaises(TypeError) as e:
            _ = TestModel()
        assert str(e.exception) == '_post_init_hooks must be a dict mapping names to Callables'

        TestModel._post_init_hooks = {'name': 'not callable'}
        with self.assertRaises(ValueError) as e:
            _ = TestModel()
        assert str(e.exception) == '_post_init_hooks must be a dict mapping names to Callables'

    def test_SqlModel_encode_value_raises_packify_UsageError_for_unrecognized_type(self):
        with self.assertRaises(packify.UsageError) as e:
            classes.SqlModel.encode_value(classes.SqlModel)

    def test_SqlModel_encode_value_encodes_values_properly(self):
        bstr = b'123'
        assert classes.SqlModel.encode_value(bstr) == packify.pack(bstr).hex()

        list_of_bytes = [b'123', b'321']
        expected = packify.pack(list_of_bytes).hex()
        assert classes.SqlModel.encode_value(list_of_bytes) == expected

        tuple_of_bytes = (b'123', b'321')
        expected = packify.pack(tuple_of_bytes).hex()
        assert classes.SqlModel.encode_value(tuple_of_bytes) == expected

        unencoded_dict = {b'123': b'321', 1: '123'}
        expected = packify.pack(unencoded_dict).hex()
        assert classes.SqlModel.encode_value(unencoded_dict) == expected

    def test_SqlModel_insert_raises_TypeError_for_nondict_input(self):
        with self.assertRaises(TypeError) as e:
            classes.SqlModel.insert('not a dict')
        assert str(e.exception) == 'data must be dict'

    def test_SqlModel_insert_many_raises_TypeError_for_nonlist_of_dict_input(self):
        with self.assertRaises(TypeError) as e:
            classes.SqlModel.insert_many('not a list')
        assert str(e.exception) == 'items must be type list[dict]'

        with self.assertRaises(TypeError) as e:
            classes.SqlModel.insert_many(['not a dict'])
        assert str(e.exception) == 'items must be type list[dict]'

    def test_SqlModel_update_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            classes.SqlModel().update('not a dict')
        assert str(e.exception) == 'updates must be dict'

        with self.assertRaises(TypeError) as e:
            classes.SqlModel().update({}, 'not a dict')
        assert str(e.exception) == 'conditions must be dict or None'

        with self.assertRaises(ValueError) as e:
            classes.SqlModel().update({})
        assert str(e.exception) == f'instance must have id or conditions defined'


    # SqliteModel tests
    def test_SqliteModel_implements_ModelProtocol(self):
        assert isinstance(classes.SqliteModel(), interfaces.ModelProtocol)

    def test_SqliteModel_extends_SqlModel(self):
        assert issubclass(classes.SqliteModel, classes.SqlModel)

    def test_SqliteModel_insert_and_find(self):
        # e2e test
        inserted = classes.SqliteModel.insert({'name': 'test1'})
        assert isinstance(inserted, classes.SqliteModel), \
            'insert() must return SqliteModel instance'
        assert classes.SqliteModel.id_column in inserted.data, \
            'insert() return value must have id'

        found = classes.SqliteModel.find(inserted.data[classes.SqliteModel.id_column])
        assert isinstance(found, classes.SqliteModel), \
            'find() must return SqliteModel instance'

        assert inserted == found, \
            'inserted must equal found'

    def test_SqliteModel_update_save_and_delete(self):
        # e2e test
        inserted = classes.SqliteModel.insert({'name': 'test1'})
        updated = inserted.update({'name': 'test2'})
        assert isinstance(updated, classes.SqliteModel), \
            'update() must return SqliteModel instance'
        assert updated.data['name'] == 'test2', 'value must be updated'
        assert updated == inserted, 'must be equal'
        found = classes.SqliteModel.find(inserted.data[inserted.id_column])
        assert updated == found, 'must be equal'

        updated.data['name'] = 'test3'
        saved = updated.save()
        assert isinstance(saved, classes.SqliteModel), \
            'save() must return SqliteModel instance'
        assert saved == updated, 'must be equal'
        found = classes.SqliteModel.find(inserted.data[inserted.id_column])
        assert saved == found, 'must be equal'

        updated.delete()
        found = classes.SqliteModel.find(inserted.data[inserted.id_column])
        assert found is None, 'found must be None'

    def test_SqliteModel_insert_many_and_count(self):
        # e2e test
        inserted = classes.SqliteModel.insert_many([
            {'name': 'test1'},
            {'name': 'test2'},
        ])
        assert type(inserted) is int, 'insert_many() must return int'
        assert inserted == 2, 'insert_many() should return 2'

        found = classes.SqliteModel.query().count()
        assert found == 2

    def test_SqliteModel_reload_reads_values_from_db(self):
        model = classes.SqliteModel.insert({'name': 'Tarzan'})
        model.query({'id':model.data['id']}).update({'name': 'Jane'})
        assert model.data['name'] == 'Tarzan'
        model.reload()
        assert model.data['name'] == 'Jane'


    # JoinedModel test
    def test_JoinedModel_get_models_returns_correct_models(self):
        model1 = classes.SqliteModel.insert({"name": "model 1"})
        model2 = classes.Attachment({"details": "attachment 1"})
        model2.attach_to(model1)
        model2 = model2.save()

        joined = classes.JoinedModel(
            [classes.SqliteModel, classes.Attachment],
            {
                **{
                    f"{classes.SqliteModel.table}.{k}": v
                    for k,v in model1.data.items()
                },
                **{
                    f"{classes.Attachment.table}.{k}": v
                    for k,v in model2.data.items()
                },
            }
        )

        models = joined.get_models()
        assert type(models) is list and len(models) == 2
        assert model1 in models
        assert model2 in models


    # Row test
    def test_Row_initializes_correctly(self):
        row = classes.Row({'a': b'c'})
        assert isinstance(row, interfaces.RowProtocol)
        assert row.data == {'a': b'c'}


    # dynamic_sqlite_model test
    def test_dynamic_sqlite_model_returns_type_ModelProtocol(self):
        filepath = "some/path/to/file.db"
        tablename = "some_table"
        modelclass = classes.dynamic_sqlite_model(filepath, tablename)
        assert type(modelclass) is type
        assert issubclass(modelclass, classes.SqliteModel)
        model = modelclass()
        assert isinstance(model, interfaces.ModelProtocol)
        assert hasattr(model, "file_path") and model.file_path == filepath
        assert hasattr(model, "table") and model.table == tablename

        modelclass = classes.dynamic_sqlite_model("some/path/to/file.db")
        assert type(modelclass) is type
        assert issubclass(modelclass, classes.SqliteModel)
        model = modelclass()
        assert isinstance(model, interfaces.ModelProtocol)
        assert hasattr(model, "file_path") and model.file_path == filepath
        assert model.table == ""


    # SqlQueryBuilder tests
    def test_SqlQueryBuilder_implements_QueryBuilderProtocol(self):
        assert isinstance(classes.SqlQueryBuilder, interfaces.QueryBuilderProtocol)

    def test_SqlQueryBuilder_rejects_invalid_model(self):
        with self.assertRaises(TypeError) as e:
            sqb = classes.SqlQueryBuilder(model=dict)
        assert str(e.exception) == 'model must be SqlModel subclass'

        with self.assertRaises(TypeError) as e:
            sqb = classes.SqlQueryBuilder(model='ssds')
        assert str(e.exception) == 'model must be SqlModel subclass'

    def test_SqlQueryBuilder_equal_raises_TypeError_for_nonstr_column(self):
        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).equal(b'not a str', '')
        assert str(e.exception) == 'column must be str'

    def test_SqlQueryBuilder_equal_adds_correct_clause_and_param(self):
        sqb = classes.SqlQueryBuilder(model=classes.SqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.equal('name', 'test')
        assert len(sqb.clauses) == 1, 'equal() must append to clauses'
        assert len(sqb.params) == 1, 'equal() must append to params'
        assert sqb.clauses[0] == 'name = ?'
        assert sqb.params[0] == 'test'

    def test_SqlQueryBuilder_not_equal_raises_TypeError_for_nonstr_column(self):
        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).not_equal(b'not a str', '')
        assert str(e.exception) == 'column must be str'

    def test_SqlQueryBuilder_not_equal_adds_correct_clause_and_param(self):
        sqb = classes.SqlQueryBuilder(model=classes.SqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.not_equal('name', 'test')
        assert len(sqb.clauses) == 1, 'not_equal() must append to clauses'
        assert len(sqb.params) == 1, 'not_equal() must append to params'
        assert sqb.clauses[0] == 'name != ?'
        assert sqb.params[0] == 'test'

    def test_SqlQueryBuilder_less_raises_TypeError_for_nonstr_column(self):
        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).less(b'not a str', '')
        assert str(e.exception) == 'column must be str'

    def test_SqlQueryBuilder_less_adds_correct_clause_and_param(self):
        sqb = classes.SqlQueryBuilder(model=classes.SqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.less('name', '123')
        assert len(sqb.clauses) == 1, 'less() must append to clauses'
        assert len(sqb.params) == 1, 'less() must append to params'
        assert sqb.clauses[0] == 'name < ?'
        assert sqb.params[0] == '123'

    def test_SqlQueryBuilder_greater_raises_TypeError_for_nonstr_column(self):
        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).greater(b'not a str', '')
        assert str(e.exception) == 'column must be str'

    def test_SqlQueryBuilder_greater_adds_correct_clause_and_param(self):
        sqb = classes.SqlQueryBuilder(model=classes.SqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.greater('name', '123')
        assert len(sqb.clauses) == 1, 'greater() must append to clauses'
        assert len(sqb.params) == 1, 'greater() must append to params'
        assert sqb.clauses[0] == 'name > ?'
        assert sqb.params[0] == '123'

    def test_SqlQueryBuilder_starts_with_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).starts_with(b'not a str', '')
        assert str(e.exception) == 'column must be str'

        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).starts_with('', b'not a str')
        assert str(e.exception) == 'data must be str'

        with self.assertRaises(ValueError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).starts_with('', 'sds')
        assert str(e.exception) == 'column cannot be empty'

        with self.assertRaises(ValueError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).starts_with('sds', '')
        assert str(e.exception) == 'data cannot be empty'

    def test_SqlQueryBuilder_starts_with_adds_correct_clause_and_param(self):
        sqb = classes.SqlQueryBuilder(model=classes.SqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.starts_with('name', '123')
        assert len(sqb.clauses) == 1, 'starts_with() must append to clauses'
        assert len(sqb.params) == 1, 'starts_with() must append to params'
        assert sqb.clauses[0] == 'name like ?'
        assert sqb.params[0] == '123%'

    def test_SqlQueryBuilder_contains_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).contains(b'not a str', '')
        assert str(e.exception) == 'column must be str'

        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).contains('', b'not a str')
        assert str(e.exception) == 'data must be str'

        with self.assertRaises(ValueError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).contains('', 'sds')
        assert str(e.exception) == 'column cannot be empty'

        with self.assertRaises(ValueError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).contains('sds', '')
        assert str(e.exception) == 'data cannot be empty'

    def test_SqlQueryBuilder_contains_adds_correct_clause_and_param(self):
        sqb = classes.SqlQueryBuilder(model=classes.SqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.contains('name', '123')
        assert len(sqb.clauses) == 1, 'contains() must append to clauses'
        assert len(sqb.params) == 1, 'contains() must append to params'
        assert sqb.clauses[0] == 'name like ?'
        assert sqb.params[0] == '%123%'

    def test_SqlQueryBuilder_excludes_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).excludes(b'not a str', '')
        assert str(e.exception) == 'column must be str'

        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).excludes('', b'not a str')
        assert str(e.exception) == 'data must be str'

        with self.assertRaises(ValueError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).excludes('', 'sds')
        assert str(e.exception) == 'column cannot be empty'

        with self.assertRaises(ValueError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).excludes('sds', '')
        assert str(e.exception) == 'data cannot be empty'

    def test_SqlQueryBuilder_excludes_adds_correct_clause_and_param(self):
        sqb = classes.SqlQueryBuilder(model=classes.SqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.excludes('name', '123')
        assert len(sqb.clauses) == 1, 'excludes() must append to clauses'
        assert len(sqb.params) == 1, 'excludes() must append to params'
        assert sqb.clauses[0] == 'name not like ?'
        assert sqb.params[0] == '%123%'

    def test_SqlQueryBuilder_ends_with_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).ends_with(b'not a str', '')
        assert str(e.exception) == 'column must be str'

        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).ends_with('', b'not a str')
        assert str(e.exception) == 'data must be str'

        with self.assertRaises(ValueError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).ends_with('', 'sds')
        assert str(e.exception) == 'column cannot be empty'

        with self.assertRaises(ValueError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).ends_with('sds', '')
        assert str(e.exception) == 'data cannot be empty'

    def test_SqlQueryBuilder_ends_with_adds_correct_clause_and_param(self):
        sqb = classes.SqlQueryBuilder(model=classes.SqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.ends_with('name', '123')
        assert len(sqb.clauses) == 1, 'ends_with() must append to clauses'
        assert len(sqb.params) == 1, 'ends_with() must append to params'
        assert sqb.clauses[0] == 'name like ?'
        assert sqb.params[0] == '%123'

    def test_SqlQueryBuilder_is_in_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).is_in(b'not a str', 'not list')
        assert str(e.exception) == 'column must be str'

        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).is_in('', 'not a list')
        assert str(e.exception) == 'data must be tuple or list'

        with self.assertRaises(ValueError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).is_in('', ['sds'])
        assert str(e.exception) == 'column cannot be empty'

        with self.assertRaises(ValueError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).is_in('sds', [])
        assert str(e.exception) == 'data cannot be empty'

    def test_SqlQueryBuilder_is_in_adds_correct_clause_and_param(self):
        sqb = classes.SqlQueryBuilder(model=classes.SqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.is_in('name', ('123', '321'))
        assert len(sqb.clauses) == 1, 'is_in() must append to clauses'
        assert len(sqb.params) == 2, 'is_in() must extend params'
        assert sqb.clauses[0] == 'name in (?,?)'
        assert sqb.params[0] == '123'
        assert sqb.params[1] == '321'

    def test_SqlQueryBuilder_not_in_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).not_in(b'not a str', 'not list')
        assert str(e.exception) == 'column must be str'

        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).not_in('', 'not a list')
        assert str(e.exception) == 'data must be tuple or list'

        with self.assertRaises(ValueError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).not_in('', ['sds'])
        assert str(e.exception) == 'column cannot be empty'

        with self.assertRaises(ValueError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).not_in('sds', [])
        assert str(e.exception) == 'data cannot be empty'

    def test_SqlQueryBuilder_not_in_adds_correct_clause_and_param(self):
        sqb = classes.SqlQueryBuilder(model=classes.SqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.not_in('name', ('123', '321'))
        assert len(sqb.clauses) == 1, 'not_in() must append to clauses'
        assert len(sqb.params) == 2, 'not_in() must extend params'
        assert sqb.clauses[0] == 'name not in (?,?)'
        assert sqb.params[0] == '123'
        assert sqb.params[1] == '321'

    def test_SqlQueryBuilder_order_by_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).order_by(b'not a str', 'asc')
        assert str(e.exception) == 'column must be str'

        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).order_by('', b'not a str')
        assert str(e.exception) == 'direction must be str'

        with self.assertRaises(ValueError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).order_by('', '')
        assert str(e.exception) == 'unrecognized column'

        with self.assertRaises(ValueError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).order_by('id', 'not asc or desc')
        assert str(e.exception) == 'direction must be asc or desc'

    def test_SqlQueryBuilder_order_by_sets_order_column_and_order_dir(self):
        sqb = classes.SqlQueryBuilder(model=classes.SqlModel)
        assert sqb.order_column is None, 'order_column must initialize as None'
        assert sqb.order_dir == 'desc', 'order_dir must initialize as desc'
        sqb.order_by('name', 'asc')
        assert sqb.order_column == 'name', 'order_column must become name'
        assert sqb.order_dir == 'asc', 'order_dir must become asc'

    def test_SqlQueryBuilder_skip_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).skip('not an int')
        assert str(e.exception) == 'offset must be positive int'

        with self.assertRaises(ValueError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).skip(-1)
        assert str(e.exception) == 'offset must be positive int'

    def test_SqlQueryBuilder_skip_sets_offset(self):
        sqb = classes.SqlQueryBuilder(model=classes.SqlModel)
        assert sqb.offset is None, 'offset must initialize as None'
        assert sqb.skip(5).offset == 5, 'offset must become 5'

    def test_SqlQueryBuilder_insert_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).insert('not a dict')
        assert str(e.exception) == 'data must be dict'

        model_id = classes.SqliteModel.insert({}).data['id']

        with self.assertRaises(ValueError) as e:
            classes.SqlQueryBuilder(
                classes.SqliteModel,
                classes.SqliteContext
            ).insert({'id': model_id})
        assert str(e.exception) == 'record with this id already exists'

    def test_SqlQueryBuilder_insert_inserts_record_into_database(self):
        sqb = classes.SqlQueryBuilder(classes.SqliteModel, classes.SqliteContext)
        model_id = '32123'
        sqb.insert({'id': model_id, 'name': 'test'})

        assert sqb.find(model_id)

    def test_SqlQueryBuilder_insert_many_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).insert_many('not a list')
        assert str(e.exception) == 'items must be list[dict]'

        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).insert_many(['not a dict'])
        assert str(e.exception) == 'items must be list[dict]'

    def test_SqlQueryBuilder_take_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).take('not an int')
        assert str(e.exception) == 'limit must be positive int'

        with self.assertRaises(ValueError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).take(0)
        assert str(e.exception) == 'limit must be positive int'

    def test_SqlQueryBuilder_chunk_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            sqb = classes.SqlQueryBuilder(classes.SqliteModel, classes.SqliteContext)
            sqb.chunk('not an int')
        assert str(e.exception) == 'number must be int > 0'

        with self.assertRaises(ValueError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).chunk(0)
        assert str(e.exception) == 'number must be int > 0'

    def test_SqlQueryBuilder_update_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).update('not a dict')
        assert str(e.exception) == 'updates must be dict'

        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).update({}, 'not a dict')
        assert str(e.exception) == 'conditions must be dict'

    def test_SqlQueryBuilder_to_sql_returns_str(self):
        sqb = classes.SqlQueryBuilder(model=classes.SqlModel)
        assert type(sqb.to_sql()) is str, 'to_sql() must return str'
        assert sqb.to_sql() == ' where '

        sqb.equal('name', 'foo')
        assert sqb.to_sql() == ' where name = foo'

        sqb.order_by('id')
        assert sqb.to_sql() == ' where name = foo order by id desc'

        sqb.skip(3)
        assert sqb.to_sql() == ' where name = foo order by id desc'

        sqb.offset = None
        sqb.limit = 5
        assert sqb.to_sql() == ' where name = foo order by id desc limit 5'

        sqb.skip(3)
        assert sqb.to_sql() == ' where name = foo order by id desc limit 5 offset 3'

    def test_SqlQueryBuilder_reset_returns_fresh_instance(self):
        sqb = classes.SqlQueryBuilder(model=classes.SqlModel)
        sql1 = sqb.to_sql()
        sql2 = sqb.equal('name', 'thing').to_sql()
        assert sql1 != sql2
        assert sqb.reset().to_sql() == sql1

    def test_SqlQueryBuilder_execute_raw_raises_TypeError_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            classes.SqlQueryBuilder(classes.SqlModel).execute_raw(b'not str')
        assert str(e.exception) == 'sql must be str'

    # SqliteQueryBuilder tests
    def test_SqliteQueryBuilder_implements_QueryBuilderProtocol(self):
        assert issubclass(classes.SqliteQueryBuilder, classes.SqlQueryBuilder)

    def test_SqliteQueryBuilder_insert_inserts_record_into_datastore(self):
        # e2e test
        sqb = classes.SqliteQueryBuilder(model=classes.SqliteModel)
        assert sqb.count() == 0, 'count() must return 0'
        inserted = sqb.insert({'name': 'test1'})
        assert isinstance(inserted, sqb.model), \
            'insert() must return instance of sqb.model'
        assert inserted.id_column not in inserted.data, \
            'insert() must not assign id'
        assert sqb.count() == 1, 'count() must return 1'
        inserted = sqb.insert({'name': 'test2', 'id': '321'})
        assert sqb.find('321') is not None, \
            'find() must return a record that was inserted'

    def test_SqliteQueryBuilder_insert_many_inserts_records_into_datastore(self):
        # e2e test
        sqb = classes.SqliteQueryBuilder(model=classes.SqliteModel)
        assert sqb.count() == 0, 'count() must return 0'
        inserted = sqb.insert_many([
            {'name': 'test1', 'id': '123'},
            {'name': 'test1', 'id': '321'},
        ])
        assert type(inserted) is int, 'insert_many() must return int'
        assert inserted == 2, 'insert_many() should return 2'
        assert sqb.count() == 2, 'count() must return 2'
        inserted = sqb.insert_many([{'name': 'test3', 'id': 'abc'}])
        assert inserted == 1
        assert sqb.count() == 3, 'count() must return 3'
        assert sqb.find('321') is not None, \
            'find() must return a record that was inserted'

    def test_SqliteQueryBuilder_get_returns_all_matching_records(self):
        # e2e test
        sqb = classes.SqliteQueryBuilder(model=classes.SqliteModel)
        sqb.insert({'name': 'test1', 'id': '123'})
        sqb.insert({'name': 'test2', 'id': '321'})
        sqb.insert({'name': 'other', 'id': 'other'})

        results = sqb.get()
        assert len(results) == 3
        for result in results:
            assert result.data['id'] in ('123', '321', 'other')
            assert result.data['name'] in ('test1', 'test2', 'other')

        results = sqb.starts_with('name', 'test').get()
        assert len(results) == 2
        for result in results:
            assert result.data['id'] in ('123', '321')
            assert result.data['name'] in ('test1', 'test2')

        results = sqb.reset().excludes('name', '1').get()
        assert len(results) == 2
        for result in results:
            assert result.data['id'] in ('321', 'other')
            assert result.data['name'] in ('test2', 'other')

    def test_SqliteQueryBuilder_count_returns_correct_number(self):
        # e2e test
        sqb = classes.SqliteQueryBuilder(model=classes.SqliteModel)
        sqb.insert({'name': 'test1', 'id': '123'})
        sqb.insert({'name': 'test2', 'id': '321'})
        sqb.insert({'name': 'other', 'id': 'other'})

        assert sqb.count() == 3
        assert sqb.starts_with('name', 'test').count() == 2
        assert sqb.reset().excludes('name', '1').count() == 2
        assert sqb.reset().is_in('name', ['other']).count() == 1

    def test_SqliteQueryBuilder_skip_skips_records(self):
        # e2e test
        sqb = classes.SqliteQueryBuilder(model=classes.SqliteModel)
        sqb.insert({'name': 'test1', 'id': '123'})
        sqb.insert({'name': 'test2', 'id': '321'})
        sqb.insert({'name': 'other', 'id': 'other'})

        list1 = sqb.take(2)
        assert list1 == sqb.take(2), 'same limit/offset should return same results'
        list2 = sqb.skip(1).take(2)
        assert list1 != list2, 'different offsets should return different results'

    def test_SqliteQueryBuilder_take_limits_results(self):
        # e2e test
        sqb = classes.SqliteQueryBuilder(model=classes.SqliteModel)
        sqb.insert({'name': 'test1', 'id': '123'})
        sqb.insert({'name': 'test2', 'id': '321'})
        sqb.insert({'name': 'other', 'id': 'other'})

        assert sqb.count() == 3
        assert len(sqb.take(1)) == 1
        assert len(sqb.take(2)) == 2
        assert len(sqb.take(3)) == 3
        assert len(sqb.take(5)) == 3

    def test_SqliteQueryBuilder_chunk_returns_generator_that_yields_list_of_SqliteModel(self):
        # e2e test
        sqb = classes.SqliteQueryBuilder(model=classes.SqliteModel)
        dicts = [{'name': i, 'id': i} for i in range(0, 25)]
        expected = [i for i in range(0, 25)]
        observed = []
        sqb.insert_many(dicts)

        assert sqb.count() == 25
        assert isinstance(sqb.chunk(10), GeneratorType), 'chunk must return generator'
        for results in sqb.chunk(10):
            assert type(results) is list
            for record in results:
                assert isinstance(record, classes.SqliteModel)
                observed.append(int(record.data['id']))
        assert observed == expected

    def test_SqliteQueryBuilder_first_returns_one_record(self):
        # e2e test
        sqb = classes.SqliteQueryBuilder(model=classes.SqliteModel)
        inserted = sqb.insert({'name': 'test1', 'id': '123'})
        sqb.insert({'name': 'test2', 'id': '321'})
        first = sqb.first()
        assert isinstance(first, sqb.model), 'first() must return instance of sqb.model'
        first = sqb.order_by('id', 'asc').first()
        assert first == inserted, 'first() must return correct instance'

    def test_SqliteQueryBuilder_update_changes_record(self):
        # e2e test
        sqb = classes.SqliteQueryBuilder(model=classes.SqliteModel)
        sqb.insert({'name': 'test1', 'id': '123'})
        assert sqb.find('123').data['name'] == 'test1'
        updates = sqb.update({'name': 'test2'}, {'id': '123'})
        assert type(updates) is int
        assert updates == 1
        assert sqb.find('123').data['name'] == 'test2'

    def test_SqliteQueryBuilder_delete_removes_record(self):
        # e2e test
        sqb = classes.SqliteQueryBuilder(model=classes.SqliteModel)
        sqb.insert({'name': 'test1', 'id': '123'})
        assert sqb.find('123') is not None
        deleted = sqb.equal('id', '123').delete()
        assert type(deleted) is int
        assert deleted == 1
        assert sqb.reset().find('123') is None

    def test_SqliteQueryBuilder_execute_raw_executes_raw_SQL(self):
        # e2e test
        sqb = classes.SqliteQueryBuilder(model=classes.SqliteModel)
        assert sqb.count() == 0, 'count() must return 0'
        result = sqb.execute_raw("insert into example (id, name) values ('123', '321')")
        assert type(result) is tuple, 'execute_raw must return tuple'
        assert result[0] == 1, 'execute_raw returns wrong rowcount'
        result = sqb.execute_raw("insert into example (id, name) values ('321', '123'), ('abc', 'cba')")
        assert result[0] == 2, 'execute_raw returns wrong rowcount'
        assert sqb.count() == 3, 'count() must return 3'

        result = sqb.execute_raw("select * from example")
        assert type(result) is tuple, 'execute_raw must return tuple'
        assert len(result[1]) == 3, 'execute_raw did not return all rows'

    def test_SqliteQueryBuilder_join_returns_JoinedModel(self):
        model1 = classes.SqliteModel.insert({"name": "model 1"})
        model2 = classes.Attachment({"details": "attachment 1"})
        model2.attach_to(model1)
        model2 = model2.save()

        query = classes.SqliteModel.query()
        query.join(classes.Attachment, ["id", "related_id"], "inner")
        result = query.get()
        assert type(result) is list
        assert len(result) == 1
        result = result[0]
        assert isinstance(result, interfaces.JoinedModelProtocol)
        result
        assert model1.table in result.data and model2.table in result.data
        assert model1.data == result.data[model1.table]
        assert model2.data == result.data[model2.table]

    def test_SqliteQueryBuilder_select_restrains_columns_selected(self):
        # without a join
        names = ['model1', 'model2']
        models = [classes.SqliteModel.insert({"name": name}) for name in names]
        results = classes.SqliteModel.query().select(["id"]).get()
        assert type(results) is list
        assert len(results) == 2
        assert all(["id" in r.data for r in results])
        assert all(["name" not in r.data for r in results])

        # with a join
        for model in models:
            attachment = classes.Attachment({"details": f"test for {model.data['name']}"})
            attachment.attach_to(model).save()
        sqb = classes.SqliteModel.query()
        sqb.join(classes.Attachment, ["id", "related_id"])
        sqb.select(["example.name", "attachments.id"])
        results = sqb.get()
        assert type(results) is list
        assert len(results) == 2
        assert all(["example" in r.data and "attachments" in r.data for r in results])
        assert all([list(dict.keys(r.data["example"])) == ["name"] for r in results])
        assert all([list(dict.keys(r.data["attachments"])) == ["id"] for r in results])

    def test_SqliteQueryBuilder_group_groups_results(self):
        names = ['model1', 'model2']
        models = [classes.SqliteModel.insert({"name": name}) for name in names]
        for model in models:
            for i in range(5):
                attachment = classes.Attachment({"details": f"test data {i}"})
                attachment.attach_to(model).save()
        sqb = classes.Attachment.query().group("related_id")
        sqb.select(["count(*)", "related_id"])
        results = sqb.get()
        assert type(results) is list
        assert all([isinstance(r, interfaces.RowProtocol) for r in results])
        assert all([list(dict.keys(r.data)) == ["count(*)", "related_id"] for r in results])


    # HashedModel tests
    def test_HashedModel_issubclass_of_SqlModel(self):
        assert issubclass(classes.HashedModel, classes.SqlModel)

    def test_HashedModel_generated_id_is_sha256_of_packified_data(self):
        data = { 'details': token_bytes(8).hex() }
        observed = classes.HashedModel.generate_id(data)
        preimage = packify.pack(data)
        expected = sha256(preimage).digest().hex()
        assert observed == expected, 'wrong hash encountered'

    def test_HashedModel_insert_raises_TypeError_for_nondict_input(self):
        with self.assertRaises(TypeError) as e:
            classes.HashedModel.insert('not a dict')
        assert str(e.exception) == 'data must be dict'

    def test_HashedModel_insert_generates_id_and_makes_record(self):
        data = { 'details': token_bytes(8).hex() }
        inserted = classes.HashedModel.insert(data)
        assert isinstance(inserted, classes.HashedModel)
        assert 'details' in inserted.data
        assert inserted.data['details'] == data['details']
        assert classes.HashedModel.id_column in inserted.data
        assert type(inserted.data[classes.HashedModel.id_column]) == str
        assert len(inserted.data[classes.HashedModel.id_column]) == 64
        assert len(bytes.fromhex(inserted.data[classes.HashedModel.id_column])) == 32

        found = classes.HashedModel.find(inserted.data[classes.HashedModel.id_column])
        assert isinstance(found, classes.HashedModel)
        assert found == inserted

    def test_HashedModel_insert_many_raises_TypeError_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            classes.HashedModel.insert_many('not a list')
        assert str(e.exception) == 'items must be type list[dict]'

        with self.assertRaises(TypeError) as e:
            classes.HashedModel.insert_many(['not a dict'])
        assert str(e.exception) == 'items must be type list[dict]'

    def test_HashedModel_insert_many_generates_ids_and_makes_records(self):
        data1 = { 'details': token_bytes(8).hex() }
        data2 = { 'details': token_bytes(8).hex() }
        inserted = classes.HashedModel.insert_many([data1, data2])
        assert type(inserted) == int
        assert inserted == 2

        items = classes.HashedModel.query().get()
        assert type(items) is list
        assert len(items) == 2
        for item in items:
            assert item.data['details'] in (data1['details'], data2['details'])
            assert classes.HashedModel.id_column in item.data
            assert type(item.data[classes.HashedModel.id_column]) == str
            assert len(item.data[classes.HashedModel.id_column]) == 64
            assert len(bytes.fromhex(item.data[classes.HashedModel.id_column])) == 32

    def test_HashedModel_update_raises_errors_for_invalid_input(self):
        with self.assertRaises(TypeError) as e:
            classes.HashedModel({}).update('not a dict')
        assert str(e.exception) == 'updates must be dict'

        with self.assertRaises(ValueError) as e:
            classes.HashedModel({}).update({'badcolumn': '123'})
        assert str(e.exception) == 'unrecognized column: badcolumn'

    def test_HashedModel_save_and_update_delete_original_and_makes_new_record(self):
        data1 = { 'details': token_bytes(8).hex() }
        data2 = { 'details': token_bytes(8).hex() }
        data3 = { 'details': token_bytes(8).hex() }

        inserted = classes.HashedModel.insert(data1)
        id1 = inserted.data['id']
        assert classes.DeletedModel.query().count() == 0

        updated = inserted.update(data2)
        assert classes.DeletedModel.query().count() == 1
        assert updated.data['id'] != id1

        updated.data['details'] = data3['details']
        saved = updated.save()
        assert classes.DeletedModel.query().count() == 2
        assert saved.data['id'] not in (id1, updated.data['id'])


    # DeletedModel tests
    def test_DeletedModel_issubclass_of_SqlModel(self):
        assert issubclass(classes.DeletedModel, classes.SqlModel)

    def test_DeletedModel_created_when_HashedModel_is_deleted(self):
        item = classes.HashedModel.insert({'data': '123'})
        deleted = item.delete()
        assert isinstance(deleted, classes.DeletedModel)
        assert type(deleted.data[deleted.id_column]) is str
        assert classes.DeletedModel.find(deleted.data[deleted.id_column]) != None

    def test_DeletedModel_restore_returns_SqlModel_and_deleted_records_row(self):
        item = classes.HashedModel.insert({'data': '123'})

        deleted = item.delete()
        assert classes.DeletedModel.find(deleted.data[deleted.id_column]) is not None
        assert classes.HashedModel.find(item.data[item.id_column]) is None

        restored = deleted.restore()
        assert isinstance(restored, classes.SqlModel)
        assert classes.DeletedModel.find(deleted.data[deleted.id_column]) is None
        assert classes.HashedModel.find(restored.data[restored.id_column]) is not None

    def test_DeletedModel_restore_raises_errors_for_invalid_target_record(self):
        class NotValidClass:
            ...

        classes.NotValidClass = NotValidClass

        deleted = classes.DeletedModel.query().insert({
            'id': classes.DeletedModel.generate_id(),
            'model_class': 'sdskdj',
            'record_id': 'dsdisjd',
            'record': 'codework'
        })

        with self.assertRaises(ValueError) as e:
            deleted.restore()
        assert str(e.exception) == 'model_class must be accessible'

        deleted = classes.DeletedModel.query().insert({
            'id': classes.DeletedModel.generate_id(),
            'model_class': NotValidClass.__name__,
            'record_id': 'dsdisjd',
            'record': '{"January": "is a decent song"}'
        })

        with self.assertRaises(TypeError) as e:
            deleted.restore()
        assert str(e.exception) == 'related_model must inherit from SqlModel'


    # Attachment tests
    def test_Attachment_issubclass_of_HashedModel(self):
        assert issubclass(classes.Attachment, classes.HashedModel)

    def test_Attachment_attach_to_raises_TypeError_for_invalid_input(self):
        class NotValidClass:
            ...

        with self.assertRaises(TypeError) as e:
            classes.Attachment({'details': 'should fail'}).attach_to(NotValidClass())
        assert str(e.exception) == 'related must inherit from SqlModel'

    def test_Attachment_attach_to_sets_related_model_and_related_id(self):
        data = { 'data': token_bytes(8).hex() }
        hashedmodel = classes.HashedModel.insert(data)
        attachment = classes.Attachment()
        attachment.attach_to(hashedmodel)

        assert 'related_model' in attachment.data
        assert attachment.data['related_model'] == hashedmodel.__class__.__name__
        assert 'related_id' in attachment.data
        assert attachment.data['related_id'] == hashedmodel.data['id']

    def test_Attachment_set_details_packs_and_details_unpacks(self):
        details = {'123': 'some information'}
        attachment = classes.Attachment()

        assert 'details' not in attachment.data

        attachment.set_details(details)
        assert 'details' in attachment.data
        assert type(attachment.data['details']) is bytes

        assert type(attachment.get_details()) is dict
        assert attachment.get_details(True) == details

    def test_Attachment_related_raises_TypeError_for_invalid_related_model(self):
        class NotValidClass:
            ...

        classes.NotValidClass = NotValidClass

        attachment = classes.Attachment.insert({
            'related_model': 'not even a real class name',
            'related_id': '321',
            'details': 'chill music is nice to listen to while coding'
        })
        with self.assertRaises(ValueError) as e:
            attachment.related()
        assert str(e.exception) == 'model_class must be accessible'

        attachment = classes.Attachment.insert({
            'related_model': NotValidClass.__name__,
            'related_id': '321',
            'details': 'fail whale incoming'
        })
        with self.assertRaises(TypeError) as e:
            attachment.related()
        assert str(e.exception) == 'related_model must inherit from SqlModel'

    def test_Attachment_related_returns_SqlModel_instance(self):
        data = { 'data': token_bytes(8).hex() }
        hashedmodel = classes.HashedModel.insert(data)
        details = {'123': 'some information'}
        attachment = classes.Attachment({'details': packify.pack(details)})
        attachment.attach_to(hashedmodel)
        attachment.save()

        related = attachment.related(True)
        assert isinstance(related, classes.SqlModel)


    # tests for HashedSqliteModel, DeletedSqliteModel, and AttachmentSqlite
    def test_HashedSqliteModel_etc(self):
        assert issubclass(classes.HashedSqliteModel, classes.SqliteModel)
        hm = classes.HashedSqliteModel.insert({'details': '123'})
        assert classes.AttachmentSqlite.query().count() == 0
        am = classes.AttachmentSqlite({'details': '321'})
        am.attach_to(hm).save()
        assert classes.AttachmentSqlite.query().count() == 1
        assert classes.DeletedSqliteModel.query().count() == 0
        dm = hm.delete()
        assert classes.DeletedSqliteModel.query().count() == 1
        assert classes.HashedSqliteModel.query().count() == 0
        restored: classes.HashedSqliteModel = dm.restore()
        assert classes.HashedSqliteModel.query().count() == 1
        assert type(restored) is type(hm)
        assert restored.id == hm.id
        assert type(am.id) is str


if __name__ == '__main__':
    unittest.main()
