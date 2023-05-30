from context import classes, interfaces, relations
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
        primary = self.OwnerModel.insert({'data': '1234'})
        secondary = self.OwnedModel.insert({'data': '321'})
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
        assert str(e.exception) == 'primary must be instance of OwnerModel'

        with self.assertRaises(AssertionError) as e:
            relation.secondary_model_precondition('not a ModelProtocol')
        assert str(e.exception) == 'secondary must be instance of OwnedModel'

        with self.assertRaises(AssertionError) as e:
            relation.pivot_preconditions('not a type')
        assert str(e.exception) == 'pivot must be class implementing ModelProtocol'

    def test_Relation_set_primary_sets_primary(self):
        relation = relations.Relation(
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        primary = self.OwnerModel.insert({'data': '123abc'})

        with self.assertRaises(AssertionError) as e:
            relation.primary = 'not a primary class'
        assert str(e.exception) == 'model must implement ModelProtocol'

        assert relation.primary is None
        relation.set_primary(primary)
        assert relation.primary is primary

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
        self.OwnerModel.owned = hasone.create_property()

        owner = self.OwnerModel({'data': '123'})
        owned = self.OwnedModel({'data': '321'})

        assert owner.owned is None
        owner.owned = owned
        assert owner.owned is not None
        assert type(owner.owned) is not type(owned)
        assert owner.owned.data == owned.data

        assert callable(owner.owned)
        assert type(owner.owned()) is relations.HasOne

    def test_HasOne_save_changes_only_foreign_id_field_in_db(self):
        hasone = relations.HasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        self.OwnerModel.owned = hasone.create_property()

        owner = self.OwnerModel.insert({'data': '123'})
        owned = self.OwnedModel.insert({'data': '321'})
        owner.owned = owned
        owner.owned.data['data'] = 'abc'
        owner.owned().save()

        owned.reload()
        assert owned.data['data'] == '321'
        assert owned.data['owner_id'] == owner.data['id']

    def test_has_one_function_sets_property_from_HasOne(self):
        self.OwnerModel.owned = relations.has_one(
            self.OwnerModel,
            self.OwnedModel,
            'owner_id'
        )

        assert type(self.OwnerModel.owned) is property

        owner = self.OwnerModel.insert({'data': '321'})
        owned = self.OwnedModel.insert({'data': '321'})
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

        owner1 = self.OwnerModel.insert({'data': 'owner1'})
        owner2 = self.OwnerModel.insert({'data': 'owner2'})
        owned1 = self.OwnedModel.insert({'data': 'owned1'})
        owned2 = self.OwnedModel.insert({'data': 'owned2'})

        owner1.owned = owned1
        owner1.owned().save()

        owner2.owned = owned2
        owner2.owned().save()

        assert owner1.relations != owner2.relations
        assert owner1.owned() is not owner2.owned()
        assert owner1.owned.data['id'] == owned1.data['id']
        assert owner2.owned.data['id'] == owned2.data['id']

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

        with self.assertRaises(AssertionError) as e:
            relations.HasMany(
                b'not a str',
                primary_class=self.OwnerModel,
                secondary_class=self.OwnedModel
            )
        assert str(e.exception) == 'foreign_id_field must be str'

    def test_HasMany_sets_primary_and_secondary_correctly(self):
        hasmany = relations.HasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        primary = self.OwnerModel.insert({'data': '321ads'})
        secondary = self.OwnedModel.insert({'data':'321'})

        assert hasmany.primary is None
        hasmany.primary = primary
        assert hasmany.primary is primary

        with self.assertRaises(AssertionError) as e:
            hasmany.secondary = secondary
        assert str(e.exception) == 'must be a list of ModelProtocol'

        with self.assertRaises(AssertionError) as e:
            hasmany.secondary = [self.OwnerModel({'data': '1234f'})]
        assert str(e.exception) == 'secondary must be instance of OwnedModel'

        assert hasmany.secondary is None
        hasmany.secondary = [secondary]
        assert hasmany.secondary == (secondary,)

    def test_HasMany_get_cache_key_includes_foreign_id_field(self):
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

        with self.assertRaises(AssertionError) as e:
            hasmany.save()
        assert str(e.exception) == 'cannot save incomplete HasMany'

    def test_HasMany_save_changes_foreign_id_field_on_secondary(self):
        hasmany = relations.HasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        primary = self.OwnerModel.insert({'data': '321ads'})
        secondary = self.OwnedModel.insert({'data':'321'})

        hasmany.primary = primary
        hasmany.secondary = [secondary]

        assert secondary.data['owner_id'] == None
        hasmany.save()
        assert secondary.data['owner_id'] == primary.data['id']

        reloaded = self.OwnedModel.find(secondary.data['id'])
        assert reloaded.data['owner_id'] == primary.data['id']

    def test_HasMany_changing_primary_and_secondary_updates_models_correctly(self):
        hasmany = relations.HasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        primary1 = self.OwnerModel.insert({'data': '321ads'})
        primary2 = self.OwnerModel.insert({'data': '12332'})
        secondary1 = self.OwnedModel.insert({'data':'321'})
        secondary2 = self.OwnedModel.insert({'data':'afgbfb'})

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
        assert secondary1.data['owner_id'] == ''

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

        owner = self.OwnerModel({'data': '123'})
        owned = self.OwnedModel({'data': '321'})

        assert owner.owned is None
        owner.owned = [owned]
        assert owner.owned is not None
        assert isinstance(owner.owned, tuple)
        assert owner.owned[0].data == owned.data

        assert callable(owner.owned)
        assert type(owner.owned()) is relations.HasMany

    def test_HasMany_save_changes_only_foreign_id_field_in_db(self):
        hasmany = relations.HasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        self.OwnerModel.owned = hasmany.create_property()

        owner = self.OwnerModel.insert({'data': '123'})
        owned = self.OwnedModel.insert({'data': '321'})
        owner.owned = [owned]
        owner.owned[0].data['data'] = 'abc'
        owner.owned().save()

        owned.reload()
        assert owned.data['data'] == '321'
        assert owned.data['owner_id'] == owner.data['id']

    def test_has_many_function_sets_property_from_HasMany(self):
        self.OwnerModel.owned = relations.has_many(
            self.OwnerModel,
            self.OwnedModel,
            'owner_id'
        )

        assert type(self.OwnerModel.owned) is property

        owner = self.OwnerModel.insert({'data': '321'})
        owned = self.OwnedModel.insert({'data': '321'})
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

        owner1 = self.OwnerModel.insert({'data': 'owner1'})
        owner2 = self.OwnerModel.insert({'data': 'owner2'})
        owned1 = self.OwnedModel.insert({'data': 'owned1'})
        owned2 = self.OwnedModel.insert({'data': 'owned2'})

        owner1.owned = [owned1]
        owner1.owned().save()

        owner2.owned = [owned2]
        owner2.owned().save()

        assert owner1.relations != owner2.relations
        assert owner1.owned() is not owner2.owned()
        assert owner1.owned[0].data['id'] == owned1.data['id']
        assert owner2.owned[0].data['id'] == owned2.data['id']

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

        with self.assertRaises(AssertionError) as e:
            relations.BelongsTo(
                b'not a str',
                primary_class=self.OwnerModel,
                secondary_class=self.OwnedModel
            )
        assert str(e.exception) == 'foreign_id_field must be str'

    def test_BelongsTo_sets_primary_and_secondary_correctly(self):
        belongsto = relations.BelongsTo(
            'owner_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        primary = self.OwnedModel.insert({'data': '321ads'})
        secondary = self.OwnerModel.insert({'data':'321'})

        assert belongsto.primary is None
        belongsto.primary = primary
        assert belongsto.primary is primary

        with self.assertRaises(AssertionError) as e:
            belongsto.secondary = primary
        assert str(e.exception) == 'secondary must be instance of OwnerModel'

        assert belongsto.secondary is None
        belongsto.secondary = secondary
        assert belongsto.secondary == secondary

    def test_BelongsTo_get_cache_key_includes_foreign_id_field(self):
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

        with self.assertRaises(AssertionError) as e:
            belongsto.save()
        assert str(e.exception) == 'cannot save incomplete BelongsTo'

    def test_BelongsTo_save_changes_foreign_id_field_on_secondary(self):
        belongsto = relations.BelongsTo(
            'owner_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        primary = self.OwnedModel.insert({'data': '321ads'})
        secondary = self.OwnerModel.insert({'data':'321'})

        belongsto.primary = primary
        belongsto.secondary = secondary

        assert primary.data['owner_id'] == None
        belongsto.save()
        assert primary.data['owner_id'] == secondary.data['id']

        reloaded = self.OwnedModel.find(primary.data['id'])
        assert reloaded.data['owner_id'] == secondary.data['id']

    def test_BelongsTo_changing_primary_and_secondary_updates_models_correctly(self):
        belongsto = relations.BelongsTo(
            'owner_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        primary1 = self.OwnedModel.insert({'data': '321ads'})
        primary2 = self.OwnedModel.insert({'data': '12332'})
        secondary1 = self.OwnerModel.insert({'data':'321'})
        secondary2 = self.OwnerModel.insert({'data':'afgbfb'})

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
        assert primary1.data['owner_id'] == ''

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

        owned = self.OwnedModel({'data': '321'})
        owner = self.OwnerModel({'data': '123'})

        assert owned.owner is None
        owned.owner = owner
        assert owned.owner is not None
        assert isinstance(owned.owner, self.OwnerModel)
        assert owned.owner.data == owner.data

        assert callable(owned.owner)
        assert type(owned.owner()) is relations.BelongsTo

    def test_BelongsTo_save_changes_only_foreign_id_field_in_db(self):
        belongsto = relations.BelongsTo(
            'owner_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        self.OwnedModel.owner = belongsto.create_property()

        owned = self.OwnedModel.insert({'data': '123'})
        owner = self.OwnerModel.insert({'data': '321'})
        owned.owner = owner
        owned.owner.data['data'] = 'abc'
        owned.owner().save()

        owner.reload()
        assert owner.data['data'] == '321'
        assert owned.data['owner_id'] == owner.data['id']

    def test_belongs_to_function_sets_property_from_BelongsTo(self):
        self.OwnedModel.owner = relations.belongs_to(
            self.OwnedModel,
            self.OwnerModel,
            'owner_id'
        )

        assert type(self.OwnedModel.owner) is property

        owned = self.OwnedModel.insert({'data': '321'})
        owner = self.OwnerModel.insert({'data': '123'})
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

        owned1 = self.OwnedModel.insert({'data': 'owned1'})
        owned2 = self.OwnedModel.insert({'data': 'owned2'})
        owner1 = self.OwnerModel.insert({'data': 'owner1'})
        owner2 = self.OwnerModel.insert({'data': 'owner2'})

        owned1.owner = owner1
        owned1.owner().save()

        owned2.owner = owner2
        owned2.owner().save()

        assert owner1.relations != owner2.relations
        assert owned1.owner() is not owned2.owner()
        assert owned1.owner.data['id'] == owner1.data['id']
        assert owned2.owner.data['id'] == owner2.data['id']


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

        with self.assertRaises(AssertionError) as e:
            relations.BelongsToMany(
                Pivot,
                b'not a str',
                'second_id'
            )
        assert str(e.exception) == 'primary_id_field and secondary_id_field must be str'

    def test_BelongsToMany_sets_primary_and_secondary_correctly(self):
        belongstomany = relations.BelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        primary = self.OwnedModel.insert({'data': '321ads'})
        secondary = self.OwnerModel.insert({'data':'321'})

        assert belongstomany.primary is None
        belongstomany.primary = primary
        assert belongstomany.primary is primary

        with self.assertRaises(AssertionError) as e:
            belongstomany.secondary = secondary
        assert str(e.exception) == 'must be a list of ModelProtocol'

        with self.assertRaises(AssertionError) as e:
            belongstomany.secondary = [primary]
        assert str(e.exception) == 'secondary must be instance of OwnerModel'

        assert belongstomany.secondary is None
        belongstomany.secondary = [secondary]
        assert belongstomany.secondary[0] == secondary

    def test_BelongsToMany_get_cache_key_includes_foreign_id_field(self):
        belongstomany = relations.BelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        cache_key = belongstomany.get_cache_key()
        assert cache_key == 'OwnedModel_BelongsToMany_OwnerModel_Pivot'

    def test_BelongsToMany_save_raises_error_for_incomplete_relation(self):
        belongstomany = relations.BelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )

        with self.assertRaises(AssertionError) as e:
            belongstomany.save()
        assert str(e.exception) == 'cannot save incomplete BelongsToMany'

    def test_BelongsToMany_save_changes_foreign_id_field_on_secondary(self):
        belongstomany = relations.BelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        primary = self.OwnedModel.insert({'data': '321ads'})
        secondary = self.OwnerModel.insert({'data':'321'})

        belongstomany.primary = primary
        belongstomany.secondary = [secondary]

        assert Pivot.query().count() == 0
        belongstomany.save()
        assert Pivot.query().count() == 1
        belongstomany.save()
        assert Pivot.query().count() == 1

    def test_BelongsToMany_changing_primary_and_secondary_updates_models_correctly(self):
        belongstomany = relations.BelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        primary1 = self.OwnedModel.insert({'data': '321ads'})
        primary2 = self.OwnedModel.insert({'data': '12332'})
        secondary1 = self.OwnerModel.insert({'data':'321'})
        secondary2 = self.OwnerModel.insert({'data':'afgbfb'})

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

        owned = self.OwnedModel({'data': '321'})
        owner = self.OwnerModel({'data': '123'})

        assert owned.owners is None
        owned.owners = [owner]
        assert owned.owners is not None
        assert isinstance(owned.owners, tuple)
        assert owned.owners[0].data == owner.data

        assert callable(owned.owners)
        assert type(owned.owners()) is relations.BelongsToMany


if __name__ == '__main__':
    unittest.main()
