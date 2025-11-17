from __future__ import annotations
from asyncio import run
from context import async_classes, errors, async_interfaces, async_relations
from genericpath import isfile
import aiosqlite
import os
import unittest


DB_FILEPATH = 'test.db'

async def connect(path):
    return await aiosqlite.connect(path)


class Pivot(async_classes.AsyncSqlModel):
    connection_info: str = DB_FILEPATH
    table: str = 'pivot'
    columns: tuple = ('id', 'first_id', 'second_id')


class TestRelations(unittest.TestCase):
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
        run(self.cursor.execute('create table pivot (id text, first_id text, second_id text)'))
        run(self.cursor.execute('create table owners (id text, details text)'))
        run(self.cursor.execute('create table owned (id text, owner_id text, details text)'))
        run(self.cursor.execute('create table dag (id text, details text, parent_ids text)'))
        run(self.cursor.execute('create table deleted_records (id text not null, ' +
            'model_class text not null, record_id text not null, ' +
            'record blob not null, timestamp text not null)'))

        # rebuild test async_classes because properties will be changed in tests
        class OwnedModel(async_classes.AsyncSqlModel):
            connection_info: str = DB_FILEPATH
            table: str = 'owned'
            columns: tuple = ('id', 'owner_id', 'details')

        class OwnerModel(async_classes.AsyncSqlModel):
            connection_info: str = DB_FILEPATH
            table: str = 'owners'
            columns: tuple = ('id', 'details')

        class DAGItem(async_classes.AsyncHashedModel):
            connection_info: str = DB_FILEPATH
            table: str = 'dag'
            columns: tuple = ('id', 'details', 'parent_ids')
            parents: async_interfaces.AsyncRelatedCollection
            children: async_interfaces.AsyncRelatedCollection

            @classmethod
            async def insert(cls, data: dict) -> DAGItem|None:
                # """For better type hinting."""
                return await super().insert(data)

        self.OwnedModel = OwnedModel
        self.OwnerModel = OwnerModel
        self.DAGItem = DAGItem
        async_classes.AsyncDeletedModel.connection_info = DB_FILEPATH

        return super().setUp()

    def tearDown(self) -> None:
        """Close cursor and delete test database."""
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

    # Relation tests
    def test_AsyncRelation_implements_AsyncRelationProtocol(self):
        assert isinstance(async_relations.AsyncRelation, async_interfaces.AsyncRelationProtocol)

    def test_AsyncRelation_initializes_properly(self):
        primary = run(self.OwnerModel.insert({'details': '1234'}))
        secondary = run(self.OwnedModel.insert({'details': '321'}))
        relation = async_relations.AsyncRelation(
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel,
            primary=primary,
            secondary=secondary
        )
        assert type(relation) is async_relations.AsyncRelation

        relation = async_relations.AsyncRelation(
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        assert type(relation) is async_relations.AsyncRelation

    def test_AsyncRelation_precondition_check_methods_raise_errors(self):
        relation = async_relations.AsyncRelation(
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )

        with self.assertRaises(TypeError) as e:
            relation.single_model_precondition('not a AsyncModelProtocol')
        assert str(e.exception) == 'model must implement AsyncModelProtocol'

        with self.assertRaises(TypeError) as e:
            relation.multi_model_precondition('not a list of AsyncModelProtocol')
        assert str(e.exception) == 'must be a list of AsyncModelProtocol'

        with self.assertRaises(TypeError) as e:
            relation.multi_model_precondition(['not a AsyncModelProtocol'])
        assert str(e.exception) == 'must be a list of AsyncModelProtocol'

        with self.assertRaises(TypeError) as e:
            relation.primary_model_precondition('not a AsyncModelProtocol')
        assert str(e.exception) == 'primary must be instance of OwnerModel'

        with self.assertRaises(TypeError) as e:
            relation.secondary_model_precondition('not a AsyncModelProtocol')
        assert str(e.exception) == 'secondary must be instance of OwnedModel'

        with self.assertRaises(TypeError) as e:
            relation.pivot_preconditions('not a type')
        assert str(e.exception) == 'pivot must be class implementing AsyncModelProtocol'

    def test_AsyncRelation_get_cache_key_returns_str_containing_class_names(self):
        relation = async_relations.AsyncRelation(
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )

        cache_key = relation.get_cache_key()
        assert type(cache_key) is str
        assert cache_key == 'OwnerModel_AsyncRelation_OwnedModel'

    # AsyncHasOne tests
    def test_AsyncHasOne_extends_Relation(self):
        assert issubclass(async_relations.AsyncHasOne, async_relations.AsyncRelation)

    def test_AsyncHasOne_initializes_properly(self):
        Asynchasone = async_relations.AsyncHasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        assert isinstance(Asynchasone, async_relations.AsyncHasOne)

        with self.assertRaises(TypeError) as e:
            async_relations.AsyncHasOne(
                b'not a str',
                primary_class=self.OwnerModel,
                secondary_class=self.OwnedModel
            )
        assert str(e.exception) == 'foreign_id_column must be str'

    def test_AsyncHasOne_sets_primary_and_secondary_correctly(self):
        Asynchasone = async_relations.AsyncHasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        primary = run(self.OwnerModel.insert({'details': '321ads'}))
        secondary = run(self.OwnedModel.insert({'details':'321'}))

        assert Asynchasone.primary is None
        Asynchasone.primary = primary
        assert Asynchasone.primary is primary

        with self.assertRaises(TypeError) as e:
            Asynchasone.secondary = 'not a AsyncModelProtocol'
        assert str(e.exception) == 'model must implement AsyncModelProtocol'

        with self.assertRaises(TypeError) as e:
            Asynchasone.secondary = self.OwnerModel({'details': '1234f'})
        assert str(e.exception) == 'secondary must be instance of OwnedModel'

        assert Asynchasone.secondary is None
        Asynchasone.secondary = secondary
        assert Asynchasone.secondary is secondary

    def test_AsyncHasOne_get_cache_key_includes_foreign_id_column(self):
        Asynchasone = async_relations.AsyncHasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        cache_key = Asynchasone.get_cache_key()
        assert cache_key == 'OwnerModel_AsyncHasOne_OwnedModel_owner_id'

    def test_AsyncHasOne_save_raises_error_for_incomplete_relation(self):
        Asynchasone = async_relations.AsyncHasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )

        with self.assertRaises(errors.UsageError) as e:
            run(Asynchasone.save())
        assert str(e.exception) == 'cannot save incomplete AsyncHasOne'

    def test_AsyncHasOne_save_changes_foreign_id_column_on_secondary(self):
        Asynchasone = async_relations.AsyncHasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        primary = run(self.OwnerModel.insert({'details': '321ads'}))
        secondary = run(self.OwnedModel.insert({'details':'321'}))

        Asynchasone.primary = primary
        Asynchasone.secondary = secondary

        assert secondary.data['owner_id'] == None
        run(Asynchasone.save())
        assert secondary.data['owner_id'] == primary.data['id']

        reloaded = run(self.OwnedModel.find(secondary.data['id']))
        assert reloaded.data['owner_id'] == primary.data['id']

    def test_AsyncHasOne_save_unsets_change_tracking_properties(self):
        Asynchasone = async_relations.AsyncHasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        primary = run(self.OwnerModel.insert({'details': '321ads'}))
        primary2 = run(self.OwnerModel.insert({'details': 'sdsdsd'}))
        secondary = run(self.OwnedModel.insert({'details':'321'}))
        secondary2 = run(self.OwnedModel.insert({'details':'321asds'}))

        Asynchasone.primary = primary
        Asynchasone.secondary = secondary
        run(Asynchasone.save())
        Asynchasone.primary = primary2

        assert Asynchasone.primary_to_add is not None
        assert Asynchasone.primary_to_remove is not None
        run(Asynchasone.save())
        assert Asynchasone.primary_to_add is None
        assert Asynchasone.primary_to_remove is None

        Asynchasone.secondary = secondary2
        assert len(Asynchasone.secondary_to_add)
        assert len(Asynchasone.secondary_to_remove)
        run(Asynchasone.save())
        assert not len(Asynchasone.secondary_to_add)
        assert not len(Asynchasone.secondary_to_remove)

    def test_AsyncHasOne_changing_primary_and_secondary_updates_models_correctly(self):
        Asynchasone = async_relations.AsyncHasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        primary1 = run(self.OwnerModel.insert({'details': '321ads'}))
        primary2 = run(self.OwnerModel.insert({'details': '12332'}))
        secondary1 = run(self.OwnedModel.insert({'details':'321'}))
        secondary2 = run(self.OwnedModel.insert({'details':'afgbfb'}))

        Asynchasone.primary = primary1
        Asynchasone.secondary = secondary1
        run(Asynchasone.save())
        assert secondary1.data['owner_id'] == primary1.data['id']

        Asynchasone.primary = primary2
        run(Asynchasone.save())
        assert secondary1.data['owner_id'] == primary2.data['id']

        Asynchasone.secondary = secondary2
        run(Asynchasone.save())
        assert secondary2.data['owner_id'] == primary2.data['id']
        assert not secondary1.data['owner_id']

    def test_AsyncHasOne_create_property_returns_property(self):
        Asynchasone = async_relations.AsyncHasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        prop = Asynchasone.create_property()

        assert type(prop) is property

    def test_AsyncHasOne_property_wraps_input_class(self):
        Asynchasone = async_relations.AsyncHasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        self.OwnerModel.owned = Asynchasone.create_property()

        owner = self.OwnerModel({'details': '123'})
        owned = self.OwnedModel({'details': '321'})

        assert not owner.owned
        owner.owned = owned
        assert owner.owned
        assert type(owner.owned) is not type(owned)
        assert owner.owned.data == owned.data

        assert callable(owner.owned)
        assert type(owner.owned()) is async_relations.AsyncHasOne

    def test_AsyncHasOne_save_changes_only_foreign_id_column_in_db(self):
        Asynchasone = async_relations.AsyncHasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        self.OwnerModel.owned = Asynchasone.create_property()

        owner = run(self.OwnerModel.insert({'details': '123'}))
        owned = run(self.OwnedModel.insert({'details': '321'}))
        owner.owned = owned
        owner.owned.data['details'] = 'abc'
        run(owner.owned().save())

        run(owned.reload())
        assert owned.data['details'] == '321'
        assert owned.data['owner_id'] == owner.data['id']

    def test_async_has_one_function_sets_property_from_AsyncHasOne(self):
        self.OwnerModel.owned = async_relations.async_has_one(
            self.OwnerModel,
            self.OwnedModel,
            'owner_id'
        )

        assert type(self.OwnerModel.owned) is property

        owner = run(self.OwnerModel.insert({'details': '321'}))
        owned = run(self.OwnedModel.insert({'details': '321'}))
        owner.owned = owned

        assert callable(owner.owned)
        assert type(owner.owned()) is async_relations.AsyncHasOne

        run(owner.owned().save())

    def test_AsyncHasOne_works_with_multiple_instances(self):
        self.OwnerModel.owned = async_relations.async_has_one(
            self.OwnerModel,
            self.OwnedModel,
            'owner_id'
        )

        owner1 = run(self.OwnerModel.insert({'details': 'owner1'}))
        owner2 = run(self.OwnerModel.insert({'details': 'owner2'}))
        owned1 = run(self.OwnedModel.insert({'details': 'owned1'}))
        owned2 = run(self.OwnedModel.insert({'details': 'owned2'}))

        owner1.owned = owned1
        run(owner1.owned().save())

        owner2.owned = owned2
        run(owner2.owned().save())

        assert owner1.relations != owner2.relations
        assert owner1.owned() is not owner2.owned()
        assert owner1.owned.data['id'] == owned1.data['id']
        assert owner2.owned.data['id'] == owned2.data['id']

    def test_AsyncHasOne_reload_raises_ValueError_for_empty_relation(self):
        Asynchasone = async_relations.AsyncHasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )

        with self.assertRaises(ValueError) as e:
            run(Asynchasone.reload())
        assert str(e.exception) == 'cannot reload an empty relation'

    def test_async_has_one_related_property_loads_on_first_read(self):
        self.OwnerModel.owned = async_relations.async_has_one(
            self.OwnerModel,
            self.OwnedModel,
            'owner_id'
        )

        owner = run(self.OwnerModel.insert({'details': '321'}))
        owned = run(self.OwnedModel.insert({
            'details': '321',
            'owner_id': owner.id,
        }))
        assert owner.owned
        assert owner.owned.id == owned.id

    # AsyncHasMany tests
    def test_AsyncHasMany_extends_Relation(self):
        assert issubclass(async_relations.AsyncHasMany, async_relations.AsyncRelation)

    def test_AsyncHasMany_initializes_properly(self):
        hasmany = async_relations.AsyncHasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        assert isinstance(hasmany, async_relations.AsyncHasMany)

        with self.assertRaises(TypeError) as e:
            async_relations.AsyncHasMany(
                b'not a str',
                primary_class=self.OwnerModel,
                secondary_class=self.OwnedModel
            )
        assert str(e.exception) == 'foreign_id_column must be str'

    def test_AsyncHasMany_sets_primary_and_secondary_correctly(self):
        hasmany = async_relations.AsyncHasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        primary = run(self.OwnerModel.insert({'details': '321ads'}))
        secondary = run(self.OwnedModel.insert({'details':'321'}))

        assert hasmany.primary is None
        hasmany.primary = primary
        assert hasmany.primary is primary

        with self.assertRaises(TypeError) as e:
            hasmany.secondary = secondary
        assert str(e.exception) == 'must be a list of AsyncModelProtocol'

        with self.assertRaises(TypeError) as e:
            hasmany.secondary = [self.OwnerModel({'details': '1234f'})]
        assert str(e.exception) == 'secondary must be instance of OwnedModel'

        assert hasmany.secondary is None
        hasmany.secondary = [secondary]
        assert hasmany.secondary == (secondary,)

    def test_AsyncHasMany_get_cache_key_includes_foreign_id_column(self):
        hasmany = async_relations.AsyncHasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        cache_key = hasmany.get_cache_key()
        assert cache_key == 'OwnerModel_AsyncHasMany_OwnedModel_owner_id'

    def test_AsyncHasMany_save_raises_error_for_incomplete_relation(self):
        hasmany = async_relations.AsyncHasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )

        with self.assertRaises(errors.UsageError) as e:
            run(hasmany.save())
        assert str(e.exception) == 'cannot save incomplete AsyncHasMany'

    def test_AsyncHasMany_save_changes_foreign_id_column_on_secondary(self):
        hasmany = async_relations.AsyncHasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        primary = run(self.OwnerModel.insert({'details': '321ads'}))
        secondary = run(self.OwnedModel.insert({'details':'321'}))

        hasmany.primary = primary
        hasmany.secondary = [secondary]

        assert secondary.data['owner_id'] == None
        run(hasmany.save())
        assert secondary.data['owner_id'] == primary.data['id']

        reloaded = run(self.OwnedModel.find(secondary.data['id']))
        assert reloaded.data['owner_id'] == primary.data['id']

    def test_AsyncHasMany_save_unsets_change_tracking_properties(self):
        hasmany = async_relations.AsyncHasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        primary = run(self.OwnerModel.insert({'details': '321ads'}))
        primary2 = run(self.OwnerModel.insert({'details': 'sdsdsd'}))
        secondary = run(self.OwnedModel.insert({'details':'321'}))
        secondary2 = run(self.OwnedModel.insert({'details':'321asds'}))

        hasmany.primary = primary
        hasmany.secondary = [secondary]
        run(hasmany.save())
        hasmany.primary = primary2

        assert hasmany.primary_to_add is not None
        assert hasmany.primary_to_remove is not None
        run(hasmany.save())
        assert hasmany.primary_to_add is None
        assert hasmany.primary_to_remove is None

        hasmany.secondary = [secondary2]
        assert len(hasmany.secondary_to_add)
        assert len(hasmany.secondary_to_remove)
        run(hasmany.save())
        assert not len(hasmany.secondary_to_add)
        assert not len(hasmany.secondary_to_remove)

    def test_AsyncHasMany_changing_primary_and_secondary_updates_models_correctly(self):
        hasmany = async_relations.AsyncHasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        primary1 = run(self.OwnerModel.insert({'details': '321ads'}))
        primary2 = run(self.OwnerModel.insert({'details': '12332'}))
        secondary1 = run(self.OwnedModel.insert({'details':'321'}))
        secondary2 = run(self.OwnedModel.insert({'details':'afgbfb'}))

        hasmany.primary = primary1
        hasmany.secondary = [secondary1]
        run(hasmany.save())
        assert secondary1.data['owner_id'] == primary1.data['id']

        hasmany.primary = primary2
        run(hasmany.save())
        assert secondary1.data['owner_id'] == primary2.data['id']

        hasmany.secondary = [secondary2]
        run(hasmany.save())
        assert secondary2.data['owner_id'] == primary2.data['id']
        assert not secondary1.data['owner_id']

    def test_AsyncHasMany_create_property_returns_property(self):
        hasmany = async_relations.AsyncHasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        prop = hasmany.create_property()

        assert type(prop) is property

    def test_AsyncHasMany_property_wraps_input_tuple(self):
        hasmany = async_relations.AsyncHasMany(
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
        assert type(owner.owned()) is async_relations.AsyncHasMany

    def test_AsyncHasMany_save_changes_only_foreign_id_column_in_db(self):
        hasmany = async_relations.AsyncHasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        self.OwnerModel.owned = hasmany.create_property()

        owner = run(self.OwnerModel.insert({'details': '123'}))
        owned = run(self.OwnedModel.insert({'details': '321'}))
        owner.owned = [owned]
        owner.owned[0].data['details'] = 'abc'
        run(owner.owned().save())

        run(owned.reload())
        assert owned.data['details'] == '321'
        assert owned.data['owner_id'] == owner.data['id']

    def test_async_has_many_function_sets_property_from_AsyncHasMany(self):
        self.OwnerModel.owned = async_relations.async_has_many(
            self.OwnerModel,
            self.OwnedModel,
            'owner_id'
        )

        assert type(self.OwnerModel.owned) is property

        owner = run(self.OwnerModel.insert({'details': '321'}))
        owned = run(self.OwnedModel.insert({'details': '321'}))
        owner.owned = [owned]

        assert callable(owner.owned)
        assert type(owner.owned()) is async_relations.AsyncHasMany

        run(owner.owned().save())

    def test_AsyncHasMany_works_with_multiple_instances(self):
        self.OwnerModel.owned = async_relations.async_has_many(
            self.OwnerModel,
            self.OwnedModel,
            'owner_id'
        )

        owner1 = run(self.OwnerModel.insert({'details': 'owner1'}))
        owner2 = run(self.OwnerModel.insert({'details': 'owner2'}))
        owned1 = run(self.OwnedModel.insert({'details': 'owned1'}))
        owned2 = run(self.OwnedModel.insert({'details': 'owned2'}))

        owner1.owned = [owned1]
        run(owner1.owned().save())

        owner2.owned = [owned2]
        run(owner2.owned().save())

        assert owner1.relations != owner2.relations
        assert owner1.owned() is not owner2.owned()
        assert owner1.owned[0].data['id'] == owned1.data['id']
        assert owner2.owned[0].data['id'] == owned2.data['id']

    def test_AsyncHasMany_reload_raises_ValueError_for_empty_relation(self):
        hasmany = async_relations.AsyncHasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel,
        )

        with self.assertRaises(ValueError) as e:
            run(hasmany.reload())
        assert str(e.exception) == 'cannot reload an empty relation'

    def test_async_has_many_related_property_loads_on_first_read(self):
        self.OwnerModel.owned = async_relations.async_has_many(
            self.OwnerModel,
            self.OwnedModel,
            'owner_id'
        )

        owner = run(self.OwnerModel.insert({'details': '321'}))
        owned = run(self.OwnedModel.insert({
            'details': '321',
            'owner_id': owner.id,
        }))

        assert len(owner.owned) == 1
        assert owner.owned[0].id == owned.id

    # AsyncBelongsTo tests
    def test_AsyncBelongsTo_extends_Relation(self):
        assert issubclass(async_relations.AsyncBelongsTo, async_relations.AsyncRelation)

    def test_AsyncBelongsTo_initializes_properly(self):
        belongsto = async_relations.AsyncBelongsTo(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel
        )
        assert isinstance(belongsto, async_relations.AsyncBelongsTo)

        with self.assertRaises(TypeError) as e:
            async_relations.AsyncBelongsTo(
                b'not a str',
                primary_class=self.OwnerModel,
                secondary_class=self.OwnedModel
            )
        assert str(e.exception) == 'foreign_id_column must be str'

    def test_AsyncBelongsTo_sets_primary_and_secondary_correctly(self):
        belongsto = async_relations.AsyncBelongsTo(
            'owner_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        primary = run(self.OwnedModel.insert({'details': '321ads'}))
        secondary = run(self.OwnerModel.insert({'details':'321'}))

        assert belongsto.primary is None
        belongsto.primary = primary
        assert belongsto.primary is primary

        with self.assertRaises(TypeError) as e:
            belongsto.secondary = primary
        assert str(e.exception) == 'secondary must be instance of OwnerModel'

        assert belongsto.secondary is None
        belongsto.secondary = secondary
        assert belongsto.secondary == secondary

    def test_AsyncBelongsTo_get_cache_key_includes_foreign_id_column(self):
        belongsto = async_relations.AsyncBelongsTo(
            'owner_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        cache_key = belongsto.get_cache_key()
        assert cache_key == 'OwnedModel_AsyncBelongsTo_OwnerModel_owner_id'

    def test_AsyncBelongsTo_save_raises_error_for_incomplete_relation(self):
        belongsto = async_relations.AsyncBelongsTo(
            'owner_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )

        with self.assertRaises(errors.UsageError) as e:
            run(belongsto.save())
        assert str(e.exception) == 'cannot save incomplete AsyncBelongsTo'

    def test_AsyncBelongsTo_save_changes_foreign_id_column_on_secondary(self):
        belongsto = async_relations.AsyncBelongsTo(
            'owner_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        primary = run(self.OwnedModel.insert({'details': '321ads'}))
        secondary = run(self.OwnerModel.insert({'details':'321'}))

        belongsto.primary = primary
        belongsto.secondary = secondary

        assert primary.data['owner_id'] == None
        run(belongsto.save())
        assert primary.data['owner_id'] == secondary.data['id']

        reloaded = run(self.OwnedModel.find(primary.data['id']))
        assert reloaded.data['owner_id'] == secondary.data['id']

    def test_AsyncBelongsTo_save_unsets_change_tracking_properties(self):
        belongsto = async_relations.AsyncBelongsTo(
            'owner_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        primary = run(self.OwnedModel.insert({'details':'321'}))
        primary2 = run(self.OwnedModel.insert({'details':'321asds'}))
        secondary = run(self.OwnerModel.insert({'details': '321ads'}))
        secondary2 = run(self.OwnerModel.insert({'details': 'sdsdsd'}))

        belongsto.primary = primary
        belongsto.secondary = secondary
        run(belongsto.save())
        belongsto.primary = primary2

        assert belongsto.primary_to_add is not None
        assert belongsto.primary_to_remove is not None
        run(belongsto.save())
        assert belongsto.primary_to_add is None
        assert belongsto.primary_to_remove is None

        belongsto.secondary = secondary2
        assert len(belongsto.secondary_to_add)
        assert len(belongsto.secondary_to_remove)
        run(belongsto.save())
        assert not len(belongsto.secondary_to_add)
        assert not len(belongsto.secondary_to_remove)

    def test_AsyncBelongsTo_changing_primary_and_secondary_updates_models_correctly(self):
        belongsto = async_relations.AsyncBelongsTo(
            'owner_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        primary1 = run(self.OwnedModel.insert({'details': '321ads'}))
        primary2 = run(self.OwnedModel.insert({'details': '12332'}))
        secondary1 = run(self.OwnerModel.insert({'details':'321'}))
        secondary2 = run(self.OwnerModel.insert({'details':'afgbfb'}))

        belongsto.primary = primary1
        belongsto.secondary = secondary1
        run(belongsto.save())
        assert primary1.data['owner_id'] == secondary1.data['id']

        belongsto.primary = primary2
        run(belongsto.save())
        assert primary2.data['owner_id'] == secondary1.data['id']

        belongsto.secondary = secondary2
        run(belongsto.save())
        assert primary2.data['owner_id'] == secondary2.data['id']
        assert not primary1.data['owner_id']

    def test_AsyncBelongsTo_create_property_returns_property(self):
        belongsto = async_relations.AsyncBelongsTo(
            'owner_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        prop = belongsto.create_property()

        assert type(prop) is property

    def test_AsyncBelongsTo_property_wraps_input_class(self):
        belongsto = async_relations.AsyncBelongsTo(
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
        assert type(owned.owner()) is async_relations.AsyncBelongsTo

    def test_AsyncBelongsTo_save_changes_only_foreign_id_column_in_db(self):
        belongsto = async_relations.AsyncBelongsTo(
            'owner_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        self.OwnedModel.owner = belongsto.create_property()

        owned = run(self.OwnedModel.insert({'details': '123'}))
        owner = run(self.OwnerModel.insert({'details': '321'}))
        owned.owner = owner
        owned.owner.data['details'] = 'abc'
        run(owned.owner().save())

        run(owner.reload())
        assert owner.data['details'] == '321'
        assert owned.data['owner_id'] == owner.data['id']

    def test_async_belongs_to_function_sets_property_from_AsyncBelongsTo(self):
        self.OwnedModel.owner = async_relations.async_belongs_to(
            self.OwnedModel,
            self.OwnerModel,
            'owner_id'
        )

        assert type(self.OwnedModel.owner) is property

        owned = run(self.OwnedModel.insert({'details': '321'}))
        owner = run(self.OwnerModel.insert({'details': '123'}))
        owned.owner = owner

        assert callable(owned.owner)
        assert type(owned.owner()) is async_relations.AsyncBelongsTo

        run(owned.owner().save())

    def test_AsyncBelongsTo_works_with_multiple_instances(self):
        self.OwnedModel.owner = async_relations.async_belongs_to(
            self.OwnedModel,
            self.OwnerModel,
            'owner_id'
        )

        owned1 = run(self.OwnedModel.insert({'details': 'owned1'}))
        owned2 = run(self.OwnedModel.insert({'details': 'owned2'}))
        owner1 = run(self.OwnerModel.insert({'details': 'owner1'}))
        owner2 = run(self.OwnerModel.insert({'details': 'owner2'}))

        owned1.owner = owner1
        run(owned1.owner().save())

        owned2.owner = owner2
        run(owned2.owner().save())

        assert owned1.owner() is not owned2.owner()
        assert owned1.owner.data['id'] == owner1.data['id']
        assert owned2.owner.data['id'] == owner2.data['id']

    def test_AsyncBelongsTo_reload_raises_ValueError_for_empty_relation(self):
        belongsto = async_relations.AsyncBelongsTo(
            'owner_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel,
        )

        with self.assertRaises(ValueError) as e:
            run(belongsto.reload())
        assert str(e.exception) == 'cannot reload an empty relation'

    def test_async_belongs_to_related_property_loads_on_first_read(self):
        self.OwnedModel.owner = async_relations.async_belongs_to(
            self.OwnedModel,
            self.OwnerModel,
            'owner_id'
        )

        owner = run(self.OwnerModel.insert({'details': '123'}))
        owned = run(self.OwnedModel.insert({
            'details': '321',
            'owner_id': owner.id,
        }))

        assert owned.owner
        assert owned.owner.id == owner.id

    # AsyncBelongsToMany tests
    def test_AsyncBelongsToMany_extends_Relation(self):
        assert issubclass(async_relations.AsyncBelongsToMany, async_relations.AsyncRelation)

    def test_AsyncBelongsToMany_initializes_properly(self):
        belongstomany = async_relations.AsyncBelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        assert isinstance(belongstomany, async_relations.AsyncBelongsToMany)

        with self.assertRaises(TypeError) as e:
            async_relations.AsyncBelongsToMany(
                Pivot,
                b'not a str',
                'second_id'
            )
        assert str(e.exception) == 'primary_id_column and secondary_id_column must be str'

    def test_AsyncBelongsToMany_sets_primary_and_secondary_correctly(self):
        belongstomany = async_relations.AsyncBelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        primary = run(self.OwnedModel.insert({'details': '321ads'}))
        secondary = run(self.OwnerModel.insert({'details':'321'}))

        assert belongstomany.primary is None
        belongstomany.primary = primary
        assert belongstomany.primary is primary

        with self.assertRaises(TypeError) as e:
            belongstomany.secondary = secondary
        assert str(e.exception) == 'must be a list of AsyncModelProtocol'

        with self.assertRaises(TypeError) as e:
            belongstomany.secondary = [primary]
        assert str(e.exception) == 'secondary must be instance of OwnerModel'

        assert belongstomany.secondary is None
        belongstomany.secondary = [secondary]
        assert belongstomany.secondary[0] == secondary

    def test_AsyncBelongsToMany_get_cache_key_includes_foreign_id_column(self):
        belongstomany = async_relations.AsyncBelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        cache_key = belongstomany.get_cache_key()
        assert cache_key == 'OwnedModel_AsyncBelongsToMany_OwnerModel_Pivot_first_id_second_id'

    def test_AsyncBelongsToMany_save_raises_error_for_incomplete_relation(self):
        belongstomany = async_relations.AsyncBelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )

        with self.assertRaises(errors.UsageError) as e:
            run(belongstomany.save())
        assert str(e.exception) == 'cannot save incomplete AsyncBelongsToMany'

    def test_AsyncBelongsToMany_save_changes_foreign_id_column_on_secondary(self):
        belongstomany = async_relations.AsyncBelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        primary = run(self.OwnedModel.insert({'details': '321ads'}))
        secondary = run(self.OwnerModel.insert({'details':'321'}))

        belongstomany.primary = primary
        belongstomany.secondary = [secondary]

        assert run(Pivot.query().count()) == 0
        run(belongstomany.save())
        assert run(Pivot.query().count()) == 1
        run(belongstomany.save())
        assert run(Pivot.query().count()) == 1

    def test_AsyncBelongsToMany_save_unsets_change_tracking_properties(self):
        belongstomany = async_relations.AsyncBelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        primary = run(self.OwnedModel.insert({'details':'321'}))
        primary2 = run(self.OwnedModel.insert({'details':'321asds'}))
        secondary = run(self.OwnerModel.insert({'details': '321ads'}))
        secondary2 = run(self.OwnerModel.insert({'details': 'sdsdsd'}))

        belongstomany.primary = primary
        belongstomany.secondary = [secondary]
        run(belongstomany.save())
        belongstomany.primary = primary2

        assert belongstomany.primary_to_add is not None
        assert belongstomany.primary_to_remove is not None
        run(belongstomany.save())
        assert belongstomany.primary_to_add is None
        assert belongstomany.primary_to_remove is None

        belongstomany.secondary = [secondary2]
        assert len(belongstomany.secondary_to_add)
        assert len(belongstomany.secondary_to_remove)
        run(belongstomany.save())
        assert not len(belongstomany.secondary_to_add)
        assert not len(belongstomany.secondary_to_remove)

    def test_AsyncBelongsToMany_changing_primary_and_secondary_updates_models_correctly(self):
        belongstomany = async_relations.AsyncBelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        primary1 = run(self.OwnedModel.insert({'details': '321ads'}))
        primary2 = run(self.OwnedModel.insert({'details': '12332'}))
        secondary1 = run(self.OwnerModel.insert({'details':'321'}))
        secondary2 = run(self.OwnerModel.insert({'details':'afgbfb'}))

        belongstomany.primary = primary1
        belongstomany.secondary = [secondary1]
        run(belongstomany.save())
        pivot = run(Pivot.query().first())
        assert pivot is not None
        assert pivot.data['first_id'] == primary1.data['id']
        assert pivot.data['second_id'] == secondary1.data['id']

        belongstomany.primary = primary2
        run(belongstomany.save())
        assert run(Pivot.query().count()) == 1
        pivot = run(Pivot.query().first())
        assert pivot.data['first_id'] == primary2.data['id']
        assert pivot.data['second_id'] == secondary1.data['id']

        belongstomany.secondary = [secondary2]
        run(belongstomany.save())
        assert run(Pivot.query().count()) == 1
        pivot = run(Pivot.query().first())
        assert pivot.data['first_id'] == primary2.data['id']
        assert pivot.data['second_id'] == secondary2.data['id']

    def test_AsyncBelongsToMany_create_property_returns_property(self):
        belongstomany = async_relations.AsyncBelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        prop = belongstomany.create_property()

        assert type(prop) is property

    def test_AsyncBelongsToMany_property_wraps_input_class(self):
        belongstomany = async_relations.AsyncBelongsToMany(
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
        assert type(owned.owners()) is async_relations.AsyncBelongsToMany

    def test_AsyncBelongsToMany_save_changes_only_foreign_id_column_in_db(self):
        belongstomany = async_relations.AsyncBelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )
        self.OwnedModel.owners = belongstomany.create_property()

        owned = run(self.OwnedModel.insert({'details': '123'}))
        owner = run(self.OwnerModel.insert({'details': '321'}))
        owned.owners = [owner]
        owned.owners[0].data['details'] = 'abc'
        assert run(Pivot.query().count()) == 0
        run(owned.owners().save())

        run(owner.reload())
        assert owner.data['details'] == '321'
        assert run(Pivot.query().count()) == 1

    def test_async_belongs_to_many_function_sets_property_from_AsyncBelongsToMany(self):
        self.OwnedModel.owners = async_relations.async_belongs_to_many(
            self.OwnedModel,
            self.OwnerModel,
            Pivot,
            'first_id',
            'second_id',
        )

        assert type(self.OwnedModel.owners) is property

        owned = run(self.OwnedModel.insert({'details': '321'}))
        owner = run(self.OwnerModel.insert({'details': '123'}))
        owned.owners = [owner]

        assert callable(owned.owners)
        assert type(owned.owners()) is async_relations.AsyncBelongsToMany

        run(owned.owners().save())

    def test_AsyncBelongsToMany_works_with_multiple_instances(self):
        self.OwnedModel.owners = async_relations.async_belongs_to_many(
            self.OwnedModel,
            self.OwnerModel,
            Pivot,
            'first_id',
            'second_id',
        )

        owned1 = run(self.OwnedModel.insert({'details': 'owned1'}))
        owned2 = run(self.OwnedModel.insert({'details': 'owned2'}))
        owner1 = run(self.OwnerModel.insert({'details': 'owner1'}))
        owner2 = run(self.OwnerModel.insert({'details': 'owner2'}))

        owned1.owners = [owner1]
        run(owned1.owners().save())

        owned2.owners = [owner2]
        run(owned2.owners().save())

        assert owned1.relations != owned2.relations
        assert owned1.owners() is not owned2.owners()
        assert owned1.owners[0].data['id'] == owner1.data['id']
        assert owned2.owners[0].data['id'] == owner2.data['id']

    def test_AsyncBelongsToMany_reload_raises_ValueError_for_empty_relation(self):
        belongstomany = async_relations.AsyncBelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnerModel
        )

        with self.assertRaises(ValueError) as e:
            run(belongstomany.reload())
        assert str(e.exception) == 'cannot reload an empty relation'

    def test_async_belongs_to_many_related_property_loads_on_first_read(self):
        self.OwnedModel.owners = async_relations.async_belongs_to_many(
            self.OwnedModel,
            self.OwnerModel,
            Pivot,
            'first_id',
            'second_id',
        )

        owned = run(self.OwnedModel.insert({'details': '321'}))
        owner = run(self.OwnerModel.insert({'details': '123'}))
        run(Pivot.insert({
            'first_id': owned.id,
            'second_id': owner.id,
        }))
        assert len(owned.owners) == 1
        assert owned.owners[0].id == owner.id

    # AsyncContains tests
    def test_AsyncContains_extends_Relation(self):
        assert issubclass(async_relations.AsyncContains, async_relations.AsyncRelation)

    def test_AsyncContains_initializes_properly(self):
        contains = async_relations.AsyncContains(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        assert isinstance(contains, async_relations.AsyncContains)

        with self.assertRaises(TypeError) as e:
            async_relations.AsyncContains(
                b'not a str',
                'second_id'
            )
        assert str(e.exception) == 'foreign_id_column must be str', e.exception

    def test_AsyncContains_sets_primary_and_secondary_correctly(self):
        contains = async_relations.AsyncContains(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        secondary = run(self.DAGItem.insert({'details': '321ads'}))
        primary = self.DAGItem({'details':'321'})

        assert contains.primary is None
        contains.primary = primary
        assert contains.primary is primary

        with self.assertRaises(TypeError) as e:
            contains.secondary = secondary
        assert str(e.exception) == 'must be a list of AsyncModelProtocol', e.exception

        with self.assertRaises(TypeError) as e:
            contains.secondary = [self.OwnedModel()]
        assert str(e.exception) == 'secondary must be instance of DAGItem'

        assert contains.secondary is None
        contains.secondary = [secondary]
        assert contains.secondary[0] == secondary

    def test_AsyncContains_get_cache_key_includes_foreign_id_column(self):
        contains = async_relations.AsyncContains(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        cache_key = contains.get_cache_key()
        assert cache_key == 'DAGItem_AsyncContains_DAGItem_parent_ids'

    def test_AsyncContains_save_raises_error_for_incomplete_relation(self):
        contains = async_relations.AsyncContains(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )

        with self.assertRaises(errors.UsageError) as e:
            run(contains.save())
        assert str(e.exception) == 'cannot save incomplete AsyncContains'

    def test_AsyncContains_save_changes_foreign_id_column_on_primary(self):
        contains = async_relations.AsyncContains(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        primary = self.DAGItem({'details':'321'})
        secondary = run(self.DAGItem.insert({'details': '321ads'}))

        contains.primary = primary
        contains.secondary = [secondary]

        assert primary.id is None
        run(contains.save())
        assert primary.id is not None
        assert run(contains.query().count()) == 1
        run(contains.save())
        assert run(contains.query().count()) == 1

    def test_AsyncContains_save_unsets_change_tracking_properties(self):
        contains = async_relations.AsyncContains(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        primary = self.DAGItem({'details':'321'})
        primary2 = self.DAGItem({'details':'321asds'})
        secondary = run(self.DAGItem.insert({'details': '321ads'}))
        secondary2 = run(self.DAGItem.insert({'details': 'sdsdsd'}))

        contains.primary = primary
        contains.secondary = [secondary]
        run(contains.save())
        contains.primary = primary2

        assert contains.primary_to_add is not None
        assert contains.primary_to_remove is not None
        run(contains.save())
        assert contains.primary_to_add is None
        assert contains.primary_to_remove is None

        contains.secondary = [secondary2]
        assert len(contains.secondary_to_add)
        assert len(contains.secondary_to_remove)
        run(contains.save())
        assert not len(contains.secondary_to_add)
        assert not len(contains.secondary_to_remove)

    def test_AsyncContains_changing_primary_and_secondary_updates_models_correctly(self):
        contains = async_relations.AsyncContains(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        primary1 = self.DAGItem({'details': '321ads'})
        primary2 = self.DAGItem({'details': '12332'})
        secondary1 = run(self.DAGItem.insert({'details':'321'}))
        secondary2 = run(self.DAGItem.insert({'details':'afgbfb'}))

        assert primary1.id is None
        contains.primary = primary1
        contains.secondary = [secondary1]
        run(contains.save())
        assert primary1.id is not None

        assert primary2.id is None
        contains.primary = primary2
        run(contains.save())
        assert primary2.id is not None

        old_id = contains.primary.id
        contains.secondary = [secondary2]
        run(contains.save())
        assert contains.primary.id != old_id

    def test_AsyncContains_create_property_returns_property(self):
        contains = async_relations.AsyncContains(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        prop = contains.create_property()

        assert type(prop) is property

    def test_AsyncContains_property_wraps_input_class(self):
        contains = async_relations.AsyncContains(
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
        assert type(child.parents()) is async_relations.AsyncContains

    def test_AsyncContains_save_changes_only_foreign_id_column_in_db(self):
        contains = async_relations.AsyncContains(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        self.DAGItem.parents = contains.create_property()

        parent = run(self.DAGItem.insert({'details': '321'}))
        child = self.DAGItem({'details': '123', 'parent_ids': ''})
        child.parents = []
        assert run(child.parents().query().count()) == 0
        child.parents = [parent]
        child.parents[0].data['details'] = 'abc'
        run(child.parents().save())

        run(parent.reload())
        assert parent.data['details'] == '321'
        assert run(child.parents().query().count()) == 1

    def test_contains_function_sets_property_from_AsyncContains(self):
        self.DAGItem.parents = async_relations.async_contains(
            self.DAGItem,
            self.DAGItem,
            'parent_ids',
        )

        assert type(self.DAGItem.parents) is property

        parent = run(self.DAGItem.insert({'details': '123'}))
        child = self.DAGItem({'details': '321'})
        assert len(child.parents) == 0
        child.parents = [parent]

        assert callable(child.parents)
        assert type(child.parents()) is async_relations.AsyncContains

        run(child.parents().save())
        assert len(child.parents) == 1

    def test_AsyncContains_works_with_multiple_instances(self):
        self.DAGItem.parents = async_relations.async_contains(
            self.DAGItem,
            self.DAGItem,
            'parent_ids',
        )

        parent1 = run(self.DAGItem.insert({'details': 'parent1'}))
        parent2 = run(self.DAGItem.insert({'details': 'parent2'}))
        child1 = self.DAGItem({'details': 'child1'})
        child2 = self.DAGItem({'details': 'child2'})

        child1.parents = [parent1]
        assert child1.id is None
        run(child1.parents().save())
        assert child1.id is not None

        child2.parents = [parent2]
        run(child2.parents().save())

        assert child1.relations != child2.relations
        assert child1.parents() is not child2.parents()
        assert child1.parents[0].data['id'] == parent1.data['id']
        assert child2.parents[0].data['id'] == parent2.data['id']

    def test_AsyncContains_reload_raises_ValueError_for_empty_relation(self):
        contains = async_relations.AsyncContains(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )

        with self.assertRaises(ValueError) as e:
            run(contains.reload())
        assert str(e.exception) == 'cannot reload an empty relation'

    def test_async_contains_related_property_loads_on_first_read(self):
        self.DAGItem.parents = async_relations.async_contains(
            self.DAGItem,
            self.DAGItem,
            'parent_ids',
        )

        parent = run(self.DAGItem.insert({'details': '123'}))
        child = run(self.DAGItem.insert({
            'details': '321',
            'parent_ids': parent.id,
        }))
        assert len(child.parents) == 1
        assert child.parents[0].id == parent.id

    def test_async_contains_relation_does_not_error_on_empty_foreign_id_column(self):
        self.DAGItem.parents = async_relations.async_contains(
            self.DAGItem,
            self.DAGItem,
            'parent_ids',
        )

        child = run(self.DAGItem.insert({'details': '321'}))
        assert len(child.parents) == 0

    # Within tests
    def test_AsyncWithin_extends_Relation(self):
        assert issubclass(async_relations.AsyncWithin, async_relations.AsyncRelation)

    def test_AsyncWithin_initializes_properly(self):
        within = async_relations.AsyncWithin(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        assert isinstance(within, async_relations.AsyncWithin)

        with self.assertRaises(TypeError) as e:
            async_relations.AsyncWithin(
                b'not a str'
            )
        assert str(e.exception) == 'foreign_id_column must be str', e.exception

    def test_AsyncWithin_sets_primary_and_secondary_correctly(self):
        within = async_relations.AsyncWithin(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        primary = run(self.DAGItem.insert({'details': '321ads'}))
        secondary = self.DAGItem({'details':'321'})

        assert within.primary is None
        within.primary = primary
        assert within.primary is primary

        with self.assertRaises(TypeError) as e:
            within.secondary = self.OwnedModel()
        assert str(e.exception) == 'must be a list of AsyncModelProtocol', e.exception

        with self.assertRaises(TypeError) as e:
            within.secondary = [self.OwnedModel()]
        assert str(e.exception) == 'secondary must be instance of DAGItem', e.exception

        assert within.secondary is None
        within.secondary = [secondary]
        assert within.secondary == (secondary,)

    def test_AsyncWithin_get_cache_key_includes_foreign_id_column(self):
        within = async_relations.AsyncWithin(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        cache_key = within.get_cache_key()
        assert cache_key == 'DAGItem_AsyncWithin_DAGItem_parent_ids', cache_key

    def test_AsyncWithin_save_raises_error_for_incomplete_relation(self):
        within = async_relations.AsyncWithin(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )

        with self.assertRaises(errors.UsageError) as e:
            run(within.save())
        assert str(e.exception) == 'cannot save incomplete AsyncWithin', e.exception

    def test_AsyncWithin_save_changes_foreign_id_column_on_primary(self):
        within = async_relations.AsyncWithin(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        secondary = self.DAGItem({'details':'321'})
        primary = run(self.DAGItem.insert({'details': '321ads'}))

        within.primary = primary
        within.secondary = [secondary]

        assert secondary.id is None
        run(within.save())
        assert secondary.id is not None
        assert run(within.query().count()) == 1
        run(within.save())
        assert run(within.query().count()) == 1

    def test_AsyncWithin_save_unsets_change_tracking_properties(self):
        within = async_relations.AsyncWithin(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        primary = run(self.DAGItem.insert({'details': '321ads'}))
        primary2 = run(self.DAGItem.insert({'details': 'sdsdsd'}))
        secondary = self.DAGItem({'details':'321'})
        secondary2 = self.DAGItem({'details':'321asds'})

        within.primary = primary
        within.secondary = [secondary]
        run(within.save())
        within.primary = primary2

        assert within.primary_to_add is not None
        assert within.primary_to_remove is not None
        run(within.save())
        assert within.primary_to_add is None
        assert within.primary_to_remove is None

        within.secondary = [secondary2]
        assert len(within.secondary_to_add)
        assert len(within.secondary_to_remove)
        run(within.save())
        assert not len(within.secondary_to_add)
        assert not len(within.secondary_to_remove)

    def test_AsyncWithin_changing_primary_and_secondary_updates_models_correctly(self):
        within = async_relations.AsyncWithin(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        primary1 = run(self.DAGItem.insert({'details':'321'}))
        primary2 = run(self.DAGItem.insert({'details':'afgbfb'}))
        secondary1 = self.DAGItem({'details': '321ads'})
        secondary2 = self.DAGItem({'details': '12332'})

        assert secondary1.id is None
        within.primary = primary1
        within.secondary = [secondary1]
        run(within.save())
        assert secondary1.id is not None

        assert secondary2.id is None
        within.secondary = [secondary2]
        run(within.save())
        assert secondary2.id is not None

        old_id = within.secondary[0].id
        within.primary = primary2
        run(within.save())
        assert within.secondary[0].id != old_id

    def test_AsyncWithin_create_property_returns_property(self):
        within = async_relations.AsyncWithin(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        prop = within.create_property()

        assert type(prop) is property

    def test_AsyncWithin_property_wraps_input_class(self):
        within = async_relations.AsyncWithin(
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
        assert type(parent.children()) is async_relations.AsyncWithin

    def test_AsyncWithin_save_changes_foreign_id_column_in_db(self):
        within = async_relations.AsyncWithin(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )
        self.DAGItem.children = within.create_property()

        parent = run(self.DAGItem.insert({'details': '321'}))
        child = self.DAGItem({'details': '123', 'parent_ids': ''})
        parent.children = []
        assert run(parent.children().query().count()) == 0
        parent.children = [child]
        parent.children[0].data['details'] = 'abc'
        run(parent.children().save())

        run(child.reload())
        assert child.data['details'] == 'abc', child.data
        assert child.id is not None
        assert run(parent.children().query().count()) == 1

    def test_async_within_function_sets_property_from_Within(self):
        self.DAGItem.children = async_relations.async_within(
            self.DAGItem,
            self.DAGItem,
            'parent_ids',
        )

        assert type(self.DAGItem.children) is property

        parent = run(self.DAGItem.insert({'details': '123'}))
        child = self.DAGItem({'details': '321'})
        assert len(parent.children) == 0
        parent.children = [child]

        assert callable(parent.children)
        assert type(parent.children()) is async_relations.AsyncWithin

        run(parent.children().save())
        assert len(parent.children) == 1

    def test_AsyncWithin_works_with_multiple_instances(self):
        self.DAGItem.children = async_relations.async_within(
            self.DAGItem,
            self.DAGItem,
            'parent_ids',
        )

        parent1 = run(self.DAGItem.insert({'details': 'parent1'}))
        parent2 = run(self.DAGItem.insert({'details': 'parent2'}))
        child1 = self.DAGItem({'details': 'child1'})
        child2 = self.DAGItem({'details': 'child2'})

        parent1.children = [child1]
        assert child1.id is None
        run(parent1.children().save())
        assert child1.id is not None

        parent2.children = [child2]
        run(parent2.children().save())

        assert child1.relations != child2.relations
        assert parent1.children() is not parent2.children()
        assert parent1.children[0].data['id'] == child1.data['id']
        assert parent2.children[0].data['id'] == child2.data['id']

    def test_AsyncWithin_reload_raises_ValueError_for_empty_relation(self):
        within = async_relations.AsyncWithin(
            'parent_ids',
            primary_class=self.DAGItem,
            secondary_class=self.DAGItem
        )

        with self.assertRaises(ValueError) as e:
            run(within.reload())
        assert str(e.exception) == 'cannot reload an empty relation'

    def test_async_within_related_property_loads_on_first_read(self):
        self.DAGItem.children = async_relations.async_within(
            self.DAGItem,
            self.DAGItem,
            'parent_ids',
        )

        parent = run(self.DAGItem.insert({'details': '123'}))
        child = run(self.DAGItem.insert({
            'details': '321',
            'parent_ids': parent.id,
        }))
        assert len(parent.children) == 1
        assert parent.children[0].id == child.id

    # e2e tests
    def test_AsyncHasOne_AsyncBelongsTo_e2e(self):
        self.OwnerModel.__name__ = 'Owner'
        self.OwnerModel.owned = async_relations.async_has_one(
            self.OwnerModel,
            self.OwnedModel
        )
        self.OwnedModel.owner = async_relations.async_belongs_to(
            self.OwnedModel,
            self.OwnerModel
        )

        owner1 = run(self.OwnerModel.insert({'details': 'owner1'}))
        owned1 = run(self.OwnedModel.insert({'details': 'owned1'}))
        owner2 = self.OwnerModel({'details': 'owner2'})
        owned2 = self.OwnedModel({'details': 'owned2'})

        assert owner1.owned().foreign_id_column == 'owner_id'

        owner1.owned = owned1
        run(owner1.owned().save())
        run(owned1.owner().reload())
        assert owned1.owner
        assert owned1.owner.data == owner1.data
        owned1.owner = owner2
        run(owned1.owner().save())

        run(owner2.owned().reload())
        assert owner2.owned
        assert owner2.owned.data == owned1.data

        owner2.owned = owned2
        run(owner2.owned().save())
        assert owner2.owned
        assert owner2.owned.data == owned2.data

        run(owned2.owner().reload())
        assert owned2.owner
        assert owned2.owner.data == owner2.data

        Asynchasone = async_relations.AsyncHasOne(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel,
        )
        Asynchasone.secondary = owned2
        run(Asynchasone.reload())
        assert Asynchasone.primary
        assert Asynchasone.primary == owner2

    def test_AsyncHasMany_AsyncBelongsTo_e2e(self):
        self.OwnerModel.__name__ = 'Owner'
        self.OwnerModel.owned = async_relations.async_has_many(
            self.OwnerModel,
            self.OwnedModel
        )
        self.OwnedModel.owner = async_relations.async_belongs_to(
            self.OwnedModel,
            self.OwnerModel
        )

        owner1 = run(self.OwnerModel.insert({'details': 'owner1'}))
        owned1 = run(self.OwnedModel.insert({'details': 'owned1'}))
        owner2 = self.OwnerModel({'details': 'owner2'})
        owned2 = self.OwnedModel({'details': 'owned2'})

        assert owner1.owned().foreign_id_column == 'owner_id'

        owner1.owned = [owned1]
        run(owner1.owned().save())
        run(owned1.owner().reload())
        assert owned1.owner
        assert owned1.owner.data == owner1.data
        owned1.owner = owner2
        run(owned1.owner().save())

        run(owner2.owned().reload())
        assert owner2.owned
        assert owner2.owned[0].data == owned1.data

        owner2.owned = [owned1, owned2]
        run(owner2.owned().save())
        assert owner2.owned
        assert owner2.owned == (owned1, owned2)
        owner2.owned = [owned1, owned2, owned2]
        assert owner2.owned == (owned1, owned2)

        run(owned2.owner().reload())
        assert owned2.owner
        assert owned2.owner.data == owner2.data

        hasmany = async_relations.AsyncHasMany(
            'owner_id',
            primary_class=self.OwnerModel,
            secondary_class=self.OwnedModel,
        )
        hasmany.secondary = [owned1, owned2]
        run(hasmany.reload())
        assert hasmany.primary
        assert hasmany.primary == owner2

    def test_AsyncBelongsToMany_e2e(self):
        self.OwnedModel.owned = async_relations.async_belongs_to_many(
            self.OwnedModel,
            self.OwnedModel,
            Pivot,
            'first_id',
            'second_id',
        )
        self.OwnedModel.owners = async_relations.async_belongs_to_many(
            self.OwnedModel,
            self.OwnedModel,
            Pivot,
            'second_id',
            'first_id',
        )

        owned1 = run(self.OwnedModel.insert({'details': '1'}))
        owned2 = run(self.OwnedModel.insert({'details': '2'}))
        owned3 = run(self.OwnedModel.insert({'details': '3'}))

        owned1.owned = [owned2, owned3]
        assert owned1.owned
        assert owned1.owned == (owned2, owned3)
        run(owned1.owned().save())
        owned1.owned = [owned2, owned3, owned3]
        assert owned1.owned == (owned2, owned3)

        run(owned2.owners().reload())
        assert owned2.owners
        assert owned2.owners == (owned1,)

        belongstomany = async_relations.AsyncBelongsToMany(
            Pivot,
            'first_id',
            'second_id',
            primary_class=self.OwnedModel,
            secondary_class=self.OwnedModel,
        )

        belongstomany.secondary = [owned2, owned3]
        run(belongstomany.reload())
        assert belongstomany.primary
        assert belongstomany.primary == owned1

    def test_AsyncContains_Within_e2e(self):
        self.DAGItem.parents = async_relations.async_contains(
            self.DAGItem,
            self.DAGItem,
            'parent_ids',
        )
        self.DAGItem.children = async_relations.async_within(
            self.DAGItem,
            self.DAGItem,
            'parent_ids',
        )

        parent1 = run(self.DAGItem.insert({'details': 'Gen 1 item 1'}))
        parent2 = run(self.DAGItem.insert({'details': 'Gen 1 item 2'}))
        child1 = self.DAGItem({'details': 'Gen 2 item 1'})
        child2 = self.DAGItem({'details': 'Gen 2 item 2'})

        assert len(parent1.children) == 0
        parent1.children = [child1, child2]
        run(parent1.children().save())
        run(parent1.children().reload())
        assert len(parent1.children) == 2
        assert child1 in parent1.children
        assert child2 in parent1.children

        assert child1.parents == (parent1,)
        child1.parents = [parent1, parent2]
        run(child1.parents().save())

        assert len(parent2.children) == 1


if __name__ == '__main__':
    unittest.main()
