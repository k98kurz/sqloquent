from context import relations, interfaces
import unittest


class TestRelations(unittest.TestCase):
    def setUp(self) -> None:
        return super().setUp()

    def setUpClass() -> None:
        ...

    def tearDown(self) -> None:
        return super().tearDown()

    def test_HasOne_extends_Relation(self):
        assert issubclass(relations.HasOne, relations.Relation)


if __name__ == '__main__':
    unittest.main()
