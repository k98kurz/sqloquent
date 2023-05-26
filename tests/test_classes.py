from secrets import token_bytes
from context import classes, interfaces
from genericpath import isfile
from hashlib import sha256
from types import GeneratorType
import json
import os
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
            'model_class text not null, record_id text not null, record text not null)')

        return super().setUp()

    def setUpClass() -> None:
        """Couple these models to sqlite for testing purposes."""
        class DeletedModel(classes.DeletedModel, classes.SqliteModel):
            file_path = TestClasses.db_filepath
        classes.DeletedModel = DeletedModel

        # save uncoupled original for subclass checking
        class HashedModel(classes.HashedModel, classes.SqliteModel):
            file_path = TestClasses.db_filepath
        classes.HashedModel_original = classes.HashedModel
        classes.HashedModel = HashedModel

        class Attachment(classes.Attachment, classes.SqliteModel):
            file_path = TestClasses.db_filepath
        classes.Attachment = Attachment

    def tearDown(self) -> None:
        """Close cursor and delete test database."""
        self.cursor.close()
        self.db.close()
        os.remove(self.db_filepath)
        return super().tearDown()

    # general tests
    def test_imports_without_errors(self):
        assert True

    def test_classes_contains_correct_classes(self):
        assert hasattr(classes, 'SqlQueryBuilder')
        assert type(classes.SqlQueryBuilder) is type
        assert hasattr(classes, 'SqliteQueryBuilder')
        assert type(classes.SqliteQueryBuilder) is type
        assert hasattr(classes, 'SqlModel')
        assert type(classes.SqlModel) is type
        assert hasattr(classes, 'SqliteModel')
        assert type(classes.SqliteModel) is type
        assert hasattr(classes, 'DeletedModel')
        assert type(classes.DeletedModel) is type
        assert hasattr(classes, 'HashedModel')
        assert type(classes.HashedModel) is type
        assert hasattr(classes, 'Attachment')
        assert type(classes.Attachment) is type


    # context manager test
    def test_SqliteContext_implements_DBContextProtocol(self):
        assert issubclass(classes.SqliteContext, interfaces.DBContextProtocol)


    # SqlModel tests
    def test_SqlModel_implements_ModelProtocol(self):
        assert isinstance(classes.SqlModel(), interfaces.ModelProtocol)


    # SqliteModel tests
    def test_SqliteModel_implements_ModelProtocol(self):
        assert isinstance(classes.SqliteModel(), interfaces.ModelProtocol)

    def test_SqliteModel_extends_SqlModel(self):
        assert issubclass(classes.SqliteModel, classes.SqlModel)

    def test_SqliteModel_insert_and_find(self):
        # setup
        self.cursor.execute('create table example (id text, name text)')
        classes.SqliteModel.file_path = self.db_filepath

        # e2e test
        inserted = classes.SqliteModel.insert({'name': 'test1'})
        assert isinstance(inserted, classes.SqliteModel), \
            'insert() must return SqliteModel instance'
        assert classes.SqliteModel.id_field in inserted.data, \
            'insert() return value must have id'

        found = classes.SqliteModel.find(inserted.data[classes.SqliteModel.id_field])
        assert isinstance(found, classes.SqliteModel), \
            'find() must return SqliteModel instance'

        assert inserted == found, \
            'inserted must equal found'

    def test_SqliteModel_update_save_and_delete(self):
        # setup
        self.cursor.execute('create table example (id text, name text)')
        classes.SqliteModel.file_path = self.db_filepath

        # e2e test
        inserted = classes.SqliteModel.insert({'name': 'test1'})
        updated = inserted.update({'name': 'test2'})
        assert isinstance(updated, classes.SqliteModel), \
            'update() must return SqliteModel instance'
        assert updated.data['name'] == 'test2', 'value must be updated'
        assert updated == inserted, 'must be equal'
        found = classes.SqliteModel.find(inserted.data[inserted.id_field])
        assert updated == found, 'must be equal'

        updated.data['name'] = 'test3'
        saved = updated.save()
        assert isinstance(saved, classes.SqliteModel), \
            'save() must return SqliteModel instance'
        assert saved == updated, 'must be equal'
        found = classes.SqliteModel.find(inserted.data[inserted.id_field])
        assert saved == found, 'must be equal'

        updated.delete()
        found = classes.SqliteModel.find(inserted.data[inserted.id_field])
        assert found is None, 'found must be None'

    def test_SqliteModel_insert_many_and_count(self):
        # setup
        self.cursor.execute('create table example (id text, name text)')
        classes.SqliteModel.file_path = self.db_filepath

        # e2e test
        inserted = classes.SqliteModel.insert_many([
            {'name': 'test1'},
            {'name': 'test2'},
        ])
        assert type(inserted) is int, 'insert_many() must return int'
        assert inserted == 2, 'insert_many() should return 2'

        found = classes.SqliteModel.query().count()
        assert found == 2


    # SqlQueryBuilder tests
    def test_SqlQueryBuilder_implements_QueryBuilderProtocol(self):
        assert isinstance(classes.SqlQueryBuilder, interfaces.QueryBuilderProtocol)

    def test_SqlQueryBuilder_rejects_invalid_model(self):
        with self.assertRaises(AssertionError) as e:
            sqb = classes.SqlQueryBuilder(model=dict)
        assert isinstance(e.exception, AssertionError)
        assert str(e.exception) == 'model must be SqlModel subclass'

    def test_SqlQueryBuilder_equal_adds_correct_clause_and_param(self):
        sqb = classes.SqlQueryBuilder(model=classes.SqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.equal('name', 'test')
        assert len(sqb.clauses) == 1, 'equal() must append to clauses'
        assert len(sqb.params) == 1, 'equal() must append to params'
        assert sqb.clauses[0] == 'name = ?'
        assert sqb.params[0] == 'test'

    def test_SqlQueryBuilder_not_equal_adds_correct_clause_and_param(self):
        sqb = classes.SqlQueryBuilder(model=classes.SqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.not_equal('name', 'test')
        assert len(sqb.clauses) == 1, 'not_equal() must append to clauses'
        assert len(sqb.params) == 1, 'not_equal() must append to params'
        assert sqb.clauses[0] == 'name != ?'
        assert sqb.params[0] == 'test'

    def test_SqlQueryBuilder_less_adds_correct_clause_and_param(self):
        sqb = classes.SqlQueryBuilder(model=classes.SqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.less('name', '123')
        assert len(sqb.clauses) == 1, 'less() must append to clauses'
        assert len(sqb.params) == 1, 'less() must append to params'
        assert sqb.clauses[0] == 'name < ?'
        assert sqb.params[0] == '123'

    def test_SqlQueryBuilder_greater_adds_correct_clause_and_param(self):
        sqb = classes.SqlQueryBuilder(model=classes.SqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.greater('name', '123')
        assert len(sqb.clauses) == 1, 'greater() must append to clauses'
        assert len(sqb.params) == 1, 'greater() must append to params'
        assert sqb.clauses[0] == 'name > ?'
        assert sqb.params[0] == '123'

    def test_SqlQueryBuilder_starts_with_adds_correct_clause_and_param(self):
        sqb = classes.SqlQueryBuilder(model=classes.SqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.starts_with('name', '123')
        assert len(sqb.clauses) == 1, 'starts_with() must append to clauses'
        assert len(sqb.params) == 1, 'starts_with() must append to params'
        assert sqb.clauses[0] == 'name like ?'
        assert sqb.params[0] == '123%'

    def test_SqlQueryBuilder_contains_adds_correct_clause_and_param(self):
        sqb = classes.SqlQueryBuilder(model=classes.SqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.contains('name', '123')
        assert len(sqb.clauses) == 1, 'contains() must append to clauses'
        assert len(sqb.params) == 1, 'contains() must append to params'
        assert sqb.clauses[0] == 'name like ?'
        assert sqb.params[0] == '%123%'

    def test_SqlQueryBuilder_excludes_adds_correct_clause_and_param(self):
        sqb = classes.SqlQueryBuilder(model=classes.SqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.excludes('name', '123')
        assert len(sqb.clauses) == 1, 'excludes() must append to clauses'
        assert len(sqb.params) == 1, 'excludes() must append to params'
        assert sqb.clauses[0] == 'name not like ?'
        assert sqb.params[0] == '%123%'

    def test_SqlQueryBuilder_ends_with_adds_correct_clause_and_param(self):
        sqb = classes.SqlQueryBuilder(model=classes.SqlModel)
        assert len(sqb.clauses) == 0, 'clauses must start at 0 len'
        assert len(sqb.params) == 0, 'params must start at 0 len'
        sqb.ends_with('name', '123')
        assert len(sqb.clauses) == 1, 'ends_with() must append to clauses'
        assert len(sqb.params) == 1, 'ends_with() must append to params'
        assert sqb.clauses[0] == 'name like ?'
        assert sqb.params[0] == '%123'

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

    def test_SqlQueryBuilder_order_by_sets_order_field_and_order_dir(self):
        sqb = classes.SqlQueryBuilder(model=classes.SqlModel)
        assert sqb.order_field is None, 'order_field must initialize as None'
        assert sqb.order_dir == 'desc', 'order_dir must initialize as desc'
        sqb.order_by('name', 'asc')
        assert sqb.order_field == 'name', 'order_field must become name'
        assert sqb.order_dir == 'asc', 'order_dir must become asc'

    def test_SqlQueryBuilder_skip_sets_offset(self):
        sqb = classes.SqlQueryBuilder(model=classes.SqlModel)
        assert sqb.offset is None, 'offset must initialize as None'
        assert sqb.skip(5).offset == 5, 'offset must become 5'

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


    # SqliteQueryBuilder tests
    def test_SqliteQueryBuilder_implements_QueryBuilderProtocol(self):
        assert issubclass(classes.SqliteQueryBuilder, classes.SqlQueryBuilder)

    def test_SqliteQueryBuilder_insert_inserts_record_into_datastore(self):
        # setup
        self.cursor.execute('create table example (id text, name text)')
        classes.SqliteModel.file_path = self.db_filepath

        # e2e test
        sqb = classes.SqliteQueryBuilder(model=classes.SqliteModel)
        assert sqb.count() == 0, 'count() must return 0'
        inserted = sqb.insert({'name': 'test1'})
        assert isinstance(inserted, sqb.model), \
            'insert() must return instance of sqb.model'
        assert inserted.id_field not in inserted.data, \
            'insert() must not assign id'
        assert sqb.count() == 1, 'count() must return 1'
        inserted = sqb.insert({'name': 'test2', 'id': '321'})
        assert sqb.find('321') is not None, \
            'find() must return a record that was inserted'

    def test_SqliteQueryBuilder_insert_many_inserts_records_into_datastore(self):
        # setup
        self.cursor.execute('create table example (id text, name text)')
        classes.SqliteModel.file_path = self.db_filepath

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
        # setup
        self.cursor.execute('create table example (id text, name text)')
        classes.SqliteModel.file_path = self.db_filepath

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
        # setup
        self.cursor.execute('create table example (id text, name text)')
        classes.SqliteModel.file_path = self.db_filepath

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
        # setup
        self.cursor.execute('create table example (id text, name text)')
        classes.SqliteModel.file_path = self.db_filepath

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
        # setup
        self.cursor.execute('create table example (id text, name text)')
        classes.SqliteModel.file_path = self.db_filepath

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
        # setup
        self.cursor.execute('create table example (id text, name text)')
        classes.SqliteModel.file_path = self.db_filepath

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
        # setup
        self.cursor.execute('create table example (id text, name text)')
        classes.SqliteModel.file_path = self.db_filepath

        # e2e test
        sqb = classes.SqliteQueryBuilder(model=classes.SqliteModel)
        inserted = sqb.insert({'name': 'test1', 'id': '123'})
        sqb.insert({'name': 'test2', 'id': '321'})
        first = sqb.first()
        assert isinstance(first, sqb.model), 'first() must return instance of sqb.model'
        first = sqb.order_by('id', 'asc').first()
        assert first == inserted, 'first() must return correct instance'

    def test_SqliteQueryBuilder_update_changes_record(self):
        # setup
        self.cursor.execute('create table example (id text, name text)')
        classes.SqliteModel.file_path = self.db_filepath

        # e2e test
        sqb = classes.SqliteQueryBuilder(model=classes.SqliteModel)
        sqb.insert({'name': 'test1', 'id': '123'})
        assert sqb.find('123').data['name'] == 'test1'
        updates = sqb.update({'name': 'test2'}, {'id': '123'})
        assert type(updates) is int
        assert updates == 1
        assert sqb.find('123').data['name'] == 'test2'

    def test_SqliteQueryBuilder_delete_removes_record(self):
        # setup
        self.cursor.execute('create table example (id text, name text)')
        classes.SqliteModel.file_path = self.db_filepath

        # e2e test
        sqb = classes.SqliteQueryBuilder(model=classes.SqliteModel)
        sqb.insert({'name': 'test1', 'id': '123'})
        assert sqb.find('123') is not None
        deleted = sqb.equal('id', '123').delete()
        assert type(deleted) is int
        assert deleted == 1
        assert sqb.reset().find('123') is None

    def test_SqliteQueryBuilder_execute_raw_executes_raw_SQL(self):
        # setup
        self.cursor.execute('create table example (id text, name text)')
        classes.SqliteModel.file_path = self.db_filepath

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


    # HashedModel tests
    def test_HashedModel_issubclass_of_SqlModel(self):
        assert issubclass(classes.HashedModel, classes.SqlModel)

    def test_HashedModel_generated_id_is_sha256_of_json_data(self):
        self.cursor.execute('create table hashed_records (id text, data text)')
        data = { 'data': token_bytes(8).hex() }
        observed = classes.HashedModel.generate_id(data)
        preimage = json.dumps(
            classes.HashedModel.encode_value(data),
            sort_keys=True
        )
        expected = sha256(bytes(preimage, 'utf-8')).digest().hex()
        assert observed == expected, 'wrong hash encountered'

    def test_HashedModel_insert_generates_id_and_makes_record(self):
        self.cursor.execute('create table hashed_records (id text, data text)')
        data = { 'data': token_bytes(8).hex() }
        inserted = classes.HashedModel.insert(data)
        assert isinstance(inserted, classes.HashedModel)
        assert 'data' in inserted.data
        assert inserted.data['data'] == data['data']
        assert classes.HashedModel.id_field in inserted.data
        assert type(inserted.data[classes.HashedModel.id_field]) == str
        assert len(inserted.data[classes.HashedModel.id_field]) == 64
        assert len(bytes.fromhex(inserted.data[classes.HashedModel.id_field])) == 32

        found = classes.HashedModel.find(inserted.data[classes.HashedModel.id_field])
        assert isinstance(found, classes.HashedModel)
        assert found == inserted

    def test_HashedModel_insert_many_generates_ids_and_makes_records(self):
        self.cursor.execute('create table hashed_records (id text, data text)')
        data1 = { 'data': token_bytes(8).hex() }
        data2 = { 'data': token_bytes(8).hex() }
        inserted = classes.HashedModel.insert_many([data1, data2])
        assert type(inserted) == int
        assert inserted == 2

        items = classes.HashedModel.query().get()
        assert type(items) is list
        assert len(items) == 2
        for item in items:
            assert item.data['data'] in (data1['data'], data2['data'])
            assert classes.HashedModel.id_field in item.data
            assert type(item.data[classes.HashedModel.id_field]) == str
            assert len(item.data[classes.HashedModel.id_field]) == 64
            assert len(bytes.fromhex(item.data[classes.HashedModel.id_field])) == 32

    def test_HashedModel_save_and_update_delete_original_and_makes_new_record(self):
        self.cursor.execute('create table hashed_records (id text, data text)')
        data1 = { 'data': token_bytes(8).hex() }
        data2 = { 'data': token_bytes(8).hex() }
        data3 = { 'data': token_bytes(8).hex() }

        inserted = classes.HashedModel.insert(data1)
        id1 = inserted.data['id']
        assert classes.DeletedModel.query().count() == 0

        updated = inserted.update(data2)
        assert classes.DeletedModel.query().count() == 1
        assert updated.data['id'] != id1

        updated.data['data'] = data3['data']
        saved = updated.save()
        assert classes.DeletedModel.query().count() == 2
        assert saved.data['id'] not in (id1, updated.data['id'])


    # DeletedModel tests
    def test_DeletedModel_issubclass_of_SqlModel(self):
        assert issubclass(classes.DeletedModel, classes.SqlModel)

    def test_DeletedModel_created_when_HashedModel_is_deleted(self):
        self.cursor.execute('create table hashed_records (id text, data text)')
        item = classes.HashedModel.insert({'data': '123'})
        deleted = item.delete()
        assert isinstance(deleted, classes.DeletedModel)
        assert type(deleted.data[deleted.id_field]) is str
        assert classes.DeletedModel.find(deleted.data[deleted.id_field]) != None

    def test_DeletedModel_restore_returns_SqlModel_and_deleted_records_row(self):
        self.cursor.execute('create table hashed_records (id text, data text)')
        item = classes.HashedModel.insert({'data': '123'})

        deleted = item.delete()
        assert classes.DeletedModel.find(deleted.data[deleted.id_field]) is not None
        assert classes.HashedModel.find(item.data[item.id_field]) is None

        restored = deleted.restore()
        assert isinstance(restored, classes.SqlModel)
        assert classes.DeletedModel.find(deleted.data[deleted.id_field]) is None
        assert classes.HashedModel.find(restored.data[restored.id_field]) is not None


    # Attachment tests
    def test_Attachment_issubclass_of_HashedModel(self):
        assert issubclass(classes.Attachment, classes.HashedModel_original)

    def test_Attachment_attach_to_sets_related_model_and_related_id(self):
        self.cursor.execute('create table hashed_records (id text, data text)')
        data = { 'data': token_bytes(8).hex() }
        hashedmodel = classes.HashedModel.insert(data)
        attachment = classes.Attachment()
        attachment.attach_to(hashedmodel)

        assert 'related_model' in attachment.data
        assert attachment.data['related_model'] == hashedmodel.__class__.__name__
        assert 'related_id' in attachment.data
        assert attachment.data['related_id'] == hashedmodel.data['id']

    def test_Attachment_set_details_encodes_json_and_details_decodes_json(self):
        details = {'123': 'some information'}
        attachment = classes.Attachment()

        assert 'details' not in attachment.data

        attachment.set_details(details)
        assert 'details' in attachment.data
        assert type(attachment.data['details']) is str

        assert type(attachment.details()) is dict
        assert attachment.details(True) == details

    def test_Attachment_related_returns_SqlModel_instance(self):
        self.cursor.execute('create table hashed_records (id text, data text)')
        self.cursor.execute('create table attachments (id text, ' +
            'related_model text, related_id text, details text)')
        data = { 'data': token_bytes(8).hex() }
        hashedmodel = classes.HashedModel.insert(data)
        details = {'123': 'some information'}
        attachment = classes.Attachment({'details': json.dumps(details)})
        attachment.attach_to(hashedmodel)
        attachment.save()

        related = attachment.related(True)
        assert isinstance(related, classes.SqlModel)


if __name__ == '__main__':
    unittest.main()
