from __future__ import annotations
from abc import abstractmethod
from dataclasses import dataclass, field
from simplesqlorm.interfaces import ModelProtocol, QueryBuilderProtocol
from typing import Optional


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
    inverse: Optional[Relation]
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
    def single_model_precondition(model):
        assert isinstance(model, ModelProtocol), 'model must implement ModelProtocol'

    @staticmethod
    def multi_model_precondition(model):
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
        primary_id = primary.data[primary.id_field]
        has_primary = hasattr(self, '_primary') and self._primary

        if has_primary and primary_id != self._primary.data[self._primary.id_field]:
            self.primary_to_add = primary
            if self.primary_to_remove is None:
                self.primary_to_remove = self._primary

        self._primary = primary

    def primary_model_precondition(self, primary: ModelProtocol):
        if self.primary_class is not None:
            assert isinstance(primary, self.primary_class), \
                f'primary must be instance of {self.primary_class}'

    def secondary_model_precondition(self, secondary: ModelProtocol):
        assert isinstance(secondary, self.secondary_class), \
            f'secondary must be instance of {self.secondary_class}'

    @staticmethod
    def pivot_preconditions(pivot: type[ModelProtocol]) -> None:
        assert isinstance(pivot, type), \
            'pivot must be class implementing ModelProtocol'

    def set_primary(self, primary: ModelProtocol) -> Relation:
        """Sets the primary model instance."""
        self.primary = primary
        return self

    @abstractmethod
    def save(self) -> None:
        """Save the relation by setting/unsetting the relevant database
            values and unset the following attributes: primary_to_add,
            primary_to_remove, secondary_to_add, and secondary_to_remove.
        """
        pass

    @abstractmethod
    def reload(self) -> None:
        """Reload the secondary models from the database."""
        pass

    def get_cache_key(self) -> str:
        return (f'{self.primary_class.__name__}_{self.__name__}_'
                     f'_{self.secondary_class.__name__}')

    @abstractmethod
    def create_property(self) -> property:
        ...


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
        """Sets the secondary model instance."""
        if self.primary_to_remove and self.secondary:
            self.save()

        if secondary is None:
            if self._secondary:
                if self._secondary.data[self._secondary.id_field] in [
                    item.data[item.id_field]
                    for item in self.secondary_to_add
                ]:
                    secondary_id = self._secondary.data[self._secondary.id_field]
                    self.secondary_to_add = [
                        item for item in self.secondary_to_add
                        if item.data[item.id_field] != secondary_id
                    ]
                elif self._secondary.data[self._secondary.id_field] not in [
                    item.data[item.id_field]
                    for item in self.secondary_to_remove
                ]:
                    self.secondary_to_remove.append(self._secondary)

            self._secondary = None
            return

        # check preconditions
        self.single_model_precondition(secondary)
        self.secondary_model_precondition(secondary)

        # if there was one already set and it was not merely queued for adding
        if self._secondary is not None and self._secondary not in self.secondary_to_add:
            # queue for removal
            self.secondary_to_remove.append(self._secondary)

        # set the secondary
        self._secondary = secondary
        self.secondary_to_add = [secondary]

    def set_secondary(self, secondary: ModelProtocol) -> HasOne:
        """Sets the secondary model instance. Returns self in monad pattern."""
        self.secondary = secondary
        return self

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

        # handle removals
        if self.primary_to_remove is not None and len(self.secondary_to_remove):
            # remove a relation where both primary and secondary are removed
            owner_id = self.primary_to_remove.data[self.primary_class.id_field]
            owned_id = self.secondary_to_remove[0].data[self.secondary_class.id_field]
            self.secondary_to_remove[0].data[self.foreign_id_field] = ''
            remove = True
        elif self.primary_to_remove is not None and self.secondary is not None:
            # remove a relation where primary is removed
            owner_id = self.primary_to_remove.data[self.primary_class.id_field]
            owned_id = self._secondary.data[self.secondary_class.id_field]
            self._secondary.data[self.foreign_id_field] = ''
            remove = True
        elif len(self.secondary_to_remove) and self.primary is not None:
            # remove a relation where secondary is removed
            owner_id = self._primary.data[self.primary_class.id_field]
            owned_id = self.secondary_to_remove[0].data[self.secondary_class.id_field]
            self.secondary_to_remove[0].data[self.foreign_id_field] = ''
            remove = True

        if remove:
            qb.update({
                self.foreign_id_field: ''
            }, {
                self.secondary_class.id_field: owned_id,
                self.foreign_id_field: owner_id
            })
            qb.reset()
            # set the inverse relation on secondary models if applicable
            # @todo

        # handle addition
        if self.primary is not None and self.secondary is not None:
            # add relation where both primary and secondary are added
            owner_id = self._primary.data[self.primary_class.id_field]
            owned_id = self._secondary.data[self.secondary_class.id_field]
            self._secondary.data[self.foreign_id_field] = owner_id

            qb.equal(self.secondary_class.id_field, owned_id).update({
                self.foreign_id_field: owner_id
            })
            # set the inverse relation on secondary models if applicable
            # @todo

        self.primary_to_add = None
        self.primary_to_remove = None
        self.secondary_to_add = []
        self.secondary_to_remove = []

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
                return relation

        HasOneWrapped.__name__ = f'HasOne{self.secondary_class.__name__}'


        @property
        def secondary(self) -> ModelProtocol:
            if not hasattr(self, 'relations'):
                self.relations = {cache_key: relation}

            return HasOneWrapped(relation.secondary.data)

        @secondary.setter
        def secondary(self, model: ModelProtocol) -> None:
            if not hasattr(self, 'relations'):
                self.relations = {cache_key: relation}

            if cache_key not in self.relations:
                self.relations[cache_key] = relation

            relation.secondary = model

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
                for item in self._secondary:
                    if item.data[item.id_field] in (
                        model.data[model.id_field]
                        for model in self.secondary_to_add
                    ):
                        self.secondary_to_add.remove(item)
                    elif item.data[item.id_field] not in (
                        model.data[model.id_field]
                        for model in self.secondary_to_remove
                    ):
                        self.secondary_to_remove.append(item)
            self._secondary = None
            return

        self.multi_model_precondition(secondary)
        for model in secondary:
            self.secondary_model_precondition(model)

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

    def set_secondary(self, secondary: list[ModelProtocol]) -> HasMany:
        """Sets the secondary model instances."""
        self.secondary = secondary
        return self

    def save(self) -> None:
        """Save the relation by setting the relevant database value(s)."""
        assert self.primary is not None, 'cannot save incomplete HasMany'
        assert self.secondary is not None, 'cannot save incomplete HasMany'

        qb = self._secondary.query()
        owner_id = self.primary.data[self.primary_class.id_field]
        owned_ids = [
            model.data[self.secondary_class.id_field]
            for model in self.secondary
        ]
        for model in self.secondary:
            model.data[self.foreign_id_field] = owner_id

        # handle secondary removals
        if len(self.secondary_to_remove):
            secondary_ids = [
                item.data[self.foreign_id_field]
                for item in self.secondary_to_remove
                if item.data[self.foreign_id_field] == owner_id
            ]
            if len(secondary_ids):
                qb.is_in(self.secondary_class.id_field, secondary_ids).update({
                    self.foreign_id_field: ''
                })
                qb = qb.reset()
                for item in self.secondary_to_remove:
                    if item.data[self.secondary_class.id_field] in secondary_ids:
                        item.data[self.foreign_id_field] = ''
                        # set the inverse relation on secondary models if applicable
                        # @todo

        qb.is_in(self.secondary_class.id_field, owned_ids).update({
            self.foreign_id_field: owner_id
        })

        self.primary_to_add = None
        self.primary_to_remove = None
        self.secondary_to_add = []
        self.secondary_to_remove = []

    def create_property(self) -> property:
        """Creates a property that can be used to set relation properties
            on models.
        """
        relation = self
        cache_key = self.get_cache_key()


        class HasManyWrapped(self.secondary_class):
            def __call__(self) -> Relation:
                return relation

        HasManyWrapped.__name__ = f'HasMany{self.secondary_class.__name__}'


        @property
        def secondary(self) -> ModelProtocol:
            if not hasattr(self, 'relations'):
                self.relations = {cache_key: relation}

            return [HasManyWrapped(model.data) for model in relation.secondary]

        @secondary.setter
        def secondary(self, models: Optional[list[ModelProtocol]]) -> None:
            if not hasattr(self, 'relations'):
                self.relations = {cache_key: relation}

            if cache_key not in self.relations:
                self.relations[cache_key] = relation

            relation.secondary = models

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

        owner_id = self._secondary.data[self.secondary_class.id_field]

        self._primary.update({
            self.foreign_id_field: owner_id
        })

        if self.primary_to_remove is not None:
            self.primary_to_remove.update({
                self.foreign_id_field: ''
            })

        self.primary_to_add = None
        self.primary_to_remove = None
        self.secondary_to_add = []
        self.secondary_to_remove = []

    def create_property(self) -> property:
        """Creates a property that can be used to set relation properties
            on models.
        """
        relation = self
        cache_key = self.get_cache_key()


        class BelongsToWrapped(self.secondary_class):
            def __call__(self) -> Relation:
                return relation

        BelongsToWrapped.__name__ = f'BelongsTo{self.secondary_class.__name__}'


        @property
        def secondary(self) -> ModelProtocol:
            if not hasattr(self, 'relations'):
                self.relations = {cache_key: relation}

            return [BelongsToWrapped(model.data) for model in relation.secondary]

        @secondary.setter
        def secondary(self, models: Optional[list[ModelProtocol]]) -> None:
            if not hasattr(self, 'relations'):
                self.relations = {cache_key: relation}

            if cache_key not in self.relations:
                self.relations[cache_key] = relation

            relation.secondary = models

        return secondary


class BelongsToMany(Relation):
    """Class for the relation where each primary can have many secondary
        and each secondary can have many primary; e.g. users and roles,
        or roles and permissions. This requires the use of a pivot.
    """
    pivot: type[ModelProtocol]
    primary_id_field: str
    secondary_id_field: str
    query_builder_pivot: type[QueryBuilderProtocol]

    def __init__(self, pivot: type[ModelProtocol],
                primary_id_field: str,
                secondary_id_field: str,
                query_builder_pivot: type[QueryBuilderProtocol] = None,
                *args, **kwargs) -> None:
        """Set the pivot and query_builder_pivot attributes, then let the
            Relation class handle the rest.
        """
        assert type(primary_id_field) is type(secondary_id_field) is str, \
            'primary_id_field and secondary_id_field must be str'
        self.pivot = pivot
        self.primary_id_field = primary_id_field
        self.secondary_id_field = secondary_id_field
        self.query_builder_pivot = query_builder_pivot
        super().__init__(*args, **kwargs)

    @property
    def secondary(self) -> Optional[list[ModelProtocol]]:
        return self._secondary

    @secondary.setter
    def secondary(self, secondary: Optional[list[ModelProtocol]]) -> None:
        """Sets the secondary model instance."""
        if self.primary_to_remove and self._secondary:
            self.save()

        if secondary is None and self._secondary:
            self.secondary_to_remove.extend(self._secondary)
            self._secondary = None
            return

        self.multi_model_precondition(secondary)
        for model in secondary:
            assert isinstance(model, self.secondary_class), \
                f'each secondary model must be instance of {self.secondary_class}'

        if secondary != self._secondary:
            self.unsaved_changes = True

        for item in self._secondary:
            if item not in secondary and item not in self.secondary_to_add:
                self.secondary_to_remove.append(item)
            if item in self.secondary_to_add:
                self.secondary_to_add = [
                    s for s in self.secondary_to_add
                    if s.data[s.id_field] != item.data[item.id_field]
                ]

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

            # mark for adding any new items that were not already saved
            if item_id not in secondary_ids and item_id not in secondary_to_remove_ids:
                self.secondary_to_add.append(item)
            # if the new item was already saved, remove mark for removal
            if item_id in secondary_to_remove_ids:
                self.secondary_to_remove = [
                    model for model in self.secondary_to_remove
                    if model.data[model.id_field] != item.data[item.id_field]
                ]

        self._secondary = tuple(secondary)

    @property
    def pivot(self) -> type[ModelProtocol]:
        return self._pivot

    @pivot.setter
    def pivot(self, pivot: type[ModelProtocol]) -> None:
        self.pivot_preconditions(pivot)
        self._pivot = pivot

    def set_secondary(self, secondary: list[ModelProtocol]) -> BelongsToMany:
        """Sets the secondary model instances. Returns self in monad pattern."""
        self.secondary = secondary
        return self

    def set_pivot(self, pivot: type[ModelProtocol]) -> BelongsToMany:
        """Sets the pivot str/model. Returns self in monad pattern."""
        self.pivot = pivot
        return self

    def detach_primary(self) -> BelongsToMany:
        """Detaches the primary, persisting to database."""
        assert self.secondary is not None, 'must set secondary'
        assert self.pivot is not None, 'must set pivot'

        # if there are unsaved changes, first save them
        if self.primary_to_remove or len(self.secondary_to_remove):
            self.save()

        # if already detached, do nothing
        if self.primary is None:
            return self

        # delete all relevant pivot entries
        primary_id = self.primary.data[self.primary.id_field]
        secondary_ids = [item.data[item.id_field] for item in self.secondary]
        self.pivot.query({
            self.primary_id_field: primary_id
        }).is_in(self.secondary_id_field, secondary_ids).delete()

        return self

    def detach_secondary(self, secondary: list[ModelProtocol]) -> BelongsToMany:
        """Detaches the secondary, persisting to database."""
        assert type(secondary) in (list, tuple), \
            'secondary must be list of instances of ModelProtocol'
        for item in secondary:
            self.secondary_model_precondition(item)

        # if there are unsaved changes, first save them
        if self.primary_to_remove or len(self.secondary_to_remove):
            self.save()

        # collect items to detach
        items_to_detach = []
        for item in secondary:
            if item in self.secondary:
                items_to_detach.append(item)

        # if nothing to do, do nothing
        if len(items_to_detach) == 0:
            return self

        # delete all relevant pivot entries
        primary_id = self.primary.data[self.primary.id_field]
        secondary_ids = [item.data[item.id_field] for item in items_to_detach]
        self.pivot.query({
            self.primary_id_field: primary_id
        }).is_in(self.secondary_id_field, secondary_ids).delete()

        return self

    def save(self) -> None:
        """Save the relation by setting/unsetting the relevant database value(s)."""
        secondary_ids_to_remove = [
            item.data[item.id_field]
            for item in self.secondary_to_remove
        ]
        secondary_ids_to_add = [
            item.data[item.id_field]
            for item in self.secondary_to_add
        ]
        primary_for_delete = [self.primary] + [self.primary_to_remove]
        primary_ids_for_delete = [
            item.data[item.id_field] for item in primary_for_delete
            if item is not None
        ]
        query_builder = self.query_builder_pivot(self.pivot) or self.pivot.query()

        must_remove_secondary = len(secondary_ids_to_remove) > 0 and len(primary_ids_for_delete) > 0
        must_remove_primary = self.primary_to_remove is not None
        must_add_secondary = len(secondary_ids_to_add) > 0 and (self.primary or self.primary_to_add)
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
            query_builder.reset().equal(
                self.primary_id_field,
                self.primary_to_remove[self.primary_class.id_field]
            ).is_in(
                self.secondary_id_field,
                secondary_ids_to_remove + [
                    item.data[item.id_field] for item in self.secondary
                ]
            ).delete()

        if must_add_primary or must_add_secondary:
            already_exists = query_builder.reset().equal(
                self.primary_id_field,
                self._primary.data[self.primary_class.id_field]
            ).get()
            already_added_ids = [
                item.data[self.secondary_class.id_field]
                for item in already_exists
            ]
            query_builder.reset().insert_many([
                {
                    self.primary_id_field: self._primary.data[self.primary_class.id_field],
                    self.secondary_id_field: item.data[item.id_field]
                }
                for item in self.secondary
                if item.data[self.secondary_class.id_field] not in already_added_ids
            ])

        self.primary_to_add = None
        self.primary_to_remove = None
        self.secondary_to_add = []
        self.secondary_to_remove = []

    def get_cache_key(self) -> str:
        return f'{super().get_cache_key()}_{self.pivot.__name__}'

    def create_property(self) -> property:
        """Creates a property that can be used to set relation properties
            on models.
        """
        relation = self
        cache_key = self.get_cache_key()


        class BelongsToManyWrapped(self.secondary_class):
            def __call__(self) -> Relation:
                return relation

        BelongsToManyWrapped.__name__ = f'BelongsToMany{self.secondary_class.__name__}'


        @property
        def secondary(self) -> ModelProtocol:
            if not hasattr(self, 'relations'):
                self.relations = {cache_key: relation}

            return [BelongsToManyWrapped(model.data) for model in relation.secondary]

        @secondary.setter
        def secondary(self, models: Optional[list[ModelProtocol]]) -> None:
            if not hasattr(self, 'relations'):
                self.relations = {cache_key: relation}

            if cache_key not in self.relations:
                self.relations[cache_key] = relation

            relation.secondary = models

        return secondary


def has_one(cls: type[ModelProtocol], owned_model: type[ModelProtocol],
            foreign_id_field: str = None) -> type:
    if foreign_id_field is None:
        foreign_id_field = (f'{owned_model.__name__}_{owned_model.id_field}').lower()

    relation = HasOne(foreign_id_field, primary_class=cls, secondary_class=owned_model)
    relation.inverse = BelongsTo(foreign_id_field, primary_class=owned_model, secondary_class=cls)
    relation.inverse.inverse = relation
    return relation.create_property()

def has_many(cls: type[ModelProtocol], owned_model: type[ModelProtocol],
             foreign_id_field: str = None) -> type:
    if foreign_id_field is None:
        foreign_id_field = (f'{owned_model.__name__}_{owned_model.id_field}').lower()

    relation = HasMany(foreign_id_field, primary_class=cls, secondary_class=owned_model)
    relation.inverse = BelongsTo(foreign_id_field, primary_class=owned_model, secondary_class=cls)
    relation.inverse.inverse = relation
    return relation.create_property()

def belongs_to(cls: type[ModelProtocol], owner_model: type[ModelProtocol],
               foreign_id_field: str = None, inverse_is_many: bool = False) -> type:
    if foreign_id_field is None:
        foreign_id_field = (f'{owner_model.__name__}_{owner_model.id_field}').lower()

    relation = BelongsTo(foreign_id_field, primary_class=cls, secondary_class=owner_model)
    if inverse_is_many:
        relation.inverse = HasMany(foreign_id_field, primary_class=owner_model, secondary_class=cls)
    else:
        relation.inverse = HasOne(foreign_id_field, primary_class=owner_model, secondary_class=cls)
    relation.inverse.inverse = relation
    return relation.create_property()

def many_to_many(cls: type[ModelProtocol], other_model: type[ModelProtocol],
                pivot: type[ModelProtocol],
                primary_id_field: str = None, secondary_id_field: str = None,
                query_builder_pivot: QueryBuilderProtocol = None) -> type:
    if primary_id_field is None:
        primary_id_field = (f'{cls.__name__}_{cls.id_field}').lower()
    if secondary_id_field is None:
        secondary_id_field = (f'{other_model.__name__}_{other_model.id_field}').lower()

    relation = BelongsToMany(pivot, primary_id_field, secondary_id_field,
                             query_builder_pivot, primary_class=cls,
                             secondary_class=other_model)
    inverse = BelongsToMany(pivot, secondary_id_field, primary_id_field,
                            query_builder_pivot, primary_class=other_model,
                            secondary_class=cls)
    relation.inverse = inverse
    inverse.inverse = relation
    return relation.create_property()
