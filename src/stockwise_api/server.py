from stockwise_api.runtime import configure_windows_event_loop_policy


def main() -> None:
    configure_windows_event_loop_policy()

    import uvicorn

    uvicorn.run(
        "stockwise_api.api.app:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
    )


if __name__ == "__main__":
    main()
