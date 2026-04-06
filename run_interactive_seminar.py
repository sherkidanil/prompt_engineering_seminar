from interactive_seminar.app import create_app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("run_interactive_seminar:app", host="127.0.0.1", port=8000, reload=False)
