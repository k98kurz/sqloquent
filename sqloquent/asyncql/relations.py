from __future__ import annotations
from sqloquent.errors import tert, vert, tressa
from sqloquent.asyncql.interfaces import (
    AsyncModelProtocol,
    AsyncQueryBuilderProtocol,
    AsyncRelatedCollection,
    AsyncRelatedModel,
)
from sqloquent.tools import _pascalcase_to_snake_case
from abc import abstractmethod
from copy import deepcopy
from types import MappingProxyType
from typing import Awaitable, Optional, Type
import asyncio
import nest_asyncio


nest_asyncio.apply()

def run(task: Awaitable):
    """Attempt to run a task in a new event loop, then close the loop."""
    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(task)
    except RuntimeError:
        return asyncio.run(task)
    finally:
        loop.close()


class AsyncRelation:
    """Base class for setting up relations."""
    primary_class: Type[AsyncModelProtocol]
    secondary_class: Type[AsyncModelProtocol]
    primary_to_add: AsyncModelProtocol
    primary_to_remove: AsyncModelProtocol
    secondary_to_add: list[AsyncModelProtocol]
    secondary_to_remove: list[AsyncModelProtocol]
    primary: AsyncModelProtocol
    secondary: AsyncModelProtocol|tuple[AsyncModelProtocol]
    _primary: Optional[AsyncModelProtocol]
    _secondary: Optional[AsyncModelProtocol]

    def __init__(self,
        primary_class: Type[AsyncModelProtocol],
        secondary_class: Type[AsyncModelProtocol],
        primary_to_add: AsyncModelProtocol = None,
        primary_to_remove: AsyncModelProtocol = None,
        secondary_to_add: list[AsyncModelProtocol] = [],
        secondary_to_remove: list[AsyncModelProtocol] = [],
        primary: AsyncModelProtocol = None,
        secondary: AsyncModelProtocol|tuple[AsyncModelProtocol] = None,
    ) -> None:
        self._primary = None
        self._secondary = None
        self.primary_class = primary_class
        self.secondary_class = secondary_class
        self.primary_to_add = primary_to_add
        self.primary_to_remove = primary_to_remove
        self.secondary_to_add = secondary_to_add
        self.secondary_to_remove = secondary_to_remove
        self.primary = primary
        self.secondary = secondary

    @staticmethod
    def single_model_precondition(model) -> None:
        """Precondition check for a single model. Raises TypeError if
            the check fails.
        """
        tert(isinstance(model, AsyncModelProtocol), 'model must implement AsyncModelProtocol')

    @staticmethod
    def multi_model_precondition(model) -> None:
        """Precondition checks for a list of models. Raises TypeError if
            any check fails.
        """
        tert(type(model) in (list, tuple), 'must be a list of AsyncModelProtocol')
        for item in model:
            tert(isinstance(item, AsyncModelProtocol), 'must be a list of AsyncModelProtocol')

    @property
    def primary(self) -> AsyncModelProtocol:
        """The primary model instance. Setting raises TypeError if a
            precondition check fails.
        """
        return self._primary

    @primary.setter
    def primary(self, primary: Optional[AsyncModelProtocol]) -> None:
        """Sets the primary model instance. Raises TypeError if a
            precondition check fails.
        """
        if self.secondary_to_remove and self.primary:
            run(self.save())

        if primary is None:
            if self._primary is not None and self.primary_to_remove is None:
                self.primary_to_remove = self._primary
            self._primary = None
            return

        self.single_model_precondition(primary)
        self.primary_model_precondition(primary)
        new_primary_id = primary.data[primary.id_column] if primary.id_column in primary.data else ''
        has_primary = hasattr(self, '_primary') and self._primary
        old_primary_is_valid = self._primary and self.primary_class.id_column in self._primary.data
        old_primary_id = self._primary.data[self._primary.id_column] if old_primary_is_valid else None

        if has_primary and (not old_primary_is_valid or new_primary_id != old_primary_id):
            self.primary_to_add = primary
            if self.primary_to_remove is None:
                self.primary_to_remove = self._primary

        self._primary = primary

    @property
    def secondary(self) -> Optional[AsyncModelProtocol|tuple[AsyncModelProtocol]]:
        """The secondary model instance(s)."""
        return self._secondary

    @secondary.setter
    @abstractmethod
    def secondary(self, secondary: AsyncModelProtocol|tuple[AsyncModelProtocol]) -> None:
        """Sets the secondary model instance(s)."""
        pass

    def primary_model_precondition(self, primary: AsyncModelProtocol) -> None:
        """Precondition check for the primary instance. Raises TypeError
            if the check fails.
        """
        if self.primary_class is not None:
            tert(isinstance(primary, self.primary_class),
                f'primary must be instance of {self.primary_class.__name__}')

    def secondary_model_precondition(self, secondary: AsyncModelProtocol) -> None:
        """Precondition check for a secondary instance. Raises TypeError
            if the check fails.
        """
        tert(isinstance(secondary, self.secondary_class),
            f'secondary must be instance of {self.secondary_class.__name__}')

    @staticmethod
    def pivot_preconditions(pivot: Type[AsyncModelProtocol]) -> None:
        """Precondition check for a pivot type. Raises TypeError if the
            check fails.
        """
        tert(isinstance(pivot, type),
             'pivot must be class implementing AsyncModelProtocol')

    @abstractmethod
    async def save(self) -> None:
        """Save the relation by setting/unsetting the relevant database
            values and unset the following attributes: primary_to_add,
            primary_to_remove, secondary_to_add, and secondary_to_remove.
        """
        pass

    @abstractmethod
    async def reload(self) -> AsyncRelation:
        """Reload the relation from the database. Return self in monad pattern."""
        pass

    @abstractmethod
    def query(self) -> AsyncQueryBuilderProtocol|None:
        """Creates the base query for the underlying relation."""
        pass

    def get_cache_key(self) -> str:
        """Returns the cache key for the AsyncRelation."""
        return (f'{self.primary_class.__name__}_{self.__class__.__name__}'
                     f'_{self.secondary_class.__name__}')

    @abstractmethod
    def create_property(self) -> property:
        """Creates a property to be used on a model."""
        pass


class AsyncHasOne(AsyncRelation):
    """Class for the relation where primary owns a secondary:
        primary.data[id_column] = secondary.data[foreign_id_column]. An
        owner model.
    """
    foreign_id_column: str

    def __init__(self, foreign_id_column: str, *args, **kwargs) -> None:
        """Set the foreign_id_column attribute, then let the AsyncRelation init
            handle the rest. Raises TypeError if foreign_id_column is not
            a str.
        """
        tert(isinstance(foreign_id_column, str), 'foreign_id_column must be str')
        self.foreign_id_column = foreign_id_column
        super().__init__(*args, **kwargs)

    @property
    def secondary(self) -> Optional[AsyncModelProtocol]:
        """The secondary model instance. Setting raises TypeError if the
            precondition check fails.
        """
        return self._secondary

    @secondary.setter
    def secondary(self, secondary: AsyncModelProtocol|None) -> None:
        """Sets the secondary model instance. Includes convoluted change-
            tracking measures to reduce the frequency of database calls.
        """
        if self.primary_to_remove and self.secondary:
            run(self.save())

        if secondary is None:
            if self._secondary:
                current_secondary_id = self._secondary.data[self._secondary.id_column]
                secondary_to_add_ids = [
                    item.data[item.id_column]
                    for item in self.secondary_to_add
                ]
                secondary_to_remove_ids = [
                    item.data[item.id_column]
                    for item in self.secondary_to_remove
                ]

                if current_secondary_id in secondary_to_add_ids:
                    self.secondary_to_add = [
                        item for item in self.secondary_to_add
                        if item.data[item.id_column] != current_secondary_id
                    ]
                elif current_secondary_id not in secondary_to_remove_ids:
                    self.secondary_to_remove.append(self._secondary)

            self._secondary = None
            return

        self.single_model_precondition(secondary)
        self.secondary_model_precondition(secondary)

        if self._secondary and self._secondary not in self.secondary_to_add:
            self.secondary_to_remove.append(self._secondary)

        self._secondary = secondary
        self.secondary_to_add = [secondary]

    async def save(self) -> None:
        """Save the relation by setting/unsetting the relevant database
            values and unset the following attributes: primary_to_add,
            primary_to_remove, secondary_to_add, and secondary_to_remove.
            Raises UsageError if the relation is missing data.
        """
        tressa(self.primary is not None
               or self.primary_to_remove is not None
               or self.primary_to_add is not None,
               'cannot save incomplete AsyncHasOne')
        tressa(self.secondary is not None
               or len(self.secondary_to_remove) > 0
               or len(self.secondary_to_add) > 0,
               'cannot save incomplete AsyncHasOne')

        qb = self.secondary_class.query()
        remove = False

        if self.primary_to_remove and self.secondary_to_remove:
            owner_id = self.primary_to_remove.data[self.primary_class.id_column]
            owned_id = self.secondary_to_remove[0].data[self.secondary_class.id_column]
            self.secondary_to_remove[0].data[self.foreign_id_column] = None
            remove = True
        elif self.primary_to_remove and self.secondary:
            owner_id = self.primary_to_remove.data[self.primary_class.id_column]
            owned_id = self._secondary.data[self.secondary_class.id_column]
            self._secondary.data[self.foreign_id_column] = None
            remove = True
        elif self.secondary_to_remove and self.primary:
            owner_id = self._primary.data[self.primary_class.id_column]
            owned_id = self.secondary_to_remove[0].data[self.secondary_class.id_column]
            self.secondary_to_remove[0].data[self.foreign_id_column] = None
            remove = True

        if remove:
            await qb.update({
                self.foreign_id_column: None
            }, {
                self.secondary_class.id_column: owned_id,
                self.foreign_id_column: owner_id
            })
            qb.reset()

        if self.primary and self.secondary:
            if self.primary_class.id_column not in self._primary.data:
                await self._primary.save()
            if self.secondary_class.id_column not in self._secondary.data:
                await self._secondary.save()
            owner_id = self._primary.data[self.primary_class.id_column]
            owned_id = self._secondary.data[self.secondary_class.id_column]
            self._secondary.data[self.foreign_id_column] = owner_id

            await qb.equal(self.secondary_class.id_column, owned_id).update({
                self.foreign_id_column: owner_id
            })

        self.primary_to_add = None
        self.primary_to_remove = None
        self.secondary_to_add = []
        self.secondary_to_remove = []

    async def reload(self) -> AsyncHasOne:
        """Reload the relation from the database. Return self in monad pattern."""
        self.primary_to_add = None
        self.primary_to_remove = None
        self.secondary_to_add = []
        self.secondary_to_remove = []

        if self.primary and self.primary_class.id_column in self.primary.data:
            primary_id = self.primary.data[self.primary.id_column]
            self._secondary = await self.secondary_class.query({
                self.foreign_id_column: primary_id
            }).first()
            return self

        if self.secondary and self.foreign_id_column in self.secondary.data:
            secondary_id = self.secondary.data[self.foreign_id_column]
            self._primary = await self.primary_class.find(secondary_id)
            return self

        raise ValueError('cannot reload an empty relation')

    def query(self) -> AsyncQueryBuilderProtocol|None:
        """Creates the base query for the underlying relation."""
        if self.primary and self.primary_class.id_column in self.primary.data:
            primary_id = self.primary.data[self.primary.id_column]
            return self.secondary_class.query({
                self.foreign_id_column: primary_id
            })
        if self.secondary:
            primary_id = self.secondary[0].data[self.foreign_id_column]
            return self.secondary_class.query({
                self.foreign_id_column: primary_id
            })

    def get_cache_key(self) -> str:
        """Returns the cache key for this relation."""
        return f'{super().get_cache_key()}_{self.foreign_id_column}'

    def create_property(self) -> property:
        """Creates a property that can be used to set relation properties
            on models. Sets the relevant post-init hook to set up the
            relation on newly created models. Setting the secondary
            property on the instance will raise a TypeError if the
            precondition check fails. Reading the property for the first
            time will cause an attempt to read from the database using
            a synchronized async call, which might produce a
            `ResourceWarning` if done within an async function.
        """
        relation = self
        cache_key = self.get_cache_key()


        class HasOneWrapped(self.secondary_class):
            def __init__(self, original: AsyncModelProtocol = None) -> None:
                self.data = original.data if original else {}
                self.data_original = MappingProxyType({**self.data})
            def __call__(self) -> AsyncRelation:
                return self.relations[cache_key]
            def __bool__(self) -> bool:
                return len(self.data.keys()) > 0

        HasOneWrapped.__name__ = f'(AsyncHasOne){self.secondary_class.__name__}'

        def setup_relation(self: AsyncModelProtocol):
            """Sets up the AsyncHasOne relation during instance initialization."""
            if not hasattr(self, 'relations'):
                self.relations = {}
            self.relations[cache_key] = deepcopy(relation)
            self.relations[cache_key].primary = self

        if not hasattr(self.primary_class, '_post_init_hooks'):
            self.primary_class._post_init_hooks = {}
        self.primary_class._post_init_hooks[cache_key] = setup_relation


        @property
        def secondary(self: AsyncModelProtocol) -> AsyncRelatedModel:
            """The secondary model instance. Setting raises TypeError if
                the precondition check fails.
            """
            if cache_key not in self.relations or \
                self.relations[cache_key] is None:

                if cache_key not in self.relations or self.relations[cache_key] is None:
                    self.relations[cache_key] = deepcopy(relation)
                    self.relations[cache_key].primary = self

            if self.relations[cache_key].secondary is None:
                try:
                    run(self.relations[cache_key].reload())
                except ValueError:
                    pass

            if self.relations[cache_key].secondary is None:
                empty = HasOneWrapped()
                empty.relations = {}
                empty.relations[cache_key] = self.relations[cache_key]
                return empty

            if not hasattr(self.relations[cache_key], 'secondary_wrapped') or \
                self.relations[cache_key].secondary_wrapped is None:
                self.relations[cache_key].secondary_wrapped = HasOneWrapped(
                    self.relations[cache_key].secondary
                )

            model = self.relations[cache_key].secondary_wrapped
            if hasattr(self.relations[cache_key].secondary, 'relations'):
                if not hasattr(model, 'relations'):
                    model.relations = {}
                if cache_key not in model.relations:
                    model.relations[cache_key] = self.relations[cache_key]

            return model

        @secondary.setter
        def secondary(self: AsyncModelProtocol, model: AsyncModelProtocol) -> None:
            """Sets the secondary model. Raises TypeError if the
                precondition check fails.
            """
            tert(isinstance(model, AsyncModelProtocol),
                 'model must implement AsyncModelProtocol')
            if not hasattr(model, 'relations'):
                model.relations = {}

            self.relations[cache_key].secondary = model
            self.relations[cache_key].secondary_wrapped = HasOneWrapped(
                model
            )

            model.relations[cache_key] = self.relations[cache_key]

        return secondary


class AsyncHasMany(AsyncHasOne):
    """Class for the relation where primary owns multiple secondary
        models: model.data[foreign_id_column] = primary.data[id_column]
        instance of this class is set on the owner model.
    """
    @property
    def secondary(self) -> Optional[tuple[AsyncModelProtocol]]:
        """The secondary model instance. Setting raises TypeError if the
            precondition check fails.
        """
        return self._secondary

    @secondary.setter
    def secondary(self, secondary: Optional[list[AsyncModelProtocol]]) -> None:
        """Sets the secondary model instance."""
        if self.primary_to_remove and self._secondary:
            run(self.save())

        secondary_is_set = self._secondary is not None and len(self._secondary) > 0

        if secondary is None:
            if secondary_is_set:
                secondary_to_add_ids = (
                    model.data[model.id_column]
                    for model in self.secondary_to_add
                )
                secondary_to_remove_ids = (
                    model.data[model.id_column]
                    for model in self.secondary_to_remove
                )
                for item in self._secondary:
                    item_id = item.data[item.id_column]
                    if item_id in secondary_to_add_ids:
                        self.secondary_to_add.remove(item)
                    elif item_id not in secondary_to_remove_ids:
                        self.secondary_to_remove.append(item)
            self._secondary = None
            return

        self.multi_model_precondition(secondary)
        secondary_list = []
        for model in secondary:
            self.secondary_model_precondition(model)
            # deduplication without using sets to maintain order
            if model not in secondary_list:
                secondary_list.append(model)
        secondary = tuple(secondary_list)

        if secondary_is_set:
            self.secondary_to_add = [
                item for item in secondary
                if item not in self.secondary_to_remove and item not in self._secondary
            ]
            self.secondary_to_remove += [
                item for item in self._secondary
                if item not in self.secondary_to_add and item not in secondary
            ]
        else:
            self.secondary_to_add = secondary
            self.secondary_to_remove = []

        self._secondary = tuple(secondary)

    async def save(self) -> None:
        """Save the relation by setting the relevant database value(s).
            Raises UsageError if the relation is incomplete.
        """
        tressa(self.primary is not None, 'cannot save incomplete AsyncHasMany')
        tressa(self.secondary is not None, 'cannot save incomplete AsyncHasMany')

        qb = self.secondary_class.query()
        owner_id = self.primary.data[self.primary_class.id_column]
        for model in self.secondary:
            if self.secondary_class.id_column not in model.data:
                await model.save()
        owned_ids = [
            model.data[self.secondary_class.id_column]
            for model in self.secondary
        ]
        for model in self.secondary:
            model.data[self.foreign_id_column] = owner_id

        if self.secondary_to_remove:
            secondary_ids = [
                item.data[self.secondary_class.id_column]
                for item in self.secondary_to_remove
                if item.data[self.foreign_id_column] == owner_id
            ]
            if secondary_ids:
                await qb.is_in(self.secondary_class.id_column, secondary_ids).update({
                    self.foreign_id_column: None
                })
                qb = qb.reset()
                for item in self.secondary_to_remove:
                    if item.data[self.secondary_class.id_column] in secondary_ids:
                        item.data[self.foreign_id_column] = None

        await qb.is_in(self.secondary_class.id_column, owned_ids).update({
            self.foreign_id_column: owner_id
        })

        self.primary_to_add = None
        self.primary_to_remove = None
        self.secondary_to_add = []
        self.secondary_to_remove = []

    async def reload(self) -> AsyncHasMany:
        """Reload the relation from the database. Return self in monad pattern."""
        self.primary_to_add = None
        self.primary_to_remove = None
        self.secondary_to_add = []
        self.secondary_to_remove = []

        if self.primary and self.primary_class.id_column in self.primary.data:
            primary_id = self.primary.data[self.primary.id_column]
            self._secondary = await self.secondary_class.query({
                self.foreign_id_column: primary_id
            }).get()
            return self

        if self.secondary:
            primary_id = self.secondary[0].data[self.foreign_id_column]
            self._primary = await self.primary_class.find(primary_id)
            return self

        raise ValueError('cannot reload an empty relation')

    def query(self) -> AsyncQueryBuilderProtocol|None:
        """Creates the base query for the underlying relation."""
        if self.primary and self.primary_class.id_column in self.primary.data:
            primary_id = self.primary.data[self.primary.id_column]
            return self.secondary_class.query({
                self.foreign_id_column: primary_id
            })
        if self.secondary:
            primary_id = self.secondary[0].data[self.foreign_id_column]
            return self.secondary_class.query({
                self.foreign_id_column: primary_id
            })

    def create_property(self) -> property:
        """Creates a property that can be used to set relation properties
            on models. Sets the relevant post-init hook to set up the
            relation on newly created models. Setting the secondary
            property on the instance will raise a TypeError if the
            precondition check fails. Reading the property for the first
            time will cause an attempt to read from the database using
            a synchronized async call, which might produce a
            `ResourceWarning` if done within an async function.
        """
        relation = self
        cache_key = self.get_cache_key()


        class HasManyTuple(tuple):
            relation: AsyncHasMany
            def __call__(self) -> AsyncHasMany:
                return self.relation

        HasManyTuple.__name__ = f'(AsyncHasMany){self.secondary_class.__name__}'

        def setup_relation(self: AsyncModelProtocol):
            """Sets up the AsyncHasMany relation during instance initialization."""
            if not hasattr(self.__class__, 'id_relations'):
                self.__class__.id_relations = {}
            if not hasattr(self, 'relations'):
                self.relations = {}
            self.relations[cache_key] = deepcopy(relation)
            self.relations[cache_key].primary = self

            if self.id_column in self.data and self.data[self.id_column] is not None:
                id_cache_key = cache_key + ':' + self.data[self.id_column]
                if id_cache_key in self.__class__.id_relations:
                    self.relations[cache_key] = self.__class__.id_relations[id_cache_key]
                else:
                    self.__class__.id_relations[id_cache_key] = self.relations[cache_key]

        if not hasattr(self.primary_class, '_post_init_hooks'):
            self.primary_class._post_init_hooks = {}
        self.primary_class._post_init_hooks[cache_key] = setup_relation


        @property
        def secondary(self: AsyncModelProtocol) -> AsyncRelatedCollection:
            """The secondary model instances. Setting raises TypeError
                if the precondition check fails.
            """
            if cache_key not in self.relations or \
                self.relations[cache_key] is None:

                if cache_key not in self.relations or self.relations[cache_key] is None:
                    self.relations[cache_key] = deepcopy(relation)
                    self.relations[cache_key].primary = self

            if self.relations[cache_key].secondary is None:
                try:
                    run(self.relations[cache_key].reload())
                except ValueError:
                    pass

            if self.relations[cache_key].secondary is None:
                empty = HasManyTuple()
                empty.relation = self.relations[cache_key]
                return empty

            models = HasManyTuple(self.relations[cache_key].secondary)
            models.relation = self.relations[cache_key]
            return models

        @secondary.setter
        def secondary(self: AsyncModelProtocol, models: Optional[list[AsyncModelProtocol]]) -> None:
            """Sets the secondary model instances. Raises TypeError if a
                precondition check fails.
            """
            tert(type(models) in (list, tuple),
                 'models must be list[AsyncModelProtocol] or tuple[AsyncModelProtocol]')
            tert(all([isinstance(m, AsyncModelProtocol) for m in models]),
                 'models must be list[AsyncModelProtocol] or tuple[AsyncModelProtocol]')
            self.relations[cache_key].secondary = models

        return secondary


class AsyncBelongsTo(AsyncHasOne):
    """Class for the relation where primary belongs to a secondary:
        primary.data[foreign_id_column] = secondary.data[id_column].
        Inverse of AsyncHasOne and AsyncHasMany. An instance of this class is set
        on the owned model.
    """
    async def save(self) -> None:
        """Persists the relation to the database. Raises UsageError if
            the relation is incomplete.
        """
        tressa(self._primary is not None, 'cannot save incomplete AsyncBelongsTo')
        tressa(self._secondary is not None, 'cannot save incomplete AsyncBelongsTo')

        if self.secondary_class.id_column not in self._secondary.data:
            await self._secondary.save()

        owner_id = self._secondary.data[self.secondary_class.id_column]

        await self._primary.update({
            self.foreign_id_column: owner_id
        })

        if self.primary_to_remove is not None:
            await self.primary_to_remove.update({
                self.foreign_id_column: None
            })

        self.primary_to_add = None
        self.primary_to_remove = None
        self.secondary_to_add = []
        self.secondary_to_remove = []

    async def reload(self) -> AsyncBelongsTo:
        """Reload the relation from the database. Return self in monad pattern."""
        self.primary_to_add = None
        self.primary_to_remove = None
        self.secondary_to_add = []
        self.secondary_to_remove = []

        if self.primary and self.foreign_id_column in self.primary.data:
            secondary_id = self.primary.data[self.foreign_id_column]
            self._secondary = await self.secondary_class.find(secondary_id)
            return self

        if self.secondary and self.secondary_class.id_column in self.secondary.data:
            secondary_id = self.secondary.data[self.secondary.id_column]
            self._primary = await self.primary_class.query({
                self.foreign_id_column: secondary_id
            }).first()
            return self

        raise ValueError('cannot reload an empty relation')

    def query(self) -> AsyncQueryBuilderProtocol|None:
        """Creates the base query for the underlying relation."""
        if self.primary and self.foreign_id_column in self.primary.data:
            secondary_id = self.primary.data[self.foreign_id_column]
            return self.secondary_class.query({
                self.primary_class.id_column: secondary_id
            })
        if self.secondary:
            secondary_id = self.secondary[0].data[self.foreign_id_column]
            return self.secondary_class.query({
                self.secondary_class.id_column: secondary_id
            })

    def create_property(self) -> property:
        """Creates a property that can be used to set relation properties
            on models. Sets the relevant post-init hook to set up the
            relation on newly created models. Setting the secondary
            property on the instance will raise a TypeError if the
            precondition check fails. Reading the property for the first
            time will cause an attempt to read from the database using
            a synchronized async call, which might produce a
            `ResourceWarning` if done within an async function.
        """
        relation = self
        cache_key = self.get_cache_key()


        class BelongsToWrapped(self.secondary_class):
            def __init__(self, original: AsyncModelProtocol = None) -> None:
                self.data = original.data if original else {}
                self.data_original = MappingProxyType({**self.data})
            def __call__(self) -> AsyncRelation:
                return self.relations[f'{cache_key}']
            def __bool__(self) -> bool:
                return len(self.data.keys()) > 0

        BelongsToWrapped.__name__ = f'(AsyncBelongsTo){self.secondary_class.__name__}'

        def setup_relation(self: AsyncModelProtocol):
            """Sets up the AsyncHasMany relation during instance initialization."""
            if not hasattr(self, 'relations'):
                self.relations = {}
            self.relations[cache_key] = deepcopy(relation)
            self.relations[cache_key].primary = self

        if not hasattr(self.primary_class, '_post_init_hooks'):
            self.primary_class._post_init_hooks = {}
        self.primary_class._post_init_hooks[cache_key] = setup_relation


        @property
        def secondary(self: AsyncModelProtocol) -> AsyncRelatedModel:
            """The secondary model instance. Setting raises TypeError if
                the precondition check fails.
            """
            if cache_key not in self.relations or \
                self.relations[cache_key] is None:

                if cache_key not in self.relations or self.relations[cache_key] is None:
                    self.relations[cache_key] = deepcopy(relation)
                    self.relations[cache_key].primary = self

            if self.relations[cache_key].secondary is None:
                try:
                    run(self.relations[cache_key].reload())
                except ValueError:
                    pass

            if self.relations[cache_key].secondary is None:
                empty = BelongsToWrapped()
                empty.relations = {}
                empty.relations[f'{cache_key}'] = self.relations[cache_key]
                return empty

            if not hasattr(self.relations[cache_key], 'secondary_wrapped') or \
                self.relations[cache_key].secondary_wrapped is None:
                self.relations[cache_key].secondary_wrapped = BelongsToWrapped(
                    self.relations[cache_key].secondary
                )

            model = self.relations[cache_key].secondary_wrapped
            if hasattr(self.relations[cache_key].secondary, 'relations'):
                if not hasattr(model, 'relations'):
                    model.relations = {}
                if cache_key not in model.relations:
                    model.relations[cache_key] = self.relations[cache_key]
            return model

        @secondary.setter
        def secondary(self: AsyncModelProtocol, model: AsyncModelProtocol) -> None:
            tert(isinstance(model, AsyncModelProtocol),
                 'model must implement AsyncModelProtocol')
            if not hasattr(model, 'relations'):
                model.relations = {}

            self.relations[cache_key].secondary = model
            self.relations[cache_key].secondary_wrapped = BelongsToWrapped(
                model
            )

        return secondary


class AsyncBelongsToMany(AsyncRelation):
    """Class for the relation where each primary can have many secondary
        and each secondary can have many primary; e.g. users and roles,
        or roles and permissions. This requires the use of a pivot.
    """
    pivot: Type[AsyncModelProtocol]
    primary_id_column: str
    secondary_id_column: str

    def __init__(self, pivot: Type[AsyncModelProtocol],
                primary_id_column: str,
                secondary_id_column: str,
                *args, **kwargs) -> None:
        """Set the pivot and query_builder_pivot attributes, then let the
            AsyncRelation class handle the rest. Raises TypeError if
            either primary_id_column or secondary_id_column is not a str.
        """
        tert(type(primary_id_column) is type(secondary_id_column) is str,
             'primary_id_column and secondary_id_column must be str')
        self.pivot = pivot
        self.primary_id_column = primary_id_column
        self.secondary_id_column = secondary_id_column
        super().__init__(*args, **kwargs)

    @property
    def secondary(self) -> Optional[list[AsyncModelProtocol]]:
        """The secondary model instances. Setting raises TypeError if a
            precondition check fails.
        """
        return self._secondary

    @secondary.setter
    def secondary(self, secondary: Optional[list[AsyncModelProtocol]]) -> None:
        """Sets the secondary model instance."""
        if self.primary_to_remove and self._secondary:
            run(self.save())

        if secondary is None:
            if self._secondary:
                self.secondary_to_remove.extend(self._secondary)
            self._secondary = None
            return

        self.multi_model_precondition(secondary)
        secondary_list = []
        for model in secondary:
            tert(isinstance(model, self.secondary_class),
                 f'secondary must be instance of {self.secondary_class.__name__}')
            # deduplication without using sets to maintain order
            if model not in secondary_list:
                secondary_list.append(model)
        secondary = tuple(secondary_list)

        if not self._secondary:
            self._secondary = secondary
            self.secondary_to_add = secondary
            return

        for item in self._secondary:
            if item not in secondary and item not in self.secondary_to_add:
                self.secondary_to_remove.append(item)
            if item in self.secondary_to_add:
                self.secondary_to_add.remove(item)

        for item in secondary:
            item_id = item.data[item.id_column]
            secondary_ids = (
                model.data[model.id_column]
                for model in self._secondary
            )
            secondary_to_remove_ids = (
                model.data[model.id_column]
                for model in self.secondary_to_remove
            )

            if item_id not in secondary_ids and item_id not in secondary_to_remove_ids:
                self.secondary_to_add.append(item)
            if item_id in secondary_to_remove_ids:
                self.secondary_to_remove = [
                    model for model in self.secondary_to_remove
                    if model.data[model.id_column] != item_id
                ]

        self._secondary = tuple(secondary)

    @property
    def pivot(self) -> Type[AsyncModelProtocol]:
        return self._pivot

    @pivot.setter
    def pivot(self, pivot: Type[AsyncModelProtocol]) -> None:
        self.pivot_preconditions(pivot)
        self._pivot = pivot

    async def save(self) -> None:
        """Save the relation by setting/unsetting the relevant database
            value(s). Raises UsageError if the relation is incomplete.
        """
        tressa(self._primary is not None, 'cannot save incomplete AsyncBelongsToMany')
        tressa(self._secondary is not None, 'cannot save incomplete AsyncBelongsToMany')

        secondary_ids_to_remove = [
            item.data[item.id_column]
            for item in self.secondary_to_remove
        ]
        secondary_ids_to_add = [
            secondary.data[secondary.id_column]
            for secondary in self.secondary_to_add
        ]
        primary_for_delete = [self.primary] + [self.primary_to_remove]
        primary_ids_for_delete = [
            primary.data[primary.id_column] for primary in primary_for_delete
            if primary
        ]

        query_builder = self.pivot.query()
        must_remove_secondary = len(secondary_ids_to_remove) > 0 and len(primary_ids_for_delete) > 0
        must_remove_primary = self.primary_to_remove is not None
        must_add_secondary = len(secondary_ids_to_add) > 0 and \
            (self.primary or self.primary_to_add) is not None
        must_add_primary = self.primary_to_add is not None

        if must_remove_secondary:
            await query_builder.is_in(
                self.secondary_id_column,
                secondary_ids_to_remove
            ).is_in(
                self.primary_id_column,
                primary_ids_for_delete
            ).delete()

        if must_remove_primary:
            primary_to_remove_id = self.primary_to_remove.data[self.primary_class.id_column]
            await query_builder.reset().equal(
                self.primary_id_column,
                primary_to_remove_id
            ).is_in(
                self.secondary_id_column,
                secondary_ids_to_remove + [
                    secondary.data[secondary.id_column] for secondary in self.secondary
                ]
            ).delete()

        if must_add_primary or must_add_secondary:
            primary_id = self._primary.data[self.primary_class.id_column]
            already_exists = await query_builder.reset().equal(
                self.primary_id_column,
                primary_id
            ).get()
            already_added_ids = [
                item.data[self.secondary_class.id_column]
                for item in already_exists
            ]
            await self.pivot.insert_many([
                {
                    self.primary_id_column: primary_id,
                    self.secondary_id_column: item.data[item.id_column]
                }
                for item in self.secondary
                if item.data[self.secondary_class.id_column] not in already_added_ids
            ])

        self.primary_to_add = None
        self.primary_to_remove = None
        self.secondary_to_add = []
        self.secondary_to_remove = []

    async def reload(self) -> AsyncBelongsToMany:
        """Reload the relation from the database. Return self in monad pattern."""
        self.primary_to_add = None
        self.primary_to_remove = None
        self.secondary_to_add = []
        self.secondary_to_remove = []

        if self.primary and self.primary_class.id_column in self.primary.data:
            primary_id = self.primary.data[self.primary.id_column]
            pivots = await self.pivot.query({
                self.primary_id_column: primary_id
            }).get()
            self._secondary = await self.secondary_class.query().is_in(
                self.secondary_class.id_column,
                [pivot.data[self.secondary_id_column] for pivot in pivots]
            ).get()
            return self

        if self.secondary and len(self.secondary):
            for secondary in self.secondary:
                if self.secondary_class.id_column not in secondary.data:
                    await secondary.save()

            pivots = await self.pivot.query().is_in(
                self.secondary_id_column,
                [secondary.data[secondary.id_column] for secondary in self.secondary]
            ).order_by(self.primary_id_column).get()

            primary_ids = [pivot.data[self.primary_id_column] for pivot in pivots]
            unique_ids = tuple(set(primary_ids))

            for primary_id in unique_ids:
                subset = [
                    pivot for pivot in pivots
                    if pivot.data[self.primary_id_column] == primary_id
                ]
                if len(subset) == len(self.secondary):
                    self._primary = await self.primary_class.find(primary_id)
                    return self

            return self

        raise ValueError('cannot reload an empty relation')

    def query(self) -> AsyncQueryBuilderProtocol|None:
        """Creates the base query for the underlying relation. This will
            return the query for a join between the pivot and the
            related model.
        """
        if self.primary:
            primary_id = self.primary.data[self.primary_class.id_column]
            return self.pivot.query({
                self.primary_id_column: primary_id
            }).join(
                self.secondary_class,
                [self.secondary_id_column, self.secondary_class.id_column],
            )

    def get_cache_key(self) -> str:
        """Returns the cache key for this relation."""
        return f'{super().get_cache_key()}_{self.pivot.__name__}_' \
            f'{self.primary_id_column}_{self.secondary_id_column}'

    def create_property(self) -> property:
        """Creates a property that can be used to set relation properties
            on models. Sets the relevant post-init hook to set up the
            relation on newly created models. Setting the secondary
            property on the instance will raise a TypeError if the
            precondition check fails. Reading the property for the first
            time will cause an attempt to read from the database using
            a synchronized async call, which might produce a
            `ResourceWarning` if done within an async function.
        """
        relation = self
        cache_key = self.get_cache_key()


        class BelongsToManyTuple(tuple):
            relation: AsyncBelongsToMany
            def __call__(self) -> AsyncBelongsToMany:
                return self.relation

        BelongsToManyTuple.__name__ = f'AsyncBelongsToMany{self.secondary_class.__name__}'

        def setup_relation(self: AsyncModelProtocol):
            """Sets up the AsyncHasMany relation during instance initialization."""
            if not hasattr(self, 'relations'):
                self.relations = {}
            self.relations[cache_key] = deepcopy(relation)
            self.relations[cache_key].primary = self

        if not hasattr(self.primary_class, '_post_init_hooks'):
            self.primary_class._post_init_hooks = {}
        self.primary_class._post_init_hooks[cache_key] = setup_relation


        @property
        def secondary(self: AsyncModelProtocol) -> AsyncRelatedCollection:
            """The secondary model instances. Setting raises TypeError
                if a precondition check fails.
            """
            if cache_key not in self.relations or \
                self.relations[cache_key] is None:

                if cache_key not in self.relations or self.relations[cache_key] is None:
                    self.relations[cache_key] = deepcopy(relation)
                    self.relations[cache_key].primary = self

            if self.relations[cache_key].secondary is None:
                try:
                    run(self.relations[cache_key].reload())
                except ValueError:
                    pass

            if self.relations[cache_key].secondary is None:
                empty = BelongsToManyTuple()
                empty.relation = self.relations[cache_key]
                return empty

            models = BelongsToManyTuple(self.relations[cache_key].secondary)
            models.relation = self.relations[cache_key]
            return models

        @secondary.setter
        def secondary(self: AsyncModelProtocol, models: Optional[list[AsyncModelProtocol]]) -> None:
            """Sets the secondary model instances. Raises TypeError if
                the precondition check fails.
            """
            self.relations[cache_key].secondary = models

        return secondary


class AsyncContains(AsyncHasMany):
    """Class for encoding a relationship in which a model contains the
        ID(s) for other models within a column:
        primary.data[foreign_id_column] = ",".join(sorted([
        s.data[id_column] for s in secondary])). Useful for DAGs using
        HashedModel or something similar. IDs are sorted for
        deterministic hashing via HashedModel.
    """
    secondary: tuple[AsyncModelProtocol]
    _secondary: tuple[AsyncModelProtocol]

    async def save(self) -> None:
        """Persists the relation to the database. Raises UsageError if
            the relation is incomplete.
        """
        tressa(self._primary is not None, 'cannot save incomplete AsyncContains')
        tressa(self._secondary is not None, 'cannot save incomplete AsyncContains')

        secondary = []
        for s in self._secondary:
            if not self.secondary_class.id_column in s.data:
                s = await s.save()
            secondary.append(s)
        self._secondary = tuple(secondary)

        ids = ",".join(sorted([
            s.data[self.secondary_class.id_column]
            for s in self._secondary
        ]))

        self.primary.data[self.foreign_id_column] = ids
        self._primary = await self.primary.save()

        if self.primary_to_remove is not None:
            await self.primary_to_remove.update({
                self.foreign_id_column: None
            })

        self.primary_to_add = None
        self.primary_to_remove = None
        self.secondary_to_add = []
        self.secondary_to_remove = []

    async def reload(self) -> AsyncContains:
        """Reload the relation from the database. Return self in monad pattern."""
        self.primary_to_add = None
        self.primary_to_remove = None
        self.secondary_to_add = []
        self.secondary_to_remove = []

        if self.primary and self.foreign_id_column in self.primary.data:
            secondary_ids = self.primary.data[self.foreign_id_column].split(',')
            self._secondary = await self.secondary_class.query().is_in(
                self.secondary_class.id_column, secondary_ids).get()
            return self

        if self.secondary and all([
            self.secondary_class.id_column in s.data for s in self.secondary
        ]):
            secondary_ids = ",".join(sorted([
                s.data[self.secondary_class.id_column]
                for s in self.secondary
            ]))
            self._primary = await self.primary_class.query({
                self.foreign_id_column: secondary_ids
            }).first()
            return self

        raise ValueError('cannot reload an empty relation')

    def query(self) -> AsyncQueryBuilderProtocol|None:
        """Creates the base query for the underlying relation."""
        if self.primary and self.foreign_id_column in self.primary.data:
            secondary_ids = self.primary.data[self.foreign_id_column] or ''
            secondary_ids = secondary_ids.split(',')
            return self.secondary_class.query().is_in(
                self.secondary_class.id_column, secondary_ids
            )
        if self.secondary:
            secondary_ids = [
                s.data[self.secondary_class.id_column]
                for s in self.secondary
            ]
            return self.secondary_class.query().is_in(
                self.secondary_class.id_column, secondary_ids
            )

    def create_property(self) -> property:
        """Creates a property that can be used to set relation properties
            on models. Sets the relevant post-init hook to set up the
            relation on newly created models. Setting the secondary
            property on the instance will raise a TypeError if the
            precondition check fails. Reading the property for the first
            time will cause an attempt to read from the database using
            a synchronized async call, which might produce a
            `ResourceWarning` if done within an async function.
        """
        relation = self
        cache_key = self.get_cache_key()


        class ContainsTuple(tuple):
            relation: AsyncContains
            def __call__(self) -> AsyncContains:
                return self.relation

        ContainsTuple.__name__ = f'(AsyncContains){self.secondary_class.__name__}'

        def setup_relation(self: AsyncModelProtocol):
            """Sets up the AsyncContains relation during instance initialization."""
            if not hasattr(self, 'relations'):
                self.relations = {}
            self.relations[cache_key] = deepcopy(relation)
            self.relations[cache_key].primary = self

        if not hasattr(self.primary_class, '_post_init_hooks'):
            self.primary_class._post_init_hooks = {}
        self.primary_class._post_init_hooks[cache_key] = setup_relation


        @property
        def secondary(self: AsyncModelProtocol) -> AsyncRelatedCollection:
            """The secondary model instances. Setting raises TypeError
                if the precondition check fails.
            """
            if cache_key not in self.relations or \
                self.relations[cache_key] is None:

                if cache_key not in self.relations or self.relations[cache_key] is None:
                    self.relations[cache_key] = deepcopy(relation)
                    self.relations[cache_key].primary = self

            if self.relations[cache_key].secondary is None:
                try:
                    run(self.relations[cache_key].reload())
                except ValueError:
                    pass

            if self.relations[cache_key].secondary is None:
                empty = ContainsTuple()
                empty.relation = self.relations[cache_key]
                return empty

            models = ContainsTuple(self.relations[cache_key].secondary)
            models.relation = self.relations[cache_key]
            return models

        @secondary.setter
        def secondary(self: AsyncModelProtocol, models: Optional[list[AsyncModelProtocol]]) -> None:
            """Sets the secondary model instances."""
            self.relations[cache_key].secondary = models

        return secondary


class AsyncWithin(AsyncHasMany):
    """Class for encoding a relationship in which the model's ID is
        contained within a column of another model: all([
        primary.data[id_column] in s.data[foreign_id_column] for s in
        secondary]). Useful for DAGs using HashedModel or something
        similar. IDs are sorted for deterministic hashing via
        HashedModel.
    """
    secondary: tuple[AsyncModelProtocol]

    async def save(self) -> None:
        """Persists the relation to the database. Raises UsageError if
            the relation is incomplete.
        """
        tressa(self._primary is not None, 'cannot save incomplete AsyncWithin')
        tressa(self._secondary is not None, 'cannot save incomplete AsyncWithin')

        if self.primary.data[self.primary_class.id_column] is None:
            await self.primary.save()

        for s in self.secondary:
            ids = s.data.get(self.foreign_id_column, '')
            ids: list = ids.split(',')
            if self.primary.data[self.primary_class.id_column] not in ids:
                ids.append(self.primary.data[self.primary_class.id_column])

            if self.primary_to_remove is not None and \
            self.primary_class.id_column in self.primary_to_remove.data:
                if self.primary_to_remove.data[self.primary_class.id_column] in ids:
                    ids.remove(self.primary_to_remove.data.get(
                        self.primary_class.id_column, None
                    ))

            ids.sort()
            s.data[self.foreign_id_column] = ",".join(ids)
            await s.save()

        self.primary_to_add = None
        self.primary_to_remove = None
        self.secondary_to_add = []
        self.secondary_to_remove = []

    async def reload(self) -> AsyncWithin:
        """Reload the relation from the database. Return self in monad pattern."""
        self.primary_to_add = None
        self.primary_to_remove = None
        self.secondary_to_add = []
        self.secondary_to_remove = []

        vert(self.primary, 'cannot reload an empty relation')

        self._secondary = tuple(await self.secondary_class.query().contains(
            self.foreign_id_column, self.primary.data[self.primary_class.id_column]
        ).get())
        return self

    def query(self) -> AsyncQueryBuilderProtocol|None:
        """Creates the base query for the underlying relation (i.e. to
            query the secondary class).
        """
        if self.primary and self.primary_class.id_column in self.primary.data:
            return self.secondary_class.query().contains(
                self.foreign_id_column, self.primary.data[self.primary_class.id_column])

    def create_property(self) -> property:
        """Creates a property that can be used to set relation properties
            on models. Sets the relevant post-init hook to set up the
            relation on newly created models. Setting the secondary
            property on the instance will raise a TypeError if the
            precondition check fails. Reading the property for the first
            time will cause an attempt to read from the database using
            a synchronized async call, which might produce a
            `ResourceWarning` if done within an async function.
        """
        relation = self
        cache_key = self.get_cache_key()


        class WithinTuple(tuple):
            relation: AsyncWithin
            def __call__(self) -> AsyncWithin:
                return self.relation

        WithinTuple.__name__ = f'(AsyncWithin){self.secondary_class.__name__}'

        def setup_relation(self: AsyncModelProtocol):
            """Sets up the AsyncWithin relation during instance initialization."""
            if not hasattr(self, 'relations'):
                self.relations = {}
            self.relations[cache_key] = deepcopy(relation)
            self.relations[cache_key].primary = self

        if not hasattr(self.primary_class, '_post_init_hooks'):
            self.primary_class._post_init_hooks = {}
        self.primary_class._post_init_hooks[cache_key] = setup_relation


        @property
        def secondary(self: AsyncModelProtocol) -> AsyncRelatedCollection:
            """The secondary model instances. Setting raises TypeError
                if a precondition check fails.
            """
            if cache_key not in self.relations or \
                self.relations[cache_key] is None:

                if cache_key not in self.relations or self.relations[cache_key] is None:
                    self.relations[cache_key] = deepcopy(relation)
                    self.relations[cache_key].primary = self

            if self.relations[cache_key].secondary is None:
                try:
                    run(self.relations[cache_key].reload())
                except ValueError:
                    pass
                except KeyError:
                    pass

            if self.relations[cache_key].secondary is None:
                empty = WithinTuple()
                empty.relation = self.relations[cache_key]
                return empty

            models = WithinTuple(self.relations[cache_key].secondary)
            models.relation = self.relations[cache_key]
            return models

        @secondary.setter
        def secondary(self: AsyncModelProtocol, models: Optional[list[AsyncModelProtocol]]) -> None:
            """Sets the secondary model instances. Raises TypeError if
                the precondition check fails.
            """
            self.relations[cache_key].secondary = models

        return secondary


def _get_id_column(cls: Type[AsyncModelProtocol]) -> str:
    return _pascalcase_to_snake_case(cls.__name__) + f'_{cls.id_column}'

def async_has_one(cls: Type[AsyncModelProtocol], owned_model: Type[AsyncModelProtocol],
            foreign_id_column: str = None) -> property:
    """Creates a AsyncHasOne relation and returns the result of
        create_property. Usage syntax is like `User.avatar = async_has_one(
        User, Avatar)`. If the foreign id column on the Avatar.table
        table is not user_id (cls.__name__ PascalCase -> snake_case +
        "_id"), then it can be specified.
    """
    if foreign_id_column is None:
        foreign_id_column = _get_id_column(cls)

    relation = AsyncHasOne(foreign_id_column, primary_class=cls, secondary_class=owned_model)
    prop = relation.create_property()
    prop.__doc__ = f'The related `{owned_model.__name__}`. Attempting to set to a ' +\
        f'non-`{owned_model.__name__}` raises a `TypeError`.'
    return prop

def async_has_many(cls: Type[AsyncModelProtocol], owned_model: Type[AsyncModelProtocol],
             foreign_id_column: str = None) -> property:
    """Creates a AsyncHasMany relation and returns the result of
        create_property. Usage syntax is like `User.posts = async_has_many(
        User, Post)`. If the foreign id column on the Post.table
        table is not user_id (cls.__name__ PascalCase -> snake_case +
        "_id"), then it can be specified.
    """
    if foreign_id_column is None:
        foreign_id_column = _get_id_column(cls)

    relation = AsyncHasMany(foreign_id_column, primary_class=cls, secondary_class=owned_model)
    prop = relation.create_property()
    prop.__doc__ = f'The related `{owned_model.__name__}`s. Attempting to set to a ' +\
        f'non-`{owned_model.__name__}` raises a `TypeError`.'
    return prop

def async_belongs_to(cls: Type[AsyncModelProtocol], owner_model: Type[AsyncModelProtocol],
               foreign_id_column: str = None) -> property:
    """Creates a AsyncBelongsTo relation and returns the result of
        create_property. Usage syntax is like `Post.owner = async_belongs_to(
        Post, User)`.  If the foreign id column on the Post.table
        table is not user_id (cls.__name__ PascalCase -> snake_case +
        "_id"), then it can be specified.
    """
    if foreign_id_column is None:
        foreign_id_column = _get_id_column(owner_model)

    relation = AsyncBelongsTo(foreign_id_column, primary_class=cls, secondary_class=owner_model)
    prop = relation.create_property()
    prop.__doc__ = f'The related `{owner_model.__name__}`. Attempting to set to a ' +\
        f'non-`{owner_model.__name__}` raises a `TypeError`.'
    return prop

def async_belongs_to_many(cls: Type[AsyncModelProtocol], other_model: Type[AsyncModelProtocol],
                pivot: Type[AsyncModelProtocol],
                primary_id_column: str = None, secondary_id_column: str = None) -> property:
    """Creates a AsyncBelongsToMany relation and returns the result of
        create_property. Usage syntax is like `User.liked_posts =
        async_belongs_to_many(User, Post, LikedPost)`. If the foriegn id
        columns on LikedPost are not user_id and post_id (cls.__name__
        or other_model.__name__ PascalCase -> snake_case + "_id"), then
        they can be specified.
    """
    if primary_id_column is None:
        primary_id_column = _get_id_column(cls)
    if secondary_id_column is None:
        secondary_id_column = _get_id_column(other_model)

    relation = AsyncBelongsToMany(pivot, primary_id_column, secondary_id_column,
                             primary_class=cls, secondary_class=other_model)
    prop = relation.create_property()
    prop.__doc__ = f'The related `{other_model.__name__}`s. Attempting to set to a ' +\
        f'non-`{other_model.__name__}` raises a `TypeError`.'
    return prop

def async_contains(cls: Type[AsyncModelProtocol], other_model: Type[AsyncModelProtocol],
             foreign_ids_column: str = None) -> property:
    """Creates a Contains relation and returns the result of calling
        create_property. Usage syntax is like `Item.parents =
        async_contains(Item, Item)`. If the column containing the sorted
        list of ids is not item_ids (i.e. other_model.__name__ ->
        snake_case + '_ids'), it can be specified.
    """
    if foreign_ids_column is None:
        foreign_ids_column = _get_id_column(other_model) + 's'
    relation = AsyncContains(foreign_ids_column, primary_class=cls,
                        secondary_class=other_model)
    prop = relation.create_property()
    prop.__doc__ = f'The related `{other_model.__name__}`s. Attempting to set to a ' +\
        f'non-`{other_model.__name__}` raises a `TypeError`.'
    return prop

def async_within(cls: Type[AsyncModelProtocol], other_model: Type[AsyncModelProtocol],
             foreign_ids_column: str = None) -> property:
    """Creates a Within relation and returns the result of calling
        create_property. Usage syntax is like `Item.children =
        async_within(Item, Item)`. If the column containing the sorted
        list of ids is not item_ids (i.e. cls.__name__ ->
        snake_case + '_ids'), it can be specified.
    """
    if foreign_ids_column is None:
        foreign_ids_column = _get_id_column(cls) + 's'
    relation = AsyncWithin(foreign_ids_column, primary_class=cls,
                        secondary_class=other_model)
    prop = relation.create_property()
    prop.__doc__ = f'The related `{other_model.__name__}`s. Attempting to set to a ' +\
        f'non-`{other_model.__name__}` raises a `TypeError`.'
    return prop
