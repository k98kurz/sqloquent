from __future__ import annotations
from abc import abstractmethod
from dataclasses import dataclass, field
from simplesqlorm.interfaces import ModelProtocol, QueryBuilderProtocol
from typing import Optional


@dataclass
class Relation:
    """Base class for setting up relations."""
    primary: ModelProtocol = field(default=None)
    primary_class: type[ModelProtocol] = field(default=None)
    secondary: ModelProtocol|list[ModelProtocol] = field(default=None)
    secondary_class: type[ModelProtocol] = field(default=None)
    primary_to_add: ModelProtocol = None
    primary_to_remove: ModelProtocol = None
    secondary_to_add: list[ModelProtocol] = []
    secondary_to_remove: list[ModelProtocol] = []

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

    @property.setter
    def primary(self, primary: Optional[ModelProtocol]) -> None:
        """Sets the primary model instance."""
        # first process secondary removals before changing primary
        if len(self.secondary_to_remove) > 0 and self.primary is not None:
            self.save()

        if primary is None:
            if self._primary is not None and self.primary_to_remove is None:
                self.primary_to_remove = self._primary
            self._primary = None
            return

        self.single_model_precondition(primary)
        self.primary_model_precondition(primary)

        # if it differs from the current value
        if primary != self._primary:
            # if it was not previously set to be persisted
            if primary != self.primary_to_add:
                self.primary_to_add = primary
            # if there is not already one set for removal
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
        assert isinstance(pivot, ModelProtocol), \
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
    def secondary(self) -> ModelProtocol:
        return self._secondary

    @property.setter
    def secondary(self, secondary: ModelProtocol) -> None:
        """Sets the secondary model instance."""
        # first process primary removal before changing secondary
        if self.primary_to_remove is not None and self.secondary is not None:
            self.save()

        # handle removal of secondary
        if secondary is None:
            # if there was already one set
            if self._secondary is not None:
                # if it was merely queued for adding, remove from that queue
                if self._secondary in self.secondary_to_add:
                    self.secondary_to_add = [
                        s for s in self.secondary_to_add
                        if s is not secondary
                    ]
                # otherwise queue it for removal
                elif self._secondary not in self.secondary_to_remove:
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
        remove, add = False, False

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


class HasMany(HasOne):
    """Class for the relation where primary owns multiple secondary
        models: model.data[foreign_id_field] = primary.data[id_field]
        for model in secondary. The other inverse of BelongsTo. An
        instance of this class is set on the owner model.
    """
    @property
    def secondary(self) -> Optional[list[ModelProtocol]]:
        return self._secondary

    @property.setter
    def secondary(self, secondary: Optional[list[ModelProtocol]]) -> None:
        """Sets the secondary model instance."""
        # first process primary removal before changing secondary
        if self.primary_to_remove is not None and self._secondary is not None:
            self.save()

        # handle removal of secondary
        if secondary is None:
            # if there was already one set
            if self._secondary is not None:
                # for each secondary item
                for item in self._secondary:
                    # if it was merely queued for adding, remove from that queue
                    if item in self.secondary_to_add:
                        self.secondary_to_add = [
                            s for s in self.secondary_to_add
                            if s is not item
                        ]
                    # otherwise queue it for removal
                    elif item not in self.secondary_to_remove:
                        self.secondary_to_remove.append(item)
            self._secondary = []
            return

        # check preconditions
        self.multi_model_precondition(secondary)
        for model in secondary:
            self.secondary_model_precondition(model)

        # if there were some already set and they were not merely queued for adding
        if self._secondary is not None:
            for item in self._secondary:
                if item not in self.secondary_to_add:
                    # queue for removal
                    self.secondary_to_remove.append(self._secondary)

        # set the secondary
        self._secondary = secondary

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
        owned_id = self._primary.data[self.primary_class.id_field]
        self._primary.data[self.foreign_id_field] = owner_id

        qb = self.primary_class.query()

        qb.equal(self.primary_class.id_field, owned_id).update({
            self.foreign_id_field: owner_id
        })
        self.unsaved_changes = False


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

    @property.setter
    def secondary(self, secondary: Optional[list[ModelProtocol]]) -> None:
        """Sets the secondary model instance."""
        if secondary is None:
            self._secondary = None
            return

        self.multi_model_precondition(secondary)
        for model in secondary:
            assert isinstance(model, self.secondary_class), \
                f'each secondary model must be instance of {self.secondary_class}'

        if secondary != self._secondary:
            self.unsaved_changes = True

        # parse existing secondary items
        for item in self._secondary:
            # mark for removal any missing items that were already saved
            if item not in secondary and item not in self.secondary_to_add:
                self.secondary_to_remove.append(item)
            # if the missing item was not yet saved, remove mark for adding
            if item in self.secondary_to_add:
                self.secondary_to_add = [
                    s for s in self.secondary_to_add
                    if s.data[s.id_field] != item.data[item.id_field]
                ]

        # parse incoming secondary items
        for item in secondary:
            # mark for adding any new items that were not already saved
            if item not in self._secondary and item not in self.secondary_to_remove:
                self.secondary_to_add.append(item)
            # if the new item was already saved, remove mark for removal
            if item in self.secondary_to_remove:
                self.secondary_to_remove = [
                    s for s in self.secondary_to_remove
                    if s.data[s.id_field] != item.data[item.id_field]
                ]

        self._secondary = secondary

    @property
    def pivot(self) -> ModelProtocol:
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
        if self.unsaved_changes:
            self.save()

        # if already detached, do nothing
        if self.primary is None:
            return

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
        if self.unsaved_changes:
            self.save()

        # collect items to detach
        items_to_detach = []
        for item in secondary:
            if item in self.secondary:
                items_to_detach.append(item)

        # if nothing to do, do nothing
        if len(items_to_detach) == 0:
            return

        # delete all relevant pivot entries
        primary_id = self.primary.data[self.primary.id_field]
        secondary_ids = [item.data[item.id_field] for item in items_to_detach]
        self.pivot.query({
            self.primary_id_field: primary_id
        }).is_in(self.secondary_id_field, secondary_ids).delete()

        return self

    def save(self) -> None:
        """Save the relation by setting/unsetting the relevant database value(s)."""
        ...
        # handle secondary removals
        # if len(self.secondary_to_remove):
        #     secondary_ids = [
        #         item.data[self.foreign_id_field]
        #         for item in self.secondary_to_remove
        #         if item.data[self.foreign_id_field] == owner_id
        #     ]
        #     if len(secondary_ids):
        #         qb.is_in(self.secondary_class.id_field, secondary_ids).update({
        #             self.foreign_id_field: ''
        #         })
        #         qb = qb.reset()
        #         for item in self.secondary_to_remove:
        #             if item.data[self.secondary_class.id_field] in secondary_ids:
                        # item.data[self.foreign_id_field] = ''
                        # set the inverse relation on secondary models if applicable
                        # @todo


def has_one(cls, owned_model: ModelProtocol, foreign_id_field: str) -> type:
    ...

def belongs_to(cls, owner_model: ModelProtocol, foreign_id_field: str) -> type:
    ...

def has_many(cls, owned_model: ModelProtocol, foreign_id_field: str) -> type:
    ...

def many_to_many(cls, other_model: ModelProtocol,
                pivot: type[ModelProtocol],
                query_builder_pivot: Optional[QueryBuilderProtocol] = None) -> type:
    ...
