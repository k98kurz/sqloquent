from context import classes, errors, interfaces, relations
from genericpath import isfile
import os
import sqlite3
import unittest


DB_FILEPATH = 'test.db'


class Pivot(classes.SqliteModel):
    file_path: str = DB_FILEPATH
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

        # rebuild test classes because properties will be changed in tests
        class OwnedModel(classes.SqliteModel):
            file_path: str = DB_FILEPATH
            table: str = 'owned'
            columns: tuple = ('id', 'owner_id', 'details')

        class OwnerModel(classes.SqliteModel):
            file_path: str = DB_FILEPATH
            table: str = 'owners'
            columns: tuple = ('id', 'details')

        self.OwnedModel = OwnedModel
        self.OwnerModel = OwnerModel

        return super().setUp()

    def tearDown(self) -> None:
        """Close cursor and delete test database."""
        self.cursor.close()
        self.db.close()
        os.remove(self.db_filepath)
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

    def test_has_one_function_sets_inverse(self):
        self.OwnerModel.owned = relations.has_one(
            self.OwnerModel,
            self.OwnedModel,
            'owner_id'
        )

        owner = self.OwnerModel.insert({'details': '321'})
        owned = self.OwnedModel.insert({'details': '321'})
        owner.owned = owned

        assert hasattr(owner.owned(), 'inverse')
        assert isinstance(owner.owned().inverse, relations.BelongsTo)

    def test_has_one_function_inverse_sets_primary_and_secondary(self):
        self.OwnerModel.owned = relations.has_one(
            self.OwnerModel,
            self.OwnedModel,
            'owner_id'
        )

        owner = self.OwnerModel.insert({'details': '321'})
        owned = self.OwnedModel.insert({'details': '321'})
        owner.owned = owned

        assert owner.owned().inverse.primary.data == owner.owned.data
        assert owner.owned().inverse.secondary.data == owner.data

    def test_HasOne_changes_affect_inverse(self):
        self.OwnerModel.owned = relations.has_one(
            self.OwnerModel,
            self.OwnedModel,
            'owner_id'
        )

        owner = self.OwnerModel.insert({'details': '321'})
        owned = self.OwnedModel.insert({'details': '321'})
        owned2 = self.OwnedModel.insert({'details': '123'})
        owner.owned = owned
        assert len(owner.owned().inverse.secondary_to_add)
        owner.owned().save()

        assert owner.owned().inverse.primary.data == owner.owned.data
        assert owner.owned.data == owned.data
        assert not len(owner.owned().inverse.secondary_to_add)

        owner.owned = owned2
        assert len(owner.owned().secondary_to_add)
        assert len(owner.owned().inverse.secondary_to_add)
        owner.owned().save()
        assert not len(owner.owned().secondary_to_add)
        assert not len(owner.owned().inverse.secondary_to_add)

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

    def test_has_many_function_sets_inverse(self):
        self.OwnerModel.owned = relations.has_many(
            self.OwnerModel,
            self.OwnedModel,
            'owner_id'
        )

        owner = self.OwnerModel.insert({'details': '321'})
        owned = self.OwnedModel.insert({'details': '321'})
        owner.owned = [owned]

        assert hasattr(owner.owned(), 'inverse')
        assert isinstance(owner.owned().inverse, list)
        for inverse in owner.owned().inverse:
            assert isinstance(inverse, relations.BelongsTo)

    def test_has_many_function_inverse_sets_primary_and_secondary(self):
        self.OwnerModel.owned = relations.has_many(
            self.OwnerModel,
            self.OwnedModel,
            'owner_id'
        )

        owner = self.OwnerModel.insert({'details': '321'})
        owned = self.OwnedModel.insert({'details': '321'})
        owner.owned = [owned]

        assert owner.owned().inverse[0].primary.data == owner.owned[0].data
        assert owner.owned().inverse[0].secondary.data == owner.data

    def test_HasMany_changes_affect_inverses(self):
        self.OwnerModel.owned = relations.has_many(
            self.OwnerModel,
            self.OwnedModel,
            'owner_id'
        )

        owner = self.OwnerModel.insert({'details': '321'})
        owned = self.OwnedModel.insert({'details': '321'})
        owned2 = self.OwnedModel.insert({'details': '123'})
        owner.owned = [owned]
        assert len(owner.owned().inverse[0].secondary_to_add)
        owner.owned().save()

        assert owner.owned().inverse[0].primary.data == owner.owned[0].data
        assert owner.owned[0].data == owned.data
        assert not len(owner.owned().inverse[0].secondary_to_add)

        owner.owned = [owned2]
        assert len(owner.owned().secondary_to_add)
        assert len(owner.owned().inverse[0].secondary_to_add)
        owner.owned().save()
        assert not len(owner.owned().secondary_to_add)
        assert not len(owner.owned().inverse[0].secondary_to_add)

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

        assert owner1.relations != owner2.relations
        assert owned1.owner() is not owned2.owner()
        assert owned1.owner.data['id'] == owner1.data['id']
        assert owned2.owner.data['id'] == owner2.data['id']

    def test_belongs_to_function_sets_inverse(self):
        self.OwnedModel.owner = relations.belongs_to(
            self.OwnedModel,
            self.OwnerModel,
            'owner_id'
        )

        owner = self.OwnerModel.insert({'details': '321'})
        owned = self.OwnedModel.insert({'details': '321'})
        owned.owner = owner

        assert hasattr(owned.owner(), 'inverse')
        assert isinstance(owned.owner().inverse, relations.HasOne)

        self.OwnedModel.owner = relations.belongs_to(
            self.OwnedModel,
            self.OwnerModel,
            'owner_id',
            True
        )

        owner = self.OwnerModel.insert({'details': '123'})
        owned = self.OwnedModel.insert({'details': '123'})
        owned.owner = owner

        assert hasattr(owned.owner(), 'inverse')
        assert isinstance(owned.owner().inverse, relations.HasMany)

    def test_belongs_to_function_inverse_sets_primary_and_secondary(self):
        self.OwnedModel.owner = relations.belongs_to(
            self.OwnedModel,
            self.OwnerModel,
            'owner_id'
        )

        owner = self.OwnerModel.insert({'details': '321'})
        owned = self.OwnedModel.insert({'details': '321'})
        owned.owner = owner

        assert owned.owner().inverse.primary.data == owned.owner.data
        assert owned.owner().inverse.secondary.data == owned.data

    def test_BelongsTo_changes_affect_inverses(self):
        self.OwnedModel.owner = relations.belongs_to(
            self.OwnedModel,
            self.OwnerModel,
            'owner_id'
        )

        owner = self.OwnerModel.insert({'details': '321'})
        owner2 = self.OwnerModel.insert({'details': '123'})
        owned = self.OwnedModel.insert({'details': '321'})
        owned.owner = owner
        assert len(owned.owner().inverse.secondary_to_add)
        owned.owner().save()

        assert owned.owner().inverse.primary.data == owned.owner.data
        assert owned.owner.data == owner.data
        assert not len(owned.owner().inverse.secondary_to_add)

        owned.owner = owner2
        assert owned.owner().inverse.primary.data == owner2.data
        assert len(owned.owner().secondary_to_add)
        assert len(owned.owner().inverse.secondary_to_add)
        owned.owner().save()
        assert not len(owned.owner().secondary_to_add)
        assert not len(owned.owner().inverse.secondary_to_add)

        # now test when inverse is HasMany
        self.OwnedModel.owner = relations.belongs_to(
            self.OwnedModel,
            self.OwnerModel,
            'owner_id',
            True
        )

        owner = self.OwnerModel.insert({'details': '321'})
        owner2 = self.OwnerModel.insert({'details': '123'})
        owned = self.OwnedModel.insert({'details': '321'})
        owned.owner = owner
        assert len(owned.owner().inverse.secondary_to_add)
        owned.owner().save()

        assert owned.owner().inverse.primary.data == owned.owner.data
        assert owned.owner.data == owner.data
        assert not len(owned.owner().inverse.secondary_to_add)
        assert isinstance(owned.owner().inverse.secondary, tuple)

        owned.owner = owner2
        assert owned.owner().inverse.primary.data == owner2.data
        assert len(owned.owner().secondary_to_add)
        assert len(owned.owner().inverse.secondary_to_add)
        owned.owner().save()
        assert not len(owned.owner().secondary_to_add)
        assert not len(owned.owner().inverse.secondary_to_add)

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

    def test_belongs_to_many_function_sets_inverse(self):
        self.OwnerModel.owned = relations.belongs_to_many(
            self.OwnerModel,
            self.OwnedModel,
            Pivot,
            'first_id',
            'second_id'
        )

        owner = self.OwnerModel.insert({'details': '321'})
        owned = self.OwnedModel.insert({'details': '321'})
        owner.owned = [owned]

        assert hasattr(owner.owned(), 'inverse')
        assert isinstance(owner.owned().inverse, list)
        for inverse in owner.owned().inverse:
            assert isinstance(inverse, relations.BelongsToMany)

    def test_belongs_to_many_function_inverse_sets_primary_and_secondary(self):
        self.OwnerModel.owned = relations.belongs_to_many(
            self.OwnerModel,
            self.OwnedModel,
            Pivot,
            'first_id',
            'second_id'
        )

        owner = self.OwnerModel.insert({'details': '321'})
        owned = self.OwnedModel.insert({'details': '321'})
        owner.owned = [owned]

        assert owner.owned().inverse[0].primary.data == owner.owned[0].data
        assert owner.owned().inverse[0].secondary[0].data == owner.data

    def test_BelongsToMany_changes_affect_inverses(self):
        self.OwnerModel.owned = relations.belongs_to_many(
            self.OwnerModel,
            self.OwnedModel,
            Pivot,
            'first_id',
            'second_id'
        )

        owner = self.OwnerModel.insert({'details': '321'})
        owned = self.OwnedModel.insert({'details': '321'})
        owned2 = self.OwnedModel.insert({'details': '123'})
        owner.owned = [owned]
        assert len(owner.owned().inverse[0].secondary_to_add)
        owner.owned().save()

        assert owner.owned().inverse[0].primary.data == owner.owned[0].data
        assert owner.owned[0].data == owned.data
        assert not len(owner.owned().inverse[0].secondary_to_add)

        owner.owned = [owned2]
        assert owner.owned().inverse[0].primary.data == owned2.data
        assert len(owner.owned().secondary_to_add)
        assert len(owner.owned().inverse[0].secondary_to_add)
        owner.owned().save()
        assert not len(owner.owned().secondary_to_add)
        assert not len(owner.owned().inverse[0].secondary_to_add)

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


if __name__ == '__main__':
    unittest.main()
