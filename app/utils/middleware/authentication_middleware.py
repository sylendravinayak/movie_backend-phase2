from fastapi import Request, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse



class AuthorizationMiddleware(BaseHTTPMiddleware):

    def dispatch(self, request: Request, call_next):


        public_paths = [
            '/', '/users/login', '/users/signup', '/secure-data',
            '/docs', '/docs/oauth2-redirect', '/openapi.json', '/redoc'
        ]
        url = request.url.path

        if url in public_paths:
            # skip and move to the end point
            return call_next(request) 
        
        
        
        return call_next(request)