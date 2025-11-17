#!/bin/bash

pip install .
autodox -include_dunder -exclude_name=__subclasshook__,__name__,__doc__,__package__,__loader__,__spec__,__path__,__file__,__cached__,__builtins__ sqloquent > dox.md
autodox -include_dunder -exclude_name=__subclasshook__,__name__,__doc__,__package__,__loader__,__spec__,__path__,__file__,__cached__,__builtins__ sqloquent.asyncql > asyncql_dox.md
autodox -include_dunder -exclude_name=mappingproxy,traceback,Protocol,runtime_checkable,annotations,Any,Callable,Generator,Iterable,Optional,Type,Union,__name__,__doc__,__package__,__loader__,__spec__,__file__,__cached__,__builtins__,__subclasshook__ sqloquent.interfaces > interfaces.md
autodox -include_dunder -exclude_name=mappingproxy,traceback,Protocol,runtime_checkable,annotations,Any,RowProtocol,Callable,AsyncGenerator,Iterable,Optional,Type,Union,__name__,__doc__,__package__,__loader__,__spec__,__file__,__cached__,__builtins__,__subclasshook__ sqloquent.asyncql.interfaces > async_interfaces.md
autodox -exclude_name=Default,SqlModel,DeletedModel,HashedModel,Attachment,MigrationProtocol,ModelProtocol,Migration,Table,datetime,module,NoneType,UnionType,tert,vert,tressa,isdir,isfile,get_args,listdir,environ,argv,Any,Type,version sqloquent.tools > tools.md
pip uninstall sqloquent -y
