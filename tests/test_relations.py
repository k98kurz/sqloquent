from context import classes, relations
from genericpath import isfile
import os
import sqlite3
import unittest


class TestRelations(unittest.TestCase):
    db_filepath: str = 'test.db'
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

    # HasOne tests
    def test_HasOne_extends_Relation(self):
        assert issubclass(relations.HasOne, relations.Relation)

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
