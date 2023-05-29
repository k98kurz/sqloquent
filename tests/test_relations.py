from context import classes, relations
from genericpath import isfile
import os
import sqlite3
import unittest


DB_FILEPATH = 'test.db'


class Pivot(classes.SqliteModel):
    file_path: str = DB_FILEPATH
    table: str = 'pivot'
    fields: tuple = ('id', 'first_id', 'second_id')


class TestRelations(unittest.TestCase):
    db_filepath: str = DB_FILEPATH
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
        self.cursor.execute('create table hashed_records (id text, data text)')
        self.cursor.execute('create table attachments (id text, ' +
            'related_model text, related_id text, details text)')
        self.cursor.execute('create table pivot (id text, first_id text, second_id text)')
        self.cursor.execute('create table owners (id text, data text)')
        self.cursor.execute('create table owned (id text, owner_id text, data text)')

        # rebuild test classes because properties will be changed in tests
        class OwnedModel(classes.SqliteModel):
            file_path: str = DB_FILEPATH
            table: str = 'owned'
            fields: tuple = ('id', 'owner_id', 'data')

        class OwnerModel(classes.SqliteModel):
            file_path: str = DB_FILEPATH
            table: str = 'owners'
            fields: tuple = ('id', 'data')

        self.OwnedModel = OwnedModel
        self.OwnerModel = OwnerModel

        return super().setUp()

    def setUpClass() -> None:
        """Couple these models to sqlite for testing purposes."""
        class DeletedModel(classes.DeletedModel, classes.SqliteModel):
            file_path = TestRelations.db_filepath
        classes.DeletedModel = DeletedModel

        # save uncoupled original for subclass checking
        class HashedModel(classes.HashedModel, classes.SqliteModel):
            file_path = TestRelations.db_filepath
        classes.HashedModel = HashedModel

        class Attachment(classes.Attachment, classes.SqliteModel):
            file_path = TestRelations.db_filepath
        classes.Attachment = Attachment

    def tearDown(self) -> None:
        """Close cursor and delete test database."""
        self.cursor.close()
        self.db.close()
        os.remove(self.db_filepath)
        return super().tearDown()

    # Relation tests
    def test_Relation_initializes_properly(self):
        primary = classes.HashedModel.insert({'data': '1234'})
        secondary = classes.Attachment().attach_to(primary).save()
        relation = relations.Relation(
            primary_class=classes.HashedModel,
            secondary_class=classes.Attachment,
            primary=primary,
            secondary=secondary
        )
        assert type(relation) is relations.Relation

        relation = relations.Relation(
            primary_class=classes.HashedModel,
            secondary_class=classes.Attachment
        )
        assert type(relation) is relations.Relation

    def test_Relation_precondition_check_methods_raise_errors(self):
        relation = relations.Relation(
            primary_class=classes.HashedModel,
            secondary_class=classes.Attachment
        )

        with self.assertRaises(AssertionError) as e:
            relation.single_model_precondition('not a ModelProtocol')
        assert str(e.exception) == 'model must implement ModelProtocol'

        with self.assertRaises(AssertionError) as e:
            relation.multi_model_precondition('not a list of ModelProtocol')
        assert str(e.exception) == 'must be a list of ModelProtocol'

        with self.assertRaises(AssertionError) as e:
            relation.multi_model_precondition(['not a ModelProtocol'])
        assert str(e.exception) == 'must be a list of ModelProtocol'

        with self.assertRaises(AssertionError) as e:
            relation.primary_model_precondition('not a ModelProtocol')
        assert str(e.exception) == 'primary must be instance of HashedModel'

        with self.assertRaises(AssertionError) as e:
            relation.secondary_model_precondition('not a ModelProtocol')
        assert str(e.exception) == 'secondary must be instance of Attachment'

        with self.assertRaises(AssertionError) as e:
            relation.pivot_preconditions('not a type')
        assert str(e.exception) == 'pivot must be class implementing ModelProtocol'

    def test_Relation_set_primary_sets_primary(self):
        relation = relations.Relation(
            primary_class=classes.HashedModel,
            secondary_class=classes.Attachment
        )
        primary = classes.HashedModel.insert({'data': '123abc'})

        with self.assertRaises(AssertionError) as e:
            relation.primary = 'not a primary class'
        assert str(e.exception) == 'model must implement ModelProtocol'

        assert relation.primary is None
        relation.set_primary(primary)
        assert relation.primary is primary

    def test_Relation_get_cache_key_returns_str_containing_class_names(self):
        relation = relations.Relation(
            primary_class=classes.HashedModel,
            secondary_class=classes.Attachment
        )

        cache_key = relation.get_cache_key()
        assert type(cache_key) is str
        assert cache_key == 'HashedModel_Relation_Attachment'

    # HasOne tests
    def test_HasOne_extends_Relation(self):
        assert issubclass(relations.HasOne, relations.Relation)

    def test_HasOne_initializes_properly(self):
        hasone = relations.HasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        assert isinstance(hasone, relations.HasOne)

        with self.assertRaises(AssertionError) as e:
            relations.HasOne(
                b'not a str',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
            )
        assert str(e.exception) == 'foreign_id_field must be str'

    def test_HasOne_sets_primary_and_secondary_correctly(self):
        hasone = relations.HasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        primary = self.OwnerModel.insert({'data': '321ads'})
        secondary = self.OwnedModel.insert({'data':'321'})

        assert hasone.primary is None
        hasone.primary = primary
        assert hasone.primary is primary

        with self.assertRaises(AssertionError) as e:
            hasone.secondary = 'not a ModelProtocol'
        assert str(e.exception) == 'model must implement ModelProtocol'

        with self.assertRaises(AssertionError) as e:
            hasone.secondary = self.OwnerModel({'data': '1234f'})
        assert str(e.exception) == 'secondary must be instance of OwnedModel'

        assert hasone.secondary is None
        hasone.secondary = secondary
        assert hasone.secondary is secondary

    def test_HasOne_get_cache_key_includes_foreign_id_field(self):
        hasone = relations.HasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        cache_key = hasone.get_cache_key()
        assert cache_key == 'OwnerModel_HasOne_OwnedModel_owner_id'

    def test_HasOne_save_raises_error_for_incomplete_relation(self):
        hasone = relations.HasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )

        with self.assertRaises(AssertionError) as e:
            hasone.save()
        assert str(e.exception) == 'cannot save incomplete HasOne'

    def test_HasOne_save_changes_foreign_id_field_on_secondary(self):
        hasone = relations.HasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        primary = self.OwnerModel.insert({'data': '321ads'})
        secondary = self.OwnedModel.insert({'data':'321'})

        hasone.primary = primary
        hasone.secondary = secondary

        assert secondary.data['owner_id'] == None
        hasone.save()
        assert secondary.data['owner_id'] == primary.data['id']

        reloaded = self.OwnedModel.find(secondary.data['id'])
        assert reloaded.data['owner_id'] == primary.data['id']

    def test_HasOne_changing_primary_and_secondary_updates_models_correctly(self):
        hasone = relations.HasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        primary1 = self.OwnerModel.insert({'data': '321ads'})
        primary2 = self.OwnerModel.insert({'data': '12332'})
        secondary1 = self.OwnedModel.insert({'data':'321'})
        secondary2 = self.OwnedModel.insert({'data':'afgbfb'})

        hasone.primary = primary1
        hasone.secondary = secondary1
        hasone.save()
        assert secondary1.data['owner_id'] == primary1.data['id']

        hasone.primary = primary2
        hasone.save()
        assert secondary1.data['owner_id'] == primary2.data['id']

        hasone.secondary = secondary2
        hasone.save()
        assert secondary2.data['owner_id'] == primary2.data['id']
        assert secondary1.data['owner_id'] == ''

    def test_HasOne_create_property_returns_property(self):
        hasone = relations.HasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        prop = hasone.create_property()

        assert type(prop) is property

    def test_HasOne_property_wraps_input_class(self):
        hasone = relations.HasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )


    # HasMany tests
    def test_HasMany_extends_Relation(self):
        assert issubclass(relations.HasMany, relations.Relation)

    # BelongsTo tests
    def test_BelongsTo_extends_Relation(self):
        assert issubclass(relations.BelongsTo, relations.Relation)

    # BelongsToMany tests
    def test_BelongsToMany_extends_Relation(self):
        assert issubclass(relations.BelongsToMany, relations.Relation)


if __name__ == '__main__':
    unittest.main()
