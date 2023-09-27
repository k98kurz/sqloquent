from __future__ import annotations
from abc import abstractmethod
from copy import deepcopy
from sqloquent.interfaces import ModelProtocol, QueryBuilderProtocol
from sqloquent.tools import _pascalcase_to_snake_case
from typing import Optional


"""
    Puts the R in ORM. Change-tracking measures were taken as an
    optimization strategy to reduce the frequency of db calls. However,
    these measures often have to call the db anyway just to maintain
    data integrity, so it is arguable if it is at all helpful. I will
    experiment with scrapping it entirely in the future and then do some
    performance profiling to see if it is worth keeping. Problems for an
    older me.
"""


class Relation:
    """Base class for setting up relations."""
    primary_class: type[ModelProtocol]
    secondary_class: type[ModelProtocol]
    primary_to_add: ModelProtocol
    primary_to_remove: ModelProtocol
    secondary_to_add: list[ModelProtocol]
    secondary_to_remove: list[ModelProtocol]
    primary: ModelProtocol
    secondary: ModelProtocol|tuple[ModelProtocol]
    inverse: Optional[Relation|list[Relation]]
    _primary: Optional[ModelProtocol]
    _secondary: Optional[ModelProtocol]

    def __init__(self,
        primary_class: type[ModelProtocol],
        secondary_class: type[ModelProtocol],
        primary_to_add: ModelProtocol = None,
        primary_to_remove: ModelProtocol = None,
        secondary_to_add: list[ModelProtocol] = [],
        secondary_to_remove: list[ModelProtocol] = [],
        primary: ModelProtocol = None,
        secondary: ModelProtocol|tuple[ModelProtocol] = None,
        inverse: Optional[Relation] = None
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
        self.inverse = inverse

    @staticmethod
    def single_model_precondition(model) -> None:
        assert isinstance(model, ModelProtocol), 'model must implement ModelProtocol'

    @staticmethod
    def multi_model_precondition(model) -> None:
        assert type(model) in (list, tuple), \
            'must be a list of ModelProtocol'
        for item in model:
            assert isinstance(item, ModelProtocol), \
                'must be a list of ModelProtocol'

    @property
    def primary(self) -> ModelProtocol:
        return self._primary

    @primary.setter
    def primary(self, primary: Optional[ModelProtocol]) -> None:
        """Sets the primary model instance."""
        if self.secondary_to_remove and self.primary:
            self.save()

        if primary is None:
            if self._primary is not None and self.primary_to_remove is None:
                self.primary_to_remove = self._primary
            self._primary = None
            return

        self.single_model_precondition(primary)
        self.primary_model_precondition(primary)
        new_primary_id = primary.data[primary.id_field] if primary.id_field in primary.data else ''
        has_primary = hasattr(self, '_primary') and self._primary
        old_primary_is_valid = self._primary and self.primary_class.id_field in self._primary.data
        old_primary_id = self._primary.data[self._primary.id_field] if old_primary_is_valid else None

        if has_primary and (not old_primary_is_valid or new_primary_id != old_primary_id):
            self.primary_to_add = primary
            if self.primary_to_remove is None:
                self.primary_to_remove = self._primary

        self._primary = primary

    @property
    def secondary(self) -> Optional[ModelProtocol|tuple[ModelProtocol]]:
        return self._secondary

    @secondary.setter
    @abstractmethod
    def secondary(self, secondary: ModelProtocol|tuple[ModelProtocol]) -> None:
        """Sets the secondary model instance(s)."""
        pass

    def primary_model_precondition(self, primary: ModelProtocol) -> None:
        if self.primary_class is not None:
            assert isinstance(primary, self.primary_class), \
                f'primary must be instance of {self.primary_class.__name__}'

    def secondary_model_precondition(self, secondary: ModelProtocol) -> None:
        assert isinstance(secondary, self.secondary_class), \
            f'secondary must be instance of {self.secondary_class.__name__}'

    @staticmethod
    def pivot_preconditions(pivot: type[ModelProtocol]) -> None:
        assert isinstance(pivot, type), \
            'pivot must be class implementing ModelProtocol'

    @abstractmethod
    def save(self) -> None:
        """Save the relation by setting/unsetting the relevant database
            values and unset the following attributes: primary_to_add,
            primary_to_remove, secondary_to_add, and secondary_to_remove.
        """
        pass

    @abstractmethod
    def reload(self) -> Relation:
        """Reload the relation from the database. Return self in monad pattern."""
        pass

    def get_cache_key(self) -> str:
        return (f'{self.primary_class.__name__}_{self.__class__.__name__}'
                     f'_{self.secondary_class.__name__}')

    @abstractmethod
    def create_property(self) -> property:
        pass


class HasOne(Relation):
    """Class for the relation where primary owns a secondary:
        primary.data[id_field] = secondary.data[foreign_id_field]. An
        inverse of BelongsTo. An instance of this class is set on the
        owner model.
    """
    foreign_id_field: str

    def __init__(self, foreign_id_field: str, *args, **kwargs) -> None:
        """Set the foreign_id_field attribute, then let the Relation init
            handle the rest.
        """
        assert isinstance(foreign_id_field, str), 'foreign_id_field must be str'
        self.foreign_id_field = foreign_id_field
        super().__init__(*args, **kwargs)

    @property
    def secondary(self) -> Optional[ModelProtocol]:
        return self._secondary

    @secondary.setter
    def secondary(self, secondary: ModelProtocol) -> None:
        """Sets the secondary model instance. Includes convoluted change-
            tracking measures to reduce the frequency of database calls.
        """
        if self.primary_to_remove and self.secondary:
            self.save()

        if secondary is None:
            if self._secondary:
                current_secondary_id = self._secondary.data[self._secondary.id_field]
                secondary_to_add_ids = [
                    item.data[item.id_field]
                    for item in self.secondary_to_add
                ]
                secondary_to_remove_ids = [
                    item.data[item.id_field]
                    for item in self.secondary_to_remove
                ]

                if current_secondary_id in secondary_to_add_ids:
                    self.secondary_to_add = [
                        item for item in self.secondary_to_add
                        if item.data[item.id_field] != current_secondary_id
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

    def save(self) -> None:
        """Save the relation by setting/unsetting the relevant database
            values and unset the following attributes: primary_to_add,
            primary_to_remove, secondary_to_add, and secondary_to_remove.
        """
        assert self.primary is not None \
            or self.primary_to_remove is not None \
            or self.primary_to_add is not None, \
            'cannot save incomplete HasOne'
        assert self.secondary is not None \
            or len(self.secondary_to_remove) > 0 \
            or len(self.secondary_to_add) > 0, \
            'cannot save incomplete HasOne'

        qb = self.secondary_class.query()
        remove = False

        if self.primary_to_remove and self.secondary_to_remove:
            owner_id = self.primary_to_remove.data[self.primary_class.id_field]
            owned_id = self.secondary_to_remove[0].data[self.secondary_class.id_field]
            self.secondary_to_remove[0].data[self.foreign_id_field] = None
            remove = True
        elif self.primary_to_remove and self.secondary:
            owner_id = self.primary_to_remove.data[self.primary_class.id_field]
            owned_id = self._secondary.data[self.secondary_class.id_field]
            self._secondary.data[self.foreign_id_field] = None
            remove = True
        elif self.secondary_to_remove and self.primary:
            owner_id = self._primary.data[self.primary_class.id_field]
            owned_id = self.secondary_to_remove[0].data[self.secondary_class.id_field]
            self.secondary_to_remove[0].data[self.foreign_id_field] = None
            remove = True

        if remove:
            qb.update({
                self.foreign_id_field: None
            }, {
                self.secondary_class.id_field: owned_id,
                self.foreign_id_field: owner_id
            })
            qb.reset()

        if self.primary and self.secondary:
            if self.primary_class.id_field not in self._primary.data:
                self._primary.save()
            if self.secondary_class.id_field not in self._secondary.data:
                self._secondary.save()
            owner_id = self._primary.data[self.primary_class.id_field]
            owned_id = self._secondary.data[self.secondary_class.id_field]
            self._secondary.data[self.foreign_id_field] = owner_id

            qb.equal(self.secondary_class.id_field, owned_id).update({
                self.foreign_id_field: owner_id
            })

        self.primary_to_add = None
        self.primary_to_remove = None
        self.secondary_to_add = []
        self.secondary_to_remove = []

        if hasattr(self, 'inverse') and self.inverse:
            self.inverse.primary_to_add = None
            self.inverse.primary_to_remove = None
            self.inverse.secondary_to_add = []
            self.inverse.secondary_to_remove = []
            self.inverse.reload()

    def reload(self) -> HasOne:
        """Reload the relation from the database. Return self in monad pattern."""
        self.primary_to_add = None
        self.primary_to_remove = None
        self.secondary_to_add = []
        self.secondary_to_remove = []

        if self.primary and self.primary_class.id_field in self.primary.data:
            primary_id = self.primary.data[self.primary.id_field]
            self._secondary = self.secondary_class.query({
                self.foreign_id_field: primary_id
            }).first()
            return self

        if self.secondary and self.foreign_id_field in self.secondary.data:
            secondary_id = self.secondary.data[self.foreign_id_field]
            self._primary = self.primary_class.find(secondary_id)
            return self

        raise ValueError('cannot reload an empty relation')

    def get_cache_key(self) -> str:
        return f'{super().get_cache_key()}_{self.foreign_id_field}'

    def create_property(self) -> property:
        """Creates a property that can be used to set relation properties
            on models.
        """
        relation = self
        cache_key = self.get_cache_key()


        class HasOneWrapped(self.secondary_class):
            def __call__(self) -> Relation:
                return self.relations[f'{cache_key}_inverse']
            def __bool__(self) -> bool:
                return len(self.data.keys()) > 0

        HasOneWrapped.__name__ = f'HasOne{self.secondary_class.__name__}'

        def setup_relation(self: ModelProtocol):
            if not hasattr(self, 'relations'):
                self.relations = {}
            self.relations[cache_key] = deepcopy(relation)
            self.relations[cache_key].primary = self

        if not hasattr(self.primary_class, '_post_init_hooks'):
            self.primary_class._post_init_hooks = {}
        self.primary_class._post_init_hooks[cache_key] = setup_relation


        @property
        def secondary(self: ModelProtocol) -> ModelProtocol:
            if cache_key not in self.relations or \
                self.relations[cache_key] is None or \
                self.relations[cache_key].secondary is None:
                empty = HasOneWrapped({})

                if cache_key not in self.relations or self.relations[cache_key] is None:
                    self.relations[cache_key] = deepcopy(relation)
                    self.relations[cache_key].primary = self

                empty.relations = {}
                empty.relations[f'{cache_key}_inverse'] = self.relations[cache_key]
                return empty

            model = HasOneWrapped(self.relations[cache_key].secondary.data)
            if hasattr(self.relations[cache_key].secondary, 'relations'):
                model.relations = self.relations[cache_key].secondary.relations

            return model

        @secondary.setter
        def secondary(self: ModelProtocol, model: ModelProtocol) -> None:
            assert isinstance(model, ModelProtocol), 'model must implement ModelProtocol'
            if not hasattr(model, 'relations'):
                model.relations = {}

            self.relations[cache_key].secondary = model

            if hasattr(relation, 'inverse') and relation.inverse:
                if not hasattr(self.relations[cache_key], 'inverse') or \
                    not hasattr(self.relations[cache_key].inverse, 'copied'):
                    self.relations[cache_key].inverse = deepcopy(relation.inverse)
                    self.relations[cache_key].inverse.copied = True
                self.relations[cache_key].inverse.primary = model
                self.relations[cache_key].inverse.secondary = self

            model.relations[f'{cache_key}_inverse'] = self.relations[cache_key]

        return secondary


class HasMany(HasOne):
    """Class for the relation where primary owns multiple secondary
        models: model.data[foreign_id_field] = primary.data[id_field]
        for model in secondary. The other inverse of BelongsTo. An
        instance of this class is set on the owner model.
    """
    @property
    def secondary(self) -> Optional[tuple[ModelProtocol]]:
        return self._secondary

    @secondary.setter
    def secondary(self, secondary: Optional[list[ModelProtocol]]) -> None:
        """Sets the secondary model instance."""
        if self.primary_to_remove and self._secondary:
            self.save()

        secondary_is_set = self._secondary is not None and len(self._secondary) > 0

        if secondary is None:
            if secondary_is_set:
                secondary_to_add_ids = (
                    model.data[model.id_field]
                    for model in self.secondary_to_add
                )
                secondary_to_remove_ids = (
                    model.data[model.id_field]
                    for model in self.secondary_to_remove
                )
                for item in self._secondary:
                    item_id = item.data[item.id_field]
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

    def save(self) -> None:
        """Save the relation by setting the relevant database value(s)."""
        assert self.primary is not None, 'cannot save incomplete HasMany'
        assert self.secondary is not None, 'cannot save incomplete HasMany'

        qb = self.secondary_class.query()
        owner_id = self.primary.data[self.primary_class.id_field]
        for model in self.secondary:
            if self.secondary_class.id_field not in model.data:
                model.save()
        owned_ids = [
            model.data[self.secondary_class.id_field]
            for model in self.secondary
        ]
        for model in self.secondary:
            model.data[self.foreign_id_field] = owner_id

        if self.secondary_to_remove:
            secondary_ids = [
                item.data[self.secondary_class.id_field]
                for item in self.secondary_to_remove
                if item.data[self.foreign_id_field] == owner_id
            ]
            if secondary_ids:
                qb.is_in(self.secondary_class.id_field, secondary_ids).update({
                    self.foreign_id_field: None
                })
                qb = qb.reset()
                for item in self.secondary_to_remove:
                    if item.data[self.secondary_class.id_field] in secondary_ids:
                        item.data[self.foreign_id_field] = None

        qb.is_in(self.secondary_class.id_field, owned_ids).update({
            self.foreign_id_field: owner_id
        })

        self.primary_to_add = None
        self.primary_to_remove = None
        self.secondary_to_add = []
        self.secondary_to_remove = []

        if hasattr(self, 'inverse') and self.inverse:
            for inverse in self.inverse:
                inverse.primary_to_add = None
                inverse.primary_to_remove = None
                inverse.secondary_to_add = []
                inverse.secondary_to_remove = []

    def reload(self) -> HasMany:
        """Reload the relation from the database. Return self in monad pattern."""
        self.primary_to_add = None
        self.primary_to_remove = None
        self.secondary_to_add = []
        self.secondary_to_remove = []

        if self.primary and self.primary_class.id_field in self.primary.data:
            primary_id = self.primary.data[self.primary.id_field]
            self._secondary = self.secondary_class.query({
                self.foreign_id_field: primary_id
            }).get()
            return self

        if self.secondary:
            primary_id = self.secondary[0].data[self.foreign_id_field]
            self._primary = self.primary_class.find(primary_id)
            return self

        raise ValueError('cannot reload an empty relation')

    def query(self) -> QueryBuilderProtocol|None:
        """Creates the base query for the underlying relation."""
        if self.primary and self.primary_class.id_field in self.primary.data:
            primary_id = self.primary.data[self.primary.id_field]
            return self.secondary_class.query({
                self.foreign_id_field: primary_id
            })
        if self.secondary:
            primary_id = self.secondary[0].data[self.foreign_id_field]
            return self.secondary_class.query({
                self.foreign_id_field: primary_id
            })

    def create_property(self) -> property:
        """Creates a property that can be used to set relation properties
            on models.
        """
        relation = self
        cache_key = self.get_cache_key()


        class HasManyTuple(tuple):
            def __call__(self) -> HasMany:
                return self.relation

        HasManyTuple.__name__ = f'HasMany{self.secondary_class.__name__}'

        def setup_relation(self: ModelProtocol):
            if not hasattr(self.__class__, 'id_relations'):
                self.__class__.id_relations = {}
            if not hasattr(self, 'relations'):
                self.relations = {}
            self.relations[cache_key] = deepcopy(relation)
            self.relations[cache_key].primary = self

            if self.id_field in self.data and self.data[self.id_field] is not None:
                id_cache_key = cache_key + ':' + self.data[self.id_field]
                if id_cache_key in self.__class__.id_relations:
                    self.relations[cache_key] = self.__class__.id_relations[id_cache_key]
                else:
                    self.__class__.id_relations[id_cache_key] = self.relations[cache_key]

        if not hasattr(self.primary_class, '_post_init_hooks'):
            self.primary_class._post_init_hooks = {}
        self.primary_class._post_init_hooks[cache_key] = setup_relation


        @property
        def secondary(self: ModelProtocol) -> HasManyTuple[ModelProtocol]:
            if cache_key not in self.relations or \
                self.relations[cache_key] is None or \
                self.relations[cache_key].secondary is None:
                empty = HasManyTuple()

                if cache_key not in self.relations or self.relations[cache_key] is None:
                    self.relations[cache_key] = deepcopy(relation)
                    self.relations[cache_key].primary = self

                empty.relation = self.relations[cache_key]
                return empty

            models = HasManyTuple(self.relations[cache_key].secondary)
            models.relation = self.relations[cache_key]
            return models

        @secondary.setter
        def secondary(self: ModelProtocol, models: Optional[list[ModelProtocol]]) -> None:
            self.relations[cache_key].secondary = models

            if hasattr(relation, 'inverse') and relation.inverse:
                self.relations[cache_key].inverse = []
                for model in models:
                    inverse = deepcopy(relation.inverse)
                    inverse.primary = model
                    inverse.secondary = self
                    self.relations[cache_key].inverse.append(inverse)

        return secondary


class BelongsTo(HasOne):
    """Class for the relation where primary belongs to a secondary:
        primary.data[foreign_id_field] = secondary.data[id_field].
        Inverse of HasOne and HasMany. An instance of this class is set
        on the owned model.
    """
    def save(self) -> None:
        assert self._primary is not None, 'cannot save incomplete BelongsTo'
        assert self._secondary is not None, 'cannot save incomplete BelongsTo'

        if self.secondary_class.id_field not in self._secondary.data:
            self._secondary.save()

        owner_id = self._secondary.data[self.secondary_class.id_field]

        self._primary.update({
            self.foreign_id_field: owner_id
        })

        if self.primary_to_remove is not None:
            self.primary_to_remove.update({
                self.foreign_id_field: None
            })

        self.primary_to_add = None
        self.primary_to_remove = None
        self.secondary_to_add = []
        self.secondary_to_remove = []

        if hasattr(self, 'inverse') and self.inverse:
            self.inverse.primary_to_add = None
            self.inverse.primary_to_remove = None
            self.inverse.secondary_to_add = []
            self.inverse.secondary_to_remove = []

    def reload(self) -> BelongsTo:
        """Reload the relation from the database. Return self in monad pattern."""
        self.primary_to_add = None
        self.primary_to_remove = None
        self.secondary_to_add = []
        self.secondary_to_remove = []

        if self.primary and self.foreign_id_field in self.primary.data:
            secondary_id = self.primary.data[self.foreign_id_field]
            self._secondary = self.secondary_class.find(secondary_id)
            return self

        if self.secondary and self.secondary_class.id_field in self.secondary.data:
            secondary_id = self.secondary.data[self.secondary.id_field]
            self._primary = self.primary_class.query({
                self.foreign_id_field: secondary_id
            }).first()
            return self

        raise ValueError('cannot reload an empty relation')

    def create_property(self) -> property:
        """Creates a property that can be used to set relation properties
            on models.
        """
        relation = self
        cache_key = self.get_cache_key()


        class BelongsToWrapped(self.secondary_class):
            def __call__(self) -> Relation:
                return self.relations[f'{cache_key}_inverse']
            def __bool__(self) -> bool:
                return len(self.data.keys()) > 0

        BelongsToWrapped.__name__ = f'BelongsTo{self.secondary_class.__name__}'

        def setup_relation(self: ModelProtocol):
            if not hasattr(self, 'relations'):
                self.relations = {}
            self.relations[cache_key] = deepcopy(relation)
            self.relations[cache_key].primary = self

        if not hasattr(self.primary_class, '_post_init_hooks'):
            self.primary_class._post_init_hooks = {}
        self.primary_class._post_init_hooks[cache_key] = setup_relation


        @property
        def secondary(self: ModelProtocol) -> ModelProtocol:
            if cache_key not in self.relations or \
                self.relations[cache_key] is None or \
                self.relations[cache_key].secondary is None:
                empty = BelongsToWrapped({})

                if cache_key not in self.relations or self.relations[cache_key] is None:
                    self.relations[cache_key] = deepcopy(relation)
                    self.relations[cache_key].primary = self

                empty.relations = {}
                empty.relations[f'{cache_key}_inverse'] = self.relations[cache_key]
                return empty

            model = BelongsToWrapped(self.relations[cache_key].secondary.data)
            if hasattr(self.relations[cache_key].secondary, 'relations'):
                model.relations = self.relations[cache_key].secondary.relations
            return model

        @secondary.setter
        def secondary(self: ModelProtocol, model: ModelProtocol) -> None:
            assert isinstance(model, ModelProtocol), 'model must implement ModelProtocol'
            if not hasattr(model, 'relations'):
                model.relations = {}

            self.relations[cache_key].secondary = model

            if hasattr(relation, 'inverse') and relation.inverse:
                self.relations[cache_key].inverse = deepcopy(relation.inverse)
                self.relations[cache_key].inverse.primary = model
                if isinstance(relation.inverse, HasMany):
                    self.relations[cache_key].inverse.secondary = [self]
                else:
                    self.relations[cache_key].inverse.secondary = self

            model.relations[f'{cache_key}_inverse'] = self.relations[cache_key]

        return secondary


class BelongsToMany(Relation):
    """Class for the relation where each primary can have many secondary
        and each secondary can have many primary; e.g. users and roles,
        or roles and permissions. This requires the use of a pivot.
    """
    pivot: type[ModelProtocol]
    primary_id_field: str
    secondary_id_field: str

    def __init__(self, pivot: type[ModelProtocol],
                primary_id_field: str,
                secondary_id_field: str,
                *args, **kwargs) -> None:
        """Set the pivot and query_builder_pivot attributes, then let the
            Relation class handle the rest.
        """
        assert type(primary_id_field) is type(secondary_id_field) is str, \
            'primary_id_field and secondary_id_field must be str'
        self.pivot = pivot
        self.primary_id_field = primary_id_field
        self.secondary_id_field = secondary_id_field
        super().__init__(*args, **kwargs)

    @property
    def secondary(self) -> Optional[list[ModelProtocol]]:
        return self._secondary

    @secondary.setter
    def secondary(self, secondary: Optional[list[ModelProtocol]]) -> None:
        """Sets the secondary model instance."""
        if self.primary_to_remove and self._secondary:
            self.save()

        if secondary is None:
            if self._secondary:
                self.secondary_to_remove.extend(self._secondary)
            self._secondary = None
            return

        self.multi_model_precondition(secondary)
        secondary_list = []
        for model in secondary:
            assert isinstance(model, self.secondary_class), \
                f'secondary must be instance of {self.secondary_class.__name__}'
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
            item_id = item.data[item.id_field]
            secondary_ids = (
                model.data[model.id_field]
                for model in self._secondary
            )
            secondary_to_remove_ids = (
                model.data[model.id_field]
                for model in self.secondary_to_remove
            )

            if item_id not in secondary_ids and item_id not in secondary_to_remove_ids:
                self.secondary_to_add.append(item)
            if item_id in secondary_to_remove_ids:
                self.secondary_to_remove = [
                    model for model in self.secondary_to_remove
                    if model.data[model.id_field] != item_id
                ]

        self._secondary = tuple(secondary)

    @property
    def pivot(self) -> type[ModelProtocol]:
        return self._pivot

    @pivot.setter
    def pivot(self, pivot: type[ModelProtocol]) -> None:
        self.pivot_preconditions(pivot)
        self._pivot = pivot

    def save(self) -> None:
        """Save the relation by setting/unsetting the relevant database value(s)."""
        assert self._primary is not None, 'cannot save incomplete BelongsToMany'
        assert self._secondary is not None, 'cannot save incomplete BelongsToMany'

        secondary_ids_to_remove = [
            item.data[item.id_field]
            for item in self.secondary_to_remove
        ]
        secondary_ids_to_add = [
            secondary.data[secondary.id_field]
            for secondary in self.secondary_to_add
        ]
        primary_for_delete = [self.primary] + [self.primary_to_remove]
        primary_ids_for_delete = [
            primary.data[primary.id_field] for primary in primary_for_delete
            if primary
        ]

        query_builder = self.pivot.query()
        must_remove_secondary = len(secondary_ids_to_remove) > 0 and len(primary_ids_for_delete) > 0
        must_remove_primary = self.primary_to_remove is not None
        must_add_secondary = len(secondary_ids_to_add) > 0 and \
            (self.primary or self.primary_to_add) is not None
        must_add_primary = self.primary_to_add is not None

        if must_remove_secondary:
            query_builder.is_in(
                self.secondary_id_field,
                secondary_ids_to_remove
            ).is_in(
                self.primary_id_field,
                primary_ids_for_delete
            ).delete()

        if must_remove_primary:
            primary_to_remove_id = self.primary_to_remove.data[self.primary_class.id_field]
            query_builder.reset().equal(
                self.primary_id_field,
                primary_to_remove_id
            ).is_in(
                self.secondary_id_field,
                secondary_ids_to_remove + [
                    secondary.data[secondary.id_field] for secondary in self.secondary
                ]
            ).delete()

        if must_add_primary or must_add_secondary:
            primary_id = self._primary.data[self.primary_class.id_field]
            already_exists = query_builder.reset().equal(
                self.primary_id_field,
                primary_id
            ).get()
            already_added_ids = [
                item.data[self.secondary_class.id_field]
                for item in already_exists
            ]
            query_builder.reset().insert_many([
                {
                    self.primary_id_field: primary_id,
                    self.secondary_id_field: item.data[item.id_field]
                }
                for item in self.secondary
                if item.data[self.secondary_class.id_field] not in already_added_ids
            ])

        self.primary_to_add = None
        self.primary_to_remove = None
        self.secondary_to_add = []
        self.secondary_to_remove = []

        if hasattr(self, 'inverse') and self.inverse and len(self.inverse):
            for inverse in self.inverse:
                inverse.primary_to_add = None
                inverse.primary_to_remove = None
                inverse.secondary_to_add = []
                inverse.secondary_to_remove = []

    def reload(self) -> BelongsToMany:
        """Reload the relation from the database. Return self in monad pattern."""
        self.primary_to_add = None
        self.primary_to_remove = None
        self.secondary_to_add = []
        self.secondary_to_remove = []

        if self.primary and self.primary_class.id_field in self.primary.data:
            primary_id = self.primary.data[self.primary.id_field]
            pivots = self.pivot.query({
                self.primary_id_field: primary_id
            }).get()
            self._secondary = self.secondary_class.query().is_in(
                self.secondary_class.id_field,
                [pivot.data[self.secondary_id_field] for pivot in pivots]
            ).get()
            return self

        if self.secondary and len(self.secondary):
            for secondary in self.secondary:
                if self.secondary_class.id_field not in secondary.data:
                    secondary.save()

            pivots = self.pivot.query().is_in(
                self.secondary_id_field,
                [secondary.data[secondary.id_field] for secondary in self.secondary]
            ).order_by(self.primary_id_field).get()

            primary_ids = [pivot.data[self.primary_id_field] for pivot in pivots]
            unique_ids = tuple(set(primary_ids))

            for primary_id in unique_ids:
                subset = [
                    pivot for pivot in pivots
                    if pivot.data[self.primary_id_field] == primary_id
                ]
                if len(subset) == len(self.secondary):
                    self._primary = self.primary_class.find(primary_id)
                    return self

            return self

        raise ValueError('cannot reload an empty relation')

    def get_cache_key(self) -> str:
        return f'{super().get_cache_key()}_{self.pivot.__name__}_' \
            f'{self.primary_id_field}_{self.secondary_id_field}'

    def create_property(self) -> property:
        """Creates a property that can be used to set relation properties
            on models.
        """
        relation = self
        cache_key = self.get_cache_key()


        class BelongsToManyTuple(tuple):
            def __call__(self) -> BelongsToMany:
                return self.relation

        BelongsToManyTuple.__name__ = f'BelongsToMany{self.secondary_class.__name__}'

        def setup_relation(self: ModelProtocol):
            if not hasattr(self, 'relations'):
                self.relations = {}
            self.relations[cache_key] = deepcopy(relation)
            self.relations[cache_key].primary = self

        if not hasattr(self.primary_class, '_post_init_hooks'):
            self.primary_class._post_init_hooks = {}
        self.primary_class._post_init_hooks[cache_key] = setup_relation


        @property
        def secondary(self: ModelProtocol) -> BelongsToManyTuple[ModelProtocol]:
            if cache_key not in self.relations or \
                self.relations[cache_key] is None or \
                self.relations[cache_key].secondary is None:
                empty = BelongsToManyTuple()

                if cache_key not in self.relations or self.relations[cache_key] is None:
                    self.relations[cache_key] = deepcopy(relation)
                    self.relations[cache_key].primary = self

                empty.relation = self.relations[cache_key]
                return empty

            models = BelongsToManyTuple(self.relations[cache_key].secondary)
            models.relation = self.relations[cache_key]
            return models

        @secondary.setter
        def secondary(self: ModelProtocol, models: Optional[list[ModelProtocol]]) -> None:
            self.relations[cache_key].secondary = models

            if hasattr(relation, 'inverse') and relation.inverse:
                self.relations[cache_key].inverse = []
                for model in models:
                    inverse = deepcopy(relation.inverse)
                    inverse.primary = model
                    inverse.secondary = [self]
                    self.relations[cache_key].inverse.append(inverse)

        return secondary


def _get_id_field(cls: type[ModelProtocol]) -> str:
    return _pascalcase_to_snake_case(cls.__name__) + f'_{cls.id_field}'

def has_one(cls: type[ModelProtocol], owned_model: type[ModelProtocol],
            foreign_id_field: str = None) -> property:
    if foreign_id_field is None:
        foreign_id_field = _get_id_field(cls)

    relation = HasOne(foreign_id_field, primary_class=cls, secondary_class=owned_model)
    relation.inverse = BelongsTo(foreign_id_field, primary_class=owned_model, secondary_class=cls)
    return relation.create_property()

def has_many(cls: type[ModelProtocol], owned_model: type[ModelProtocol],
             foreign_id_field: str = None) -> property:
    if foreign_id_field is None:
        foreign_id_field = _get_id_field(cls)

    relation = HasMany(foreign_id_field, primary_class=cls, secondary_class=owned_model)
    relation.inverse = BelongsTo(foreign_id_field, primary_class=owned_model, secondary_class=cls)
    return relation.create_property()

def belongs_to(cls: type[ModelProtocol], owner_model: type[ModelProtocol],
               foreign_id_field: str = None, inverse_is_many: bool = False) -> property:
    if foreign_id_field is None:
        foreign_id_field = _get_id_field(owner_model)

    relation = BelongsTo(foreign_id_field, primary_class=cls, secondary_class=owner_model)
    if inverse_is_many:
        relation.inverse = HasMany(foreign_id_field, primary_class=owner_model, secondary_class=cls)
    else:
        relation.inverse = HasOne(foreign_id_field, primary_class=owner_model, secondary_class=cls)
    return relation.create_property()

def belongs_to_many(cls: type[ModelProtocol], other_model: type[ModelProtocol],
                pivot: type[ModelProtocol],
                primary_id_field: str = None, secondary_id_field: str = None) -> property:
    if primary_id_field is None:
        primary_id_field = _get_id_field(cls)
    if secondary_id_field is None:
        secondary_id_field = _get_id_field(other_model)

    relation = BelongsToMany(pivot, primary_id_field, secondary_id_field,
                             primary_class=cls, secondary_class=other_model)
    inverse = BelongsToMany(pivot, secondary_id_field, primary_id_field,
                            primary_class=other_model, secondary_class=cls)
    relation.inverse = inverse
    return relation.create_property()
