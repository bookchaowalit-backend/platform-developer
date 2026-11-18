from fastapi import Depends, HTTPException, Query
from fastapi.routing import APIRoute
from platform_backend_core import create_app as base_app
from platform_backend_core import require_scope
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware import Middleware

from ._sentry import CaptureErrors
from .store import Conflict, FlagStore, InvalidInput


class Flag(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    enabled:bool
    rollout:int=Field(ge=0,le=10000)
    subjects:list[str]=Field(default_factory=list,max_length=100)
    version:int|None=Field(default=None,ge=1)
class Evaluation(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    subject:str=Field(min_length=1,max_length=128)
NOT_PUBLIC=frozenset({'/docs','/docs/oauth2-redirect','/redoc','/metrics'})
def create_app(database,verifier):
    app=base_app('developer',database,verifier,max_body_bytes=32768);store=FlagStore(database)
    # Only probes, the API and its schema are public: no docs UI, and metrics need a scope.
    metrics=next(r.endpoint for r in app.router.routes if isinstance(r,APIRoute) and r.path=='/metrics')
    app.router.routes=[r for r in app.router.routes if getattr(r,'path',None) not in NOT_PUBLIC]
    app.docs_url=app.redoc_url=None
    app.add_api_route('/metrics',metrics,methods=['GET'],include_in_schema=False,dependencies=[Depends(require_scope('metrics:read'))])
    # Last in the list = innermost: inside the core boundary that turns errors into a 500.
    app.user_middleware.append(Middleware(CaptureErrors))
    app.state.readiness_checks['flags_schema']=store.ready
    @app.exception_handler(Conflict)
    async def conflict(request,exc):
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail':'Version conflict'},409)
    @app.exception_handler(InvalidInput)
    async def invalid(request,exc):
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail':'Invalid input'},422)
    @app.get('/v1/flags')
    def listing(limit:int=Query(100,ge=1,le=100),after:str=Query('',max_length=64),p=Depends(require_scope('flags:read'))):return store.list(p.workspace,limit,after)
    @app.put('/v1/flags/{name}')
    def put(name:str,body:Flag,p=Depends(require_scope('flags:write'))):return store.put(p.workspace,name,body.enabled,body.rollout,body.subjects,body.version)
    @app.get('/v1/flags/{name}')
    def get(name:str,p=Depends(require_scope('flags:read'))):
        row=store.get(p.workspace,name)
        if row is None:raise HTTPException(404,'Not found')
        return row
    @app.delete('/v1/flags/{name}',status_code=204)
    def delete(name:str,version:int=Query(ge=1),p=Depends(require_scope('flags:write'))):store.delete(p.workspace,name,version)
    @app.post('/v1/flags/{name}/evaluate')
    def evaluate(name:str,body:Evaluation,p=Depends(require_scope('flags:read'))):return {'enabled':store.evaluate(p.workspace,name,body.subject)}
    return app
