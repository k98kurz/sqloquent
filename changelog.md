## 0.4.1

- Fix: `HashedModel` now commits to empty columns as `None` values
- Added `columns_excluded_from_hash` attribute to `HashedModel` to exclude
some columns of subclasses from sha256 id generation

## 0.4.0

- Replaced `make_migration_from_model` tool with new `make_migration_from_model`
and `make_migration_from_model_path`
- Added automatic timestamps to the `DeletedModel` and the async version
- Added `like` and `not_like` to SQB
- Added `does_not_start_with` to SQB
- Added `does_not_end_with` to SQB
- Fix: can now more reliably access relations through other relations
- Added ability to suppress parameter interpolation in SQB.to_sql method
- Relations now attempt to load automatically on first read of property, e.g.
`SomeModel.find(some_id).related_model`

## 0.3.4

- Fixed some type hints
- Reintroduced the disable_column_property_mapping feature
- Added `is_null` and `not_null` to the query builders

## 0.3.3

- Hotfix for CLI tool.

## 0.3.2

- CLI `make model` now accepts `--table {table_name}` parameters

## 0.3.1

- Documentation fixes

## 0.3.0

- Copied almost all synchronous code base and test suite into an async variety
- Added `Contains`, `Within`, `AsyncContains`, `AsyncWithin` relations
- Added `contains`, `within`, `async_contains`, `async_within` ORM helpers
- Improved CLI tool

## 0.2.3

- CLI `make model` now accepts `--columns name[=type],etc` parameters

## 0.2.0

- Simplified classes (`SqlModel` and `SqlQueryBuilder` now have default sqlite
coupling; dropped separate sqlite models)
- Refactored connection info handling scheme
- Refactored relations (removed experimental inverse tracking)
