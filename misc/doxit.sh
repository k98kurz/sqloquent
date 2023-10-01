#!/bin/bash

source venv/bin/activate
pip install .
autodox -include_private sqloquent > dox.md
autodox -include_dunder -exclude_name=traceback,Protocol,runtime_checkable,annotations,Any,Callable,Generator,Iterable,Optional,Type,Union,__name__,__doc__,__package__,__loader__,__spec__,__file__,__cached__,__builtins__ sqloquent.interfaces > interfaces.md
autodox -exclude_name=SqlModel,DeletedModel,HashedModel,Attachment,MigrationProtocol,ModelProtocol,Migration,Table,datetime,module,NoneType,UnionType,tert,vert,tressa,isdir,isfile,get_args,listdir,environ,argv,Any,Type sqloquent.tools > tools.md
