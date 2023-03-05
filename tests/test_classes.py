from secrets import token_bytes
from context import classes, interfaces
from genericpath import isfile
from hashlib import sha256
import json
import os
import sqlite3
import unittest


class TestClasses(unittest.TestCase):
    db_filepath: str = 'test.db'
    db: sqlite3.Connection = None
    cursor: sqlite3.Cursor = None

    def setUp(self) -> None:
        try:
            if isfile(self.db_filepath):
                os.remove(self.db_filepath)
        except:
            ...
        self.db = sqlite3.connect(self.db_filepath)
        self.cursor = self.db.cursor()
        # self.cursor.execute('create table deleted_records (id text not null, ' +
        #     'model_class text not null, record_id text not null, record text not null)')
        # classes.DeletedModel.file_path = self.db_filepath
        return super().setUp()

    def tearDown(self) -> None:
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
        # assert hasattr(classes, 'DeletedModel')
        # assert type(classes.DeletedModel) is type
        # assert hasattr(classes, 'HashedModel')
        # assert type(classes.HashedModel) is type
        # assert hasattr(classes, 'Attachment')
        # assert type(classes.Attachment) is type


    # context manager test
    def test_SqliteContext_implements_DBContextProtocol(self):
        assert issubclass(classes.SqliteContext, interfaces.DBContextProtocol)


    # SqlModel tests
    def test_SqlModel_implements_ModelProtocol(self):
        assert issubclass(classes.SqlModel, interfaces.ModelProtocol)


    # SqliteModel tests
    def test_SqliteModel_implements_ModelProtocol(self):
        assert issubclass(classes.SqliteModel, interfaces.ModelProtocol)

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
        assert classes.SqliteModel.id_column in inserted.data, \
            'insert() return value must have id'

        found = classes.SqliteModel.find(inserted.data[classes.SqliteModel.id_column])
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

    def test_SqlQueryBuilder_to_sql_returns_str(self):
        sqb = classes.SqlQueryBuilder(model=classes.SqlModel)
        assert type(sqb.to_sql()) is str, 'to_sql() must return str'
        assert sqb.to_sql() == ' where '

        sqb.equal('name', 'foo')
        assert sqb.to_sql() == ' where name = foo'

        sqb.order_by('id')
        assert sqb.to_sql() == ' where name = foo order by id desc'

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
        assert inserted.id_column not in inserted.data, \
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


if __name__ == '__main__':
    unittest.main()
