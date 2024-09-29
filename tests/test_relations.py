from __future__ import annotations
from context import classes, errors, interfaces, relations
from genericpath import isfile
import os
import sqlite3
import unittest


DB_FILEPATH = 'test.db'


class Pivot(classes.SqlModel):
    connection_info: str = DB_FILEPATH
    table: str = 'pivot'
    columns: tuple = ('id', 'first_id', 'second_id')


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
        self.cursor.execute('create table pivot (id text, first_id text, second_id text)')
        self.cursor.execute('create table owners (id text, details text)')
        self.cursor.execute('create table owned (id text, owner_id text, details text)')
        self.cursor.execute('create table dag (id text, details text, parent_ids text)')
        self.cursor.execute('create table deleted_records (id text not null, ' +
            'model_class text not null, record_id text not null, ' +
            'record blob not null, timestamp text not null)')

        # rebuild test classes because properties will be changed in tests
        class OwnedModel(classes.SqlModel):
            connection_info: str = DB_FILEPATH
            table: str = 'owned'
            columns: tuple = ('id', 'owner_id', 'details')

        class OwnerModel(classes.SqlModel):
            connection_info: str = DB_FILEPATH
            table: str = 'owners'
            columns: tuple = ('id', 'details')

        class DAGItem(classes.HashedModel):
            connection_info: str = DB_FILEPATH
            table: str = 'dag'
            columns: tuple = ('id', 'details', 'parent_ids')
            parents: interfaces.RelatedCollection
            children: interfaces.RelatedCollection

            @classmethod
            def insert(cls, data: dict) -> DAGItem|None:
                # """For better type hinting."""
                return super().insert(data)

        self.OwnedModel = OwnedModel
        self.OwnerModel = OwnerModel
        self.DAGItem = DAGItem
        classes.DeletedModel.connection_info = DB_FILEPATH

        return super().setUp()

    def tearDown(self) -> None:
        """Close cursor and delete test database."""
        q = "select name from sqlite_master where type='table'"
        self.cursor.execute(q)
        results = self.cursor.fetchall()
        for result in results:
            q = f"drop table if exists {result[0]};"
            try:
                self.cursor.execute(q)
            except BaseException as e:
                print(e)
        self.cursor.close()
        self.db.close()
        try:
            os.remove(DB_FILEPATH)
        except:
            ...
        return super().tearDown()

    # Relation tests
    def test_Relation_implements_RelationProtocol(self):
        assert isinstance(relations.Relation, interfaces.RelationProtocol)

    def test_Relation_initializes_properly(self):
        primary = self.OwnerModel.insert({'details': '1234'})
        secondary = self.OwnedModel.insert({'details': '321'})
        relation = relations.Relation(
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel,
            primary=primary,
            secondary=secondary
        )
        assert type(relation) is relations.Relation

        relation = relations.Relation(
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        assert type(relation) is relations.Relation

    def test_Relation_precondition_check_methods_raise_errors(self):
        relation = relations.Relation(
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )

        with self.assertRaises(TypeError) as e:
            relation.single_model_precondition('not a ModelProtocol')
        assert str(e.exception) == 'model must implement ModelProtocol'

        with self.assertRaises(TypeError) as e:
            relation.multi_model_precondition('not a list of ModelProtocol')
        assert str(e.exception) == 'must be a list of ModelProtocol'

        with self.assertRaises(TypeError) as e:
            relation.multi_model_precondition(['not a ModelProtocol'])
        assert str(e.exception) == 'must be a list of ModelProtocol'

        with self.assertRaises(TypeError) as e:
            relation.primary_model_precondition('not a ModelProtocol')
        assert str(e.exception) == 'primary must be instance of OwnerModel'

        with self.assertRaises(TypeError) as e:
            relation.secondary_model_precondition('not a ModelProtocol')
        assert str(e.exception) == 'secondary must be instance of OwnedModel'

        with self.assertRaises(TypeError) as e:
            relation.pivot_preconditions('not a type')
        assert str(e.exception) == 'pivot must be class implementing ModelProtocol'

    def test_Relation_get_cache_key_returns_str_containing_class_names(self):
        relation = relations.Relation(
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )

        cache_key = relation.get_cache_key()
        assert type(cache_key) is str
        assert cache_key == 'OwnerModel_Relation_OwnedModel'

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

        with self.assertRaises(TypeError) as e:
            relations.HasOne(
                b'not a str',
                primary_class=self.OwnerModel,
                secondary_class=self.OwnedModel
            )
        assert str(e.exception) == 'foreign_id_column must be str'

    def test_HasOne_sets_primary_and_secondary_correctly(self):
        hasone = relations.HasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        primary = self.OwnerModel.insert({'details': '321ads'})
        secondary = self.OwnedModel.insert({'details':'321'})

        assert hasone.primary is None
        hasone.primary = primary
        assert hasone.primary is primary

        with self.assertRaises(TypeError) as e:
            hasone.secondary = 'not a ModelProtocol'
        assert str(e.exception) == 'model must implement ModelProtocol'

        with self.assertRaises(TypeError) as e:
            hasone.secondary = self.OwnerModel({'details': '1234f'})
        assert str(e.exception) == 'secondary must be instance of OwnedModel'

        assert hasone.secondary is None
        hasone.secondary = secondary
        assert hasone.secondary is secondary

    def test_HasOne_get_cache_key_includes_foreign_id_column(self):
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

        with self.assertRaises(errors.UsageError) as e:
            hasone.save()
        assert str(e.exception) == 'cannot save incomplete HasOne'

    def test_HasOne_save_changes_foreign_id_column_on_secondary(self):
        hasone = relations.HasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        primary = self.OwnerModel.insert({'details': '321ads'})
        secondary = self.OwnedModel.insert({'details':'321'})

        hasone.primary = primary
        hasone.secondary = secondary

        assert secondary.data['owner_id'] == None
        hasone.save()
        assert secondary.data['owner_id'] == primary.data['id']

        reloaded = self.OwnedModel.find(secondary.data['id'])
        assert reloaded.data['owner_id'] == primary.data['id']

    def test_HasOne_save_unsets_change_tracking_properties(self):
        hasone = relations.HasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        primary = self.OwnerModel.insert({'details': '321ads'})
        primary2 = self.OwnerModel.insert({'details': 'sdsdsd'})
        secondary = self.OwnedModel.insert({'details':'321'})
        secondary2 = self.OwnedModel.insert({'details':'321asds'})

        hasone.primary = primary
        hasone.secondary = secondary
        hasone.save()
        hasone.primary = primary2

        assert hasone.primary_to_add is not None
        assert hasone.primary_to_remove is not None
        hasone.save()
        assert hasone.primary_to_add is None
        assert hasone.primary_to_remove is None

        hasone.secondary = secondary2
        assert len(hasone.secondary_to_add)
        assert len(hasone.secondary_to_remove)
        hasone.save()
        assert not len(hasone.secondary_to_add)
        assert not len(hasone.secondary_to_remove)

    def test_HasOne_changing_primary_and_secondary_updates_models_correctly(self):
        hasone = relations.HasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        primary1 = self.OwnerModel.insert({'details': '321ads'})
        primary2 = self.OwnerModel.insert({'details': '12332'})
        secondary1 = self.OwnedModel.insert({'details':'321'})
        secondary2 = self.OwnedModel.insert({'details':'afgbfb'})

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
        assert not secondary1.data['owner_id']

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
        self.OwnerModel.owned = hasone.create_property()

        owner = self.OwnerModel({'details': '123'})
        owned = self.OwnedModel({'details': '321'})

        assert not owner.owned
        owner.owned = owned
        assert owner.owned
        assert type(owner.owned) is not type(owned)
        assert owner.owned.data == owned.data

        assert callable(owner.owned)
        assert type(owner.owned()) is relations.HasOne

    def test_HasOne_save_changes_only_foreign_id_column_in_db(self):
        hasone = relations.HasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        self.OwnerModel.owned = hasone.create_property()

        owner = self.OwnerModel.insert({'details': '123'})
        owned = self.OwnedModel.insert({'details': '321'})
        owner.owned = owned
        owner.owned.data['details'] = 'abc'
        owner.owned().save()

        owned.reload()
        assert owned.data['details'] == '321'
        assert owned.data['owner_id'] == owner.data['id']

    def test_has_one_function_sets_property_from_HasOne(self):
        self.OwnerModel.owned = relations.has_one(
            self.OwnerModel,
            self.OwnedModel,
            'owner_id'
        )

        assert type(self.OwnerModel.owned) is property

        owner = self.OwnerModel.insert({'details': '321'})
        owned = self.OwnedModel.insert({'details': '321'})
        owner.owned = owned

        assert callable(owner.owned)
        assert type(owner.owned()) is relations.HasOne

        owner.owned().save()

    def test_HasOne_works_with_multiple_instances(self):
        self.OwnerModel.owned = relations.has_one(
            self.OwnerModel,
            self.OwnedModel,
            'owner_id'
        )

        owner1 = self.OwnerModel.insert({'details': 'owner1'})
        owner2 = self.OwnerModel.insert({'details': 'owner2'})
        owned1 = self.OwnedModel.insert({'details': 'owned1'})
        owned2 = self.OwnedModel.insert({'details': 'owned2'})

        owner1.owned = owned1
        owner1.owned().save()

        owner2.owned = owned2
        owner2.owned().save()

        assert owner1.relations != owner2.relations
        assert owner1.owned() is not owner2.owned()
        assert owner1.owned.data['id'] == owned1.data['id']
        assert owner2.owned.data['id'] == owned2.data['id']

    def test_HasOne_reload_raises_ValueError_for_empty_relation(self):
        hasone = relations.HasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )

        with self.assertRaises(ValueError) as e:
            hasone.reload()
        assert str(e.exception) == 'cannot reload an empty relation'

    # HasMany tests
    def test_HasMany_extends_Relation(self):
        assert issubclass(relations.HasMany, relations.Relation)

    def test_HasMany_initializes_properly(self):
        hasmany = relations.HasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        assert isinstance(hasmany, relations.HasMany)

        with self.assertRaises(TypeError) as e:
            relations.HasMany(
                b'not a str',
                primary_class=self.OwnerModel,
                secondary_class=self.OwnedModel
            )
        assert str(e.exception) == 'foreign_id_column must be str'

    def test_HasMany_sets_primary_and_secondary_correctly(self):
        hasmany = relations.HasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        primary = self.OwnerModel.insert({'details': '321ads'})
        secondary = self.OwnedModel.insert({'details':'321'})

        assert hasmany.primary is None
        hasmany.primary = primary
        assert hasmany.primary is primary

        with self.assertRaises(TypeError) as e:
            hasmany.secondary = secondary
        assert str(e.exception) == 'must be a list of ModelProtocol'

        with self.assertRaises(TypeError) as e:
            hasmany.secondary = [self.OwnerModel({'details': '1234f'})]
        assert str(e.exception) == 'secondary must be instance of OwnedModel'

        assert hasmany.secondary is None
        hasmany.secondary = [secondary]
        assert hasmany.secondary == (secondary,)

    def test_HasMany_get_cache_key_includes_foreign_id_column(self):
        hasmany = relations.HasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        cache_key = hasmany.get_cache_key()
        assert cache_key == 'OwnerModel_HasMany_OwnedModel_owner_id'

    def test_HasMany_save_raises_error_for_incomplete_relation(self):
        hasmany = relations.HasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )

        with self.assertRaises(errors.UsageError) as e:
            hasmany.save()
        assert str(e.exception) == 'cannot save incomplete HasMany'

    def test_HasMany_save_changes_foreign_id_column_on_secondary(self):
        hasmany = relations.HasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        primary = self.OwnerModel.insert({'details': '321ads'})
        secondary = self.OwnedModel.insert({'details':'321'})

        hasmany.primary = primary
        hasmany.secondary = [secondary]

        assert secondary.data['owner_id'] == None
        hasmany.save()
        assert secondary.data['owner_id'] == primary.data['id']

        reloaded = self.OwnedModel.find(secondary.data['id'])
        assert reloaded.data['owner_id'] == primary.data['id']

    def test_HasMany_save_unsets_change_tracking_properties(self):
        hasmany = relations.HasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        primary = self.OwnerModel.insert({'details': '321ads'})
        primary2 = self.OwnerModel.insert({'details': 'sdsdsd'})
        secondary = self.OwnedModel.insert({'details':'321'})
        secondary2 = self.OwnedModel.insert({'details':'321asds'})

        hasmany.primary = primary
        hasmany.secondary = [secondary]
        hasmany.save()
        hasmany.primary = primary2

        assert hasmany.primary_to_add is not None
        assert hasmany.primary_to_remove is not None
        hasmany.save()
        assert hasmany.primary_to_add is None
        assert hasmany.primary_to_remove is None

        hasmany.secondary = [secondary2]
        assert len(hasmany.secondary_to_add)
        assert len(hasmany.secondary_to_remove)
        hasmany.save()
        assert not len(hasmany.secondary_to_add)
        assert not len(hasmany.secondary_to_remove)

    def test_HasMany_changing_primary_and_secondary_updates_models_correctly(self):
        hasmany = relations.HasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        primary1 = self.OwnerModel.insert({'details': '321ads'})
        primary2 = self.OwnerModel.insert({'details': '12332'})
        secondary1 = self.OwnedModel.insert({'details':'321'})
        secondary2 = self.OwnedModel.insert({'details':'afgbfb'})

        hasmany.primary = primary1
        hasmany.secondary = [secondary1]
        hasmany.save()
        assert secondary1.data['owner_id'] == primary1.data['id']

        hasmany.primary = primary2
        hasmany.save()
        assert secondary1.data['owner_id'] == primary2.data['id']

        hasmany.secondary = [secondary2]
        hasmany.save()
        assert secondary2.data['owner_id'] == primary2.data['id']
        assert not secondary1.data['owner_id']

    def test_HasMany_create_property_returns_property(self):
        hasmany = relations.HasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        prop = hasmany.create_property()

        assert type(prop) is property

    def test_HasMany_property_wraps_input_tuple(self):
        hasmany = relations.HasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        self.OwnerModel.owned = hasmany.create_property()

        owner = self.OwnerModel({'details': '123'})
        owned = self.OwnedModel({'details': '321'})

        assert not owner.owned
        owner.owned = [owned]
        assert owner.owned
        assert isinstance(owner.owned, tuple)
        assert owner.owned[0].data == owned.data

        assert callable(owner.owned)
        assert type(owner.owned()) is relations.HasMany

    def test_HasMany_save_changes_only_foreign_id_column_in_db(self):
        hasmany = relations.HasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        self.OwnerModel.owned = hasmany.create_property()

        owner = self.OwnerModel.insert({'details': '123'})
        owned = self.OwnedModel.insert({'details': '321'})
        owner.owned = [owned]
        owner.owned[0].data['details'] = 'abc'
        owner.owned().save()

        owned.reload()
        assert owned.data['details'] == '321'
        assert owned.data['owner_id'] == owner.data['id']

    def test_has_many_function_sets_property_from_HasMany(self):
        self.OwnerModel.owned = relations.has_many(
            self.OwnerModel,
            self.OwnedModel,
            'owner_id'
        )

        assert type(self.OwnerModel.owned) is property

        owner = self.OwnerModel.insert({'details': '321'})
        owned = self.OwnedModel.insert({'details': '321'})
        owner.owned = [owned]

        assert callable(owner.owned)
        assert type(owner.owned()) is relations.HasMany

        owner.owned().save()

    def test_HasMany_works_with_multiple_instances(self):
        self.OwnerModel.owned = relations.has_many(
            self.OwnerModel,
            self.OwnedModel,
            'owner_id'
        )

        owner1 = self.OwnerModel.insert({'details': 'owner1'})
        owner2 = self.OwnerModel.insert({'details': 'owner2'})
        owned1 = self.OwnedModel.insert({'details': 'owned1'})
        owned2 = self.OwnedModel.insert({'details': 'owned2'})

        owner1.owned = [owned1]
        owner1.owned().save()

        owner2.owned = [owned2]
        owner2.owned().save()

        assert owner1.relations != owner2.relations
        assert owner1.owned() is not owner2.owned()
        assert owner1.owned[0].data['id'] == owned1.data['id']
        assert owner2.owned[0].data['id'] == owned2.data['id']

    def test_HasMany_reload_raises_ValueError_for_empty_relation(self):
        hasmany = relations.HasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel,
        )

        with self.assertRaises(ValueError) as e:
            hasmany.reload()
        assert str(e.exception) == 'cannot reload an empty relation'

    # BelongsTo tests
    def test_BelongsTo_extends_Relation(self):
        assert issubclass(relations.BelongsTo, relations.Relation)

    def test_BelongsTo_initializes_properly(self):
        belongsto = relations.BelongsTo(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        assert isinstance(belongsto, relations.BelongsTo)

        with self.assertRaises(TypeError) as e:
            relations.BelongsTo(
                b'not a str',
                primary_class=self.OwnerModel,
                secondary_class=self.OwnedModel
            )
        assert str(e.exception) == 'foreign_id_column must be str'

    def test_BelongsTo_sets_primary_and_secondary_correctly(self):
        belongsto = relations.BelongsTo(
            'owner_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        primary = self.OwnedModel.insert({'details': '321ads'})
        secondary = self.OwnerModel.insert({'details':'321'})

        assert belongsto.primary is None
        belongsto.primary = primary
        assert belongsto.primary is primary

        with self.assertRaises(TypeError) as e:
            belongsto.secondary = primary
        assert str(e.exception) == 'secondary must be instance of OwnerModel'

        assert belongsto.secondary is None
        belongsto.secondary = secondary
        assert belongsto.secondary == secondary

    def test_BelongsTo_get_cache_key_includes_foreign_id_column(self):
        belongsto = relations.BelongsTo(
            'owner_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        cache_key = belongsto.get_cache_key()
        assert cache_key == 'OwnedModel_BelongsTo_OwnerModel_owner_id'

    def test_BelongsTo_save_raises_error_for_incomplete_relation(self):
        belongsto = relations.BelongsTo(
            'owner_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )

        with self.assertRaises(errors.UsageError) as e:
            belongsto.save()
        assert str(e.exception) == 'cannot save incomplete BelongsTo'

    def test_BelongsTo_save_changes_foreign_id_column_on_secondary(self):
        belongsto = relations.BelongsTo(
            'owner_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        primary = self.OwnedModel.insert({'details': '321ads'})
        secondary = self.OwnerModel.insert({'details':'321'})

        belongsto.primary = primary
        belongsto.secondary = secondary

        assert primary.data['owner_id'] == None
        belongsto.save()
        assert primary.data['owner_id'] == secondary.data['id']

        reloaded = self.OwnedModel.find(primary.data['id'])
        assert reloaded.data['owner_id'] == secondary.data['id']

    def test_BelongsTo_save_unsets_change_tracking_properties(self):
        belongsto = relations.BelongsTo(
            'owner_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        primary = self.OwnedModel.insert({'details':'321'})
        primary2 = self.OwnedModel.insert({'details':'321asds'})
        secondary = self.OwnerModel.insert({'details': '321ads'})
        secondary2 = self.OwnerModel.insert({'details': 'sdsdsd'})

        belongsto.primary = primary
        belongsto.secondary = secondary
        belongsto.save()
        belongsto.primary = primary2

        assert belongsto.primary_to_add is not None
        assert belongsto.primary_to_remove is not None
        belongsto.save()
        assert belongsto.primary_to_add is None
        assert belongsto.primary_to_remove is None

        belongsto.secondary = secondary2
        assert len(belongsto.secondary_to_add)
        assert len(belongsto.secondary_to_remove)
        belongsto.save()
        assert not len(belongsto.secondary_to_add)
        assert not len(belongsto.secondary_to_remove)

    def test_BelongsTo_changing_primary_and_secondary_updates_models_correctly(self):
        belongsto = relations.BelongsTo(
            'owner_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        primary1 = self.OwnedModel.insert({'details': '321ads'})
        primary2 = self.OwnedModel.insert({'details': '12332'})
        secondary1 = self.OwnerModel.insert({'details':'321'})
        secondary2 = self.OwnerModel.insert({'details':'afgbfb'})

        belongsto.primary = primary1
        belongsto.secondary = secondary1
        belongsto.save()
        assert primary1.data['owner_id'] == secondary1.data['id']

        belongsto.primary = primary2
        belongsto.save()
        assert primary2.data['owner_id'] == secondary1.data['id']

        belongsto.secondary = secondary2
        belongsto.save()
        assert primary2.data['owner_id'] == secondary2.data['id']
        assert not primary1.data['owner_id']

    def test_BelongsTo_create_property_returns_property(self):
        belongsto = relations.BelongsTo(
            'owner_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        prop = belongsto.create_property()

        assert type(prop) is property

    def test_BelongsTo_property_wraps_input_class(self):
        belongsto = relations.BelongsTo(
            'owner_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        self.OwnedModel.owner = belongsto.create_property()

        owned = self.OwnedModel({'details': '321'})
        owner = self.OwnerModel({'details': '123'})

        assert not owned.owner
        owned.owner = owner
        assert owned.owner
        assert isinstance(owned.owner, self.OwnerModel)
        assert owned.owner.data == owner.data

        assert callable(owned.owner)
        assert type(owned.owner()) is relations.BelongsTo

    def test_BelongsTo_save_changes_only_foreign_id_column_in_db(self):
        belongsto = relations.BelongsTo(
            'owner_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        self.OwnedModel.owner = belongsto.create_property()

        owned = self.OwnedModel.insert({'details': '123'})
        owner = self.OwnerModel.insert({'details': '321'})
        owned.owner = owner
        owned.owner.data['details'] = 'abc'
        owned.owner().save()

        owner.reload()
        assert owner.data['details'] == '321'
        assert owned.data['owner_id'] == owner.data['id']

    def test_belongs_to_function_sets_property_from_BelongsTo(self):
        self.OwnedModel.owner = relations.belongs_to(
            self.OwnedModel,
            self.OwnerModel,
            'owner_id'
        )

        assert type(self.OwnedModel.owner) is property

        owned = self.OwnedModel.insert({'details': '321'})
        owner = self.OwnerModel.insert({'details': '123'})
        owned.owner = owner

        assert callable(owned.owner)
        assert type(owned.owner()) is relations.BelongsTo

        owned.owner().save()

    def test_BelongsTo_works_with_multiple_instances(self):
        self.OwnedModel.owner = relations.belongs_to(
            self.OwnedModel,
            self.OwnerModel,
            'owner_id'
        )

        owned1 = self.OwnedModel.insert({'details': 'owned1'})
        owned2 = self.OwnedModel.insert({'details': 'owned2'})
        owner1 = self.OwnerModel.insert({'details': 'owner1'})
        owner2 = self.OwnerModel.insert({'details': 'owner2'})

        owned1.owner = owner1
        owned1.owner().save()

        owned2.owner = owner2
        owned2.owner().save()

        assert owned1.owner() is not owned2.owner()
        assert owned1.owner.data['id'] == owner1.data['id']
        assert owned2.owner.data['id'] == owner2.data['id']

    def test_BelongsTo_reload_raises_ValueError_for_empty_relation(self):
        belongsto = relations.BelongsTo(
            'owner_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel,
        )

        with self.assertRaises(ValueError) as e:
            belongsto.reload()
        assert str(e.exception) == 'cannot reload an empty relation'

    # BelongsToMany tests
    def test_BelongsToMany_extends_Relation(self):
        assert issubclass(relations.BelongsToMany, relations.Relation)

    def test_BelongsToMany_initializes_properly(self):
        belongstomany = relations.BelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        assert isinstance(belongstomany, relations.BelongsToMany)

        with self.assertRaises(TypeError) as e:
            relations.BelongsToMany(
                Pivot,
                b'not a str',
                'second_id'
            )
        assert str(e.exception) == 'primary_id_column and secondary_id_column must be str'

    def test_BelongsToMany_sets_primary_and_secondary_correctly(self):
        belongstomany = relations.BelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        primary = self.OwnedModel.insert({'details': '321ads'})
        secondary = self.OwnerModel.insert({'details':'321'})

        assert belongstomany.primary is None
        belongstomany.primary = primary
        assert belongstomany.primary is primary

        with self.assertRaises(TypeError) as e:
            belongstomany.secondary = secondary
        assert str(e.exception) == 'must be a list of ModelProtocol'

        with self.assertRaises(TypeError) as e:
            belongstomany.secondary = [primary]
        assert str(e.exception) == 'secondary must be instance of OwnerModel'

        assert belongstomany.secondary is None
        belongstomany.secondary = [secondary]
        assert belongstomany.secondary[0] == secondary

    def test_BelongsToMany_get_cache_key_includes_foreign_id_column(self):
        belongstomany = relations.BelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        cache_key = belongstomany.get_cache_key()
        assert cache_key == 'OwnedModel_BelongsToMany_OwnerModel_Pivot_first_id_second_id'

    def test_BelongsToMany_save_raises_error_for_incomplete_relation(self):
        belongstomany = relations.BelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )

        with self.assertRaises(errors.UsageError) as e:
            belongstomany.save()
        assert str(e.exception) == 'cannot save incomplete BelongsToMany'

    def test_BelongsToMany_save_changes_foreign_id_column_on_secondary(self):
        belongstomany = relations.BelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        primary = self.OwnedModel.insert({'details': '321ads'})
        secondary = self.OwnerModel.insert({'details':'321'})

        belongstomany.primary = primary
        belongstomany.secondary = [secondary]

        assert Pivot.query().count() == 0
        belongstomany.save()
        assert Pivot.query().count() == 1
        belongstomany.save()
        assert Pivot.query().count() == 1

    def test_BelongsToMany_save_unsets_change_tracking_properties(self):
        belongstomany = relations.BelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        primary = self.OwnedModel.insert({'details':'321'})
        primary2 = self.OwnedModel.insert({'details':'321asds'})
        secondary = self.OwnerModel.insert({'details': '321ads'})
        secondary2 = self.OwnerModel.insert({'details': 'sdsdsd'})

        belongstomany.primary = primary
        belongstomany.secondary = [secondary]
        belongstomany.save()
        belongstomany.primary = primary2

        assert belongstomany.primary_to_add is not None
        assert belongstomany.primary_to_remove is not None
        belongstomany.save()
        assert belongstomany.primary_to_add is None
        assert belongstomany.primary_to_remove is None

        belongstomany.secondary = [secondary2]
        assert len(belongstomany.secondary_to_add)
        assert len(belongstomany.secondary_to_remove)
        belongstomany.save()
        assert not len(belongstomany.secondary_to_add)
        assert not len(belongstomany.secondary_to_remove)

    def test_BelongsToMany_changing_primary_and_secondary_updates_models_correctly(self):
        belongstomany = relations.BelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        primary1 = self.OwnedModel.insert({'details': '321ads'})
        primary2 = self.OwnedModel.insert({'details': '12332'})
        secondary1 = self.OwnerModel.insert({'details':'321'})
        secondary2 = self.OwnerModel.insert({'details':'afgbfb'})

        belongstomany.primary = primary1
        belongstomany.secondary = [secondary1]
        belongstomany.save()
        pivot = Pivot.query().first()
        assert pivot is not None
        assert pivot.data['first_id'] == primary1.data['id']
        assert pivot.data['second_id'] == secondary1.data['id']

        belongstomany.primary = primary2
        belongstomany.save()
        assert Pivot.query().count() == 1
        pivot = Pivot.query().first()
        assert pivot.data['first_id'] == primary2.data['id']
        assert pivot.data['second_id'] == secondary1.data['id']

        belongstomany.secondary = [secondary2]
        belongstomany.save()
        assert Pivot.query().count() == 1
        pivot = Pivot.query().first()
        assert pivot.data['first_id'] == primary2.data['id']
        assert pivot.data['second_id'] == secondary2.data['id']

    def test_BelongsToMany_create_property_returns_property(self):
        belongstomany = relations.BelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        prop = belongstomany.create_property()

        assert type(prop) is property

    def test_BelongsToMany_property_wraps_input_class(self):
        belongstomany = relations.BelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        self.OwnedModel.owners = belongstomany.create_property()

        owned = self.OwnedModel({'details': '321'})
        owner = self.OwnerModel({'details': '123'})

        assert not owned.owners
        owned.owners = [owner]
        assert owned.owners
        assert isinstance(owned.owners, tuple)
        assert owned.owners[0].data == owner.data

        assert callable(owned.owners)
        assert type(owned.owners()) is relations.BelongsToMany

    def test_BelongsToMany_save_changes_only_foreign_id_column_in_db(self):
        belongstomany = relations.BelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        self.OwnedModel.owners = belongstomany.create_property()

        owned = self.OwnedModel.insert({'details': '123'})
        owner = self.OwnerModel.insert({'details': '321'})
        owned.owners = [owner]
        owned.owners[0].data['details'] = 'abc'
        assert Pivot.query().count() == 0
        owned.owners().save()

        owner.reload()
        assert owner.data['details'] == '321'
        assert Pivot.query().count() == 1

    def test_belongs_to_many_function_sets_property_from_BelongsToMany(self):
        self.OwnedModel.owners = relations.belongs_to_many(
            self.OwnedModel,
            self.OwnerModel,
            Pivot,
            'first_id',
            'second_id',
        )

        assert type(self.OwnedModel.owners) is property

        owned = self.OwnedModel.insert({'details': '321'})
        owner = self.OwnerModel.insert({'details': '123'})
        owned.owners = [owner]

        assert callable(owned.owners)
        assert type(owned.owners()) is relations.BelongsToMany

        owned.owners().save()

    def test_BelongsToMany_works_with_multiple_instances(self):
        self.OwnedModel.owners = relations.belongs_to_many(
            self.OwnedModel,
            self.OwnerModel,
            Pivot,
            'first_id',
            'second_id',
        )

        owned1 = self.OwnedModel.insert({'details': 'owned1'})
        owned2 = self.OwnedModel.insert({'details': 'owned2'})
        owner1 = self.OwnerModel.insert({'details': 'owner1'})
        owner2 = self.OwnerModel.insert({'details': 'owner2'})

        owned1.owners = [owner1]
        owned1.owners().save()

        owned2.owners = [owner2]
        owned2.owners().save()

        assert owned1.relations != owned2.relations
        assert owned1.owners() is not owned2.owners()
        assert owned1.owners[0].data['id'] == owner1.data['id']
        assert owned2.owners[0].data['id'] == owner2.data['id']

    def test_BelongsToMany_reload_raises_ValueError_for_empty_relation(self):
        belongstomany = relations.BelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )

        with self.assertRaises(ValueError) as e:
            belongstomany.reload()
        assert str(e.exception) == 'cannot reload an empty relation'

    # Contains tests
    def test_Contains_extends_Relation(self):
        assert issubclass(relations.Contains, relations.Relation)

    def test_Contains_initializes_properly(self):
        contains = relations.Contains(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        assert isinstance(contains, relations.Contains)

        with self.assertRaises(TypeError) as e:
            relations.Contains(
                b'not a str',
                'second_id'
            )
        assert str(e.exception) == 'foreign_id_column must be str', e.exception

    def test_Contains_sets_primary_and_secondary_correctly(self):
        contains = relations.Contains(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        secondary = self.DAGItem.insert({'details': '321ads'})
        primary = self.DAGItem({'details':'321'})

        assert contains.primary is None
        contains.primary = primary
        assert contains.primary is primary

        with self.assertRaises(TypeError) as e:
            contains.secondary = secondary
        assert str(e.exception) == 'must be a list of ModelProtocol'

        with self.assertRaises(TypeError) as e:
            contains.secondary = [self.OwnedModel()]
        assert str(e.exception) == 'secondary must be instance of DAGItem'

        assert contains.secondary is None
        contains.secondary = [secondary]
        assert contains.secondary[0] == secondary

    def test_Contains_get_cache_key_includes_foreign_id_column(self):
        contains = relations.Contains(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        cache_key = contains.get_cache_key()
        assert cache_key == 'DAGItem_Contains_DAGItem_parent_ids'

    def test_Contains_save_raises_error_for_incomplete_relation(self):
        contains = relations.Contains(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )

        with self.assertRaises(errors.UsageError) as e:
            contains.save()
        assert str(e.exception) == 'cannot save incomplete Contains'

    def test_Contains_save_changes_foreign_id_column_on_primary(self):
        contains = relations.Contains(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        primary = self.DAGItem({'details':'321'})
        secondary = self.DAGItem.insert({'details': '321ads'})

        contains.primary = primary
        contains.secondary = [secondary]

        assert primary.id is None
        contains.save()
        assert primary.id is not None
        assert contains.query().count() == 1
        contains.save()
        assert contains.query().count() == 1

    def test_Contains_save_unsets_change_tracking_properties(self):
        contains = relations.Contains(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        primary = self.DAGItem({'details':'321'})
        primary2 = self.DAGItem({'details':'321asds'})
        secondary = self.DAGItem.insert({'details': '321ads'})
        secondary2 = self.DAGItem.insert({'details': 'sdsdsd'})

        contains.primary = primary
        contains.secondary = [secondary]
        contains.save()
        contains.primary = primary2

        assert contains.primary_to_add is not None
        assert contains.primary_to_remove is not None
        contains.save()
        assert contains.primary_to_add is None
        assert contains.primary_to_remove is None

        contains.secondary = [secondary2]
        assert len(contains.secondary_to_add)
        assert len(contains.secondary_to_remove)
        contains.save()
        assert not len(contains.secondary_to_add)
        assert not len(contains.secondary_to_remove)

    def test_Contains_changing_primary_and_secondary_updates_models_correctly(self):
        contains = relations.Contains(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        primary1 = self.DAGItem({'details': '321ads'})
        primary2 = self.DAGItem({'details': '12332'})
        secondary1 = self.DAGItem.insert({'details':'321'})
        secondary2 = self.DAGItem.insert({'details':'afgbfb'})

        assert primary1.id is None
        contains.primary = primary1
        contains.secondary = [secondary1]
        contains.save()
        assert primary1.id is not None

        assert primary2.id is None
        contains.primary = primary2
        contains.save()
        assert primary2.id is not None

        old_id = contains.primary.id
        contains.secondary = [secondary2]
        contains.save()
        assert contains.primary.id != old_id

    def test_Contains_create_property_returns_property(self):
        contains = relations.Contains(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        prop = contains.create_property()

        assert type(prop) is property

    def test_Contains_property_wraps_input_class(self):
        contains = relations.Contains(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        self.DAGItem.parents = contains.create_property()

        child = self.DAGItem({'details': '321'})
        parent = self.DAGItem({'details': '123'})

        assert not child.parents
        child.parents = [parent]
        assert child.parents
        assert isinstance(child.parents, tuple)
        assert child.parents[0].data == parent.data

        assert callable(child.parents)
        assert type(child.parents()) is relations.Contains

    def test_Contains_save_changes_only_foreign_id_column_in_db(self):
        contains = relations.Contains(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        self.DAGItem.parents = contains.create_property()

        parent = self.DAGItem.insert({'details': '321'})
        child = self.DAGItem({'details': '123', 'parent_ids': ''})
        child.parents = []
        assert child.parents().query().count() == 0
        child.parents = [parent]
        child.parents[0].data['details'] = 'abc'
        child.parents().save()

        parent.reload()
        assert parent.data['details'] == '321'
        assert child.parents().query().count() == 1

    def test_contains_function_sets_property_from_Contains(self):
        self.DAGItem.parents = relations.contains(
            self.DAGItem,
            self.DAGItem,
            'parent_ids',
        )

        assert type(self.DAGItem.parents) is property

        parent = self.DAGItem.insert({'details': '123'})
        child = self.DAGItem({'details': '321'})
        assert len(child.parents) == 0
        child.parents = [parent]

        assert callable(child.parents)
        assert type(child.parents()) is relations.Contains

        child.parents().save()
        assert len(child.parents) == 1

    def test_Contains_works_with_multiple_instances(self):
        self.DAGItem.parents = relations.contains(
            self.DAGItem,
            self.DAGItem,
            'parent_ids',
        )

        parent1 = self.DAGItem.insert({'details': 'parent1'})
        parent2 = self.DAGItem.insert({'details': 'parent2'})
        child1 = self.DAGItem({'details': 'child1'})
        child2 = self.DAGItem({'details': 'child2'})

        child1.parents = [parent1]
        assert child1.id is None
        child1.parents().save()
        assert child1.id is not None

        child2.parents = [parent2]
        child2.parents().save()

        assert child1.relations != child2.relations
        assert child1.parents() is not child2.parents()
        assert child1.parents[0].data['id'] == parent1.data['id']
        assert child2.parents[0].data['id'] == parent2.data['id']

    def test_Contains_reload_raises_ValueError_for_empty_relation(self):
        contains = relations.Contains(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )

        with self.assertRaises(ValueError) as e:
            contains.reload()
        assert str(e.exception) == 'cannot reload an empty relation'

    # Within tests
    def test_Within_extends_Relation(self):
        assert issubclass(relations.Within, relations.Relation)

    def test_Within_initializes_properly(self):
        within = relations.Within(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        assert isinstance(within, relations.Within)

        with self.assertRaises(TypeError) as e:
            relations.Within(
                b'not a str',
                'second_id'
            )
        assert str(e.exception) == 'foreign_id_column must be str', e.exception

    def test_Within_sets_primary_and_secondary_correctly(self):
        within = relations.Within(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        primary = self.DAGItem.insert({'details': '321ads'})
        secondary = self.DAGItem({'details':'321'})

        assert within.primary is None
        within.primary = primary
        assert within.primary is primary

        with self.assertRaises(TypeError) as e:
            within.secondary = self.OwnedModel()
        assert str(e.exception) == 'must be a list of ModelProtocol', e.exception

        with self.assertRaises(TypeError) as e:
            within.secondary = [self.OwnedModel()]
        assert str(e.exception) == 'secondary must be instance of DAGItem', e.exception

        assert within.secondary is None
        within.secondary = [secondary]
        assert within.secondary == (secondary,)

    def test_Within_get_cache_key_includes_foreign_id_column(self):
        within = relations.Within(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        cache_key = within.get_cache_key()
        assert cache_key == 'DAGItem_Within_DAGItem_parent_ids'

    def test_Within_save_raises_error_for_incomplete_relation(self):
        within = relations.Within(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )

        with self.assertRaises(errors.UsageError) as e:
            within.save()
        assert str(e.exception) == 'cannot save incomplete Within', e.exception

    def test_Within_save_changes_foreign_id_column_on_primary(self):
        within = relations.Within(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        secondary = self.DAGItem({'details':'321'})
        primary = self.DAGItem.insert({'details': '321ads'})

        within.primary = primary
        within.secondary = [secondary]

        assert secondary.id is None
        within.save()
        assert secondary.id is not None
        assert within.query().count() == 1
        within.save()
        assert within.query().count() == 1

    def test_Within_save_unsets_change_tracking_properties(self):
        within = relations.Within(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        primary = self.DAGItem.insert({'details': '321ads'})
        primary2 = self.DAGItem.insert({'details': 'sdsdsd'})
        secondary = self.DAGItem({'details':'321'})
        secondary2 = self.DAGItem({'details':'321asds'})

        within.primary = primary
        within.secondary = [secondary]
        within.save()
        within.primary = primary2

        assert within.primary_to_add is not None
        assert within.primary_to_remove is not None
        within.save()
        assert within.primary_to_add is None
        assert within.primary_to_remove is None

        within.secondary = [secondary2]
        assert len(within.secondary_to_add)
        assert len(within.secondary_to_remove)
        within.save()
        assert not len(within.secondary_to_add)
        assert not len(within.secondary_to_remove)

    def test_Within_changing_primary_and_secondary_updates_models_correctly(self):
        within = relations.Within(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        primary1 = self.DAGItem.insert({'details':'321'})
        primary2 = self.DAGItem.insert({'details':'afgbfb'})
        secondary1 = self.DAGItem({'details': '321ads'})
        secondary2 = self.DAGItem({'details': '12332'})

        assert secondary1.id is None
        within.primary = primary1
        within.secondary = [secondary1]
        within.save()
        assert secondary1.id is not None

        assert secondary2.id is None
        within.secondary = [secondary2]
        within.save()
        assert secondary2.id is not None

        old_id = within.secondary[0].id
        within.primary = primary2
        within.save()
        assert within.secondary[0].id != old_id

    def test_Within_create_property_returns_property(self):
        within = relations.Within(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        prop = within.create_property()

        assert type(prop) is property

    def test_Within_property_wraps_input_class(self):
        within = relations.Within(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        self.DAGItem.children = within.create_property()

        child = self.DAGItem({'details': '321'})
        parent = self.DAGItem({'details': '123'})

        assert not parent.children
        parent.children = [child]
        assert parent.children
        assert isinstance(parent.children, tuple)
        assert parent.children[0].data == child.data

        assert callable(parent.children)
        assert type(parent.children()) is relations.Within

    def test_Within_save_changes_foreign_id_column_in_db(self):
        within = relations.Within(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        self.DAGItem.children = within.create_property()

        parent = self.DAGItem.insert({'details': '321'})
        child = self.DAGItem({'details': '123', 'parent_ids': ''})
        parent.children = []
        assert parent.children().query().count() == 0
        parent.children = [child]
        parent.children[0].data['details'] = 'abc'
        parent.children().save()

        child.reload()
        assert child.data['details'] == 'abc', child.data
        assert child.id is not None
        assert parent.children().query().count() == 1

    def test_within_function_sets_property_from_Within(self):
        self.DAGItem.children = relations.within(
            self.DAGItem,
            self.DAGItem,
            'parent_ids',
        )

        assert type(self.DAGItem.children) is property

        parent = self.DAGItem.insert({'details': '123'})
        child = self.DAGItem({'details': '321'})
        assert len(parent.children) == 0
        parent.children = [child]

        assert callable(parent.children)
        assert type(parent.children()) is relations.Within

        parent.children().save()
        assert len(parent.children) == 1

    def test_Within_works_with_multiple_instances(self):
        self.DAGItem.children = relations.within(
            self.DAGItem,
            self.DAGItem,
            'parent_ids',
        )

        parent1 = self.DAGItem.insert({'details': 'parent1'})
        parent2 = self.DAGItem.insert({'details': 'parent2'})
        child1 = self.DAGItem({'details': 'child1'})
        child2 = self.DAGItem({'details': 'child2'})

        parent1.children = [child1]
        assert child1.id is None
        parent1.children().save()
        assert child1.id is not None

        parent2.children = [child2]
        parent2.children().save()

        assert child1.relations != child2.relations
        assert parent1.children() is not parent2.children()
        assert parent1.children[0].data['id'] == child1.data['id']
        assert parent2.children[0].data['id'] == child2.data['id']

    def test_Within_reload_raises_ValueError_for_empty_relation(self):
        within = relations.Within(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )

        with self.assertRaises(ValueError) as e:
            within.reload()
        assert str(e.exception) == 'cannot reload an empty relation'


    # e2e tests
    def test_HasOne_BelongsTo_e2e(self):
        self.OwnerModel.__name__ = 'Owner'
        self.OwnerModel.owned = relations.has_one(
            self.OwnerModel,
            self.OwnedModel
        )
        self.OwnedModel.owner = relations.belongs_to(
            self.OwnedModel,
            self.OwnerModel
        )

        owner1 = self.OwnerModel.insert({'details': 'owner1'})
        owned1 = self.OwnedModel.insert({'details': 'owned1'})
        owner2 = self.OwnerModel({'details': 'owner2'})
        owned2 = self.OwnedModel({'details': 'owned2'})

        assert owner1.owned().foreign_id_column == 'owner_id'

        owner1.owned = owned1
        owner1.owned().save()
        owned1.owner().reload()
        assert owned1.owner
        assert owned1.owner.data == owner1.data
        owned1.owner = owner2
        owned1.owner().save()

        owner2.owned().reload()
        assert owner2.owned
        assert owner2.owned.data == owned1.data

        owner2.owned = owned2
        owner2.owned().save()
        assert owner2.owned
        assert owner2.owned.data == owned2.data

        owned2.owner().reload()
        assert owned2.owner
        assert owned2.owner.data == owner2.data

        hasone = relations.HasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel,
        )
        hasone.secondary = owned2
        hasone.reload()
        assert hasone.primary
        assert hasone.primary == owner2

    def test_HasMany_BelongsTo_e2e(self):
        self.OwnerModel.__name__ = 'Owner'
        self.OwnerModel.owned = relations.has_many(
            self.OwnerModel,
            self.OwnedModel
        )
        self.OwnedModel.owner = relations.belongs_to(
            self.OwnedModel,
            self.OwnerModel
        )

        owner1 = self.OwnerModel.insert({'details': 'owner1'})
        owned1 = self.OwnedModel.insert({'details': 'owned1'})
        owner2 = self.OwnerModel({'details': 'owner2'})
        owned2 = self.OwnedModel({'details': 'owned2'})

        assert owner1.owned().foreign_id_column == 'owner_id'

        owner1.owned = [owned1]
        owner1.owned().save()
        owned1.owner().reload()
        assert owned1.owner
        assert owned1.owner.data == owner1.data
        owned1.owner = owner2
        owned1.owner().save()

        owner2.owned().reload()
        assert owner2.owned
        assert owner2.owned[0].data == owned1.data

        owner2.owned = [owned1, owned2]
        owner2.owned().save()
        assert owner2.owned
        assert owner2.owned == (owned1, owned2)
        owner2.owned = [owned1, owned2, owned2]
        assert owner2.owned == (owned1, owned2)

        owned2.owner().reload()
        assert owned2.owner
        assert owned2.owner.data == owner2.data

        hasmany = relations.HasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel,
        )
        hasmany.secondary = [owned1, owned2]
        hasmany.reload()
        assert hasmany.primary
        assert hasmany.primary == owner2

    def test_BelongsToMany_e2e(self):
        self.OwnedModel.owned = relations.belongs_to_many(
            self.OwnedModel,
            self.OwnedModel,
            Pivot,
            'first_id',
            'second_id',
        )
        self.OwnedModel.owners = relations.belongs_to_many(
            self.OwnedModel,
            self.OwnedModel,
            Pivot,
            'second_id',
            'first_id',
        )

        owned1 = self.OwnedModel.insert({'details': '1'})
        owned2 = self.OwnedModel.insert({'details': '2'})
        owned3 = self.OwnedModel.insert({'details': '3'})

        owned1.owned = [owned2, owned3]
        assert owned1.owned
        assert owned1.owned == (owned2, owned3)
        owned1.owned().save()
        owned1.owned = [owned2, owned3, owned3]
        assert owned1.owned == (owned2, owned3)

        owned2.owners().reload()
        assert owned2.owners
        assert owned2.owners == (owned1,)

        belongstomany = relations.BelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnedModel,
        )

        belongstomany.secondary = [owned2, owned3]
        belongstomany.reload()
        assert belongstomany.primary
        assert belongstomany.primary == owned1

    def test_Contains_Within_e2e(self):
        self.DAGItem.parents = relations.contains(
            self.DAGItem,
            self.DAGItem,
            'parent_ids',
        )
        self.DAGItem.children = relations.within(
            self.DAGItem,
            self.DAGItem,
            'parent_ids',
        )

        parent1 = self.DAGItem.insert({'details': 'Gen 1 item 1'})
        parent2 = self.DAGItem.insert({'details': 'Gen 1 item 2'})
        child1 = self.DAGItem({'details': 'Gen 2 item 1'})
        child2 = self.DAGItem({'details': 'Gen 2 item 2'})

        assert len(parent1.children) == 0
        parent1.children = [child1]
        parent1.children().save()
        parent1.children().reload()
        assert len(parent1.children) == 1
        parent1.children = [child1, child2]
        parent1.children().save()
        parent1.children().reload()
        assert len(parent1.children) == 2
        assert child1 in parent1.children
        assert child2 in parent1.children

        assert len(child1.parents) == 0
        child1.parents().reload()
        assert child1.parents == (parent1,)
        child1.parents = [parent1, parent2]
        child1.parents().save()

        assert len(parent2.children) == 0
        parent2.children().reload()
        assert len(parent2.children) == 1


if __name__ == '__main__':
    unittest.main()
