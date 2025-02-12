## 0.7.0

- New method `HashedModel.preimage` to get the preimage of the sha256 id in the
form of the bytes-serialized non-id, non-excluded columns and their values.
- Method `HashedModel.generate_id` now calls `preimage` internally.

## 0.6.2

- Updated migration system to use the `quote_identifier` and `quote_sql_str_value`
functions for quoting identifiers and string values.
- Updated `quote_identifier` to properly quote components in a multi-part
identifier and raise ValueError when a component has an unmatched double
quotation mark or when the identifier contains a single quote.
- Added new unit tests for `quote_identifier` and `quote_sql_str_value`

## 0.6.1

- Updated query builders to quote identifiers and escape string quotes

## 0.6.0

- Added support for boolean columns in migration system
- Added casting for boolean columns in query builders
- Added new syntax for declaring default column values on classes
- Added new syntax for declaring default column values in migrations
- Updated migration system to quote identifiers
- Updated tools for generating models and migrations from models to support
booleans and default values

## 0.5.3

- Fixed issues with `data_original` property interface (relations, etc.)
- Fixed bugs in `to_sql` method of `SqlQueryBuilder` and `AsyncSqlQueryBuilder`
- Added new syntax for QueryBuilder methods (can not use kwargs to specify
multiple conditions of the same type)

## 0.5.2

- Added change tracking to `SqlModel`, `AsyncSqlModel`, and subclasses
- Added event str as keyword arg for event hook calls: `hook(cls, *args, event=event, **kwargs)`
- Standardized `invoke_hooks` calls to include all non-event name args as kwargs;
  - `invoke_hooks` calls callbacks with `(cls, *args, **kwargs)`, but `*args` will be empty

## 0.5.1

- Fixed documentation links in readme

## 0.5.0

- Added event hook system to `SqlModel` and subclasses

## 0.4.7

- Patch: updated `SqlModel` and `AsyncSqlModel` thinking there was a bug, but
there was not actually a bug .__.

## 0.4.6

- Fix: corrected `HashedModel.update` and `AsyncHashedModel.update` to properly
persist changes to non-committed columns

## 0.4.5

- Fix: corrected ORM property docstring overwrite text (pluralized `within`
and `async_within`)

## 0.4.4

- Improved autodox documentation for library users utilizing the ORM helper
functions by overwriting relation property docstrings

## 0.4.3

- Added dependency on `nest-asyncio==1.6.0`
- Fixed `RuntimeError` issues with async ORM implementation
- Documented async ORM tendency to occasionally produce `ResourceWarning`s

## 0.4.2

- Fixed several interfaces (`Protocol`s) for more accurate type hints

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
