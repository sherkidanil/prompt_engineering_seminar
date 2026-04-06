from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI()

    @app.get("/api/health")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return app
