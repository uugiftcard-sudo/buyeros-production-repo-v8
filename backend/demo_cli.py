"""CLI demonstration for BuyerOS.

This simple command line interface allows you to interact with the
SupervisorAgent without running a full web server.  It shows how
persistent memory works by handling refund requests and subsequent
queries about the same transaction id.
"""

from app.workflows.main import create_app  # type: ignore

def main() -> None:
    app = create_app()
    workflow = app.state.workflow
    # Interactive loop
    print("BuyerOS CLI demo. Type 'exit' to quit.")
    while True:
        text = input("您: ")
        if text.strip().lower() in {"exit", "quit"}:
            break
        response = workflow.handle_message(user_id="cli_user", message=text, channel="cli", session_id="cli_user")
        print("AI:", response)


if __name__ == "__main__":
    main()
