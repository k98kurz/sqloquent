# setup

```bash
pip install .
pip install autodox
```

# dox sqloquent

```bash
autodox -include_private sqloquent > dox.md
```

# dox sqloquent.interfaces

```bash
autodox -include_private -exclude_name=traceback,Protocol,runtime_checkable,annotations,Any,Callable,Generator,Iterable,Optional,Type,Union sqloquent.interfaces > interfaces.md
```

# dox sqloquent.tools

```bash
autodox -exclude_name=SqliteModel,DeletedModel,Attachment,MigrationProtocol,ModelProtocol,Migration,Table,datetime,module,NoneType,UnionType,tert,vert,tressa,isdir,isfile,get_args,listdir,environ,argv,Any,Type sqloquent.tools > tools.md
```
