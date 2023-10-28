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
