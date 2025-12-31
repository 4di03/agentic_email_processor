from email_to_event_service import EmailToEventService, init_email_to_event_service
from test_email_summarizer import haiku, claude_sonnet
from evaluate import MODELS
import argparse
import asyncio 


if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="Test Email to Event Service")
    argparser.add_argument(
        "--model",
        type=str,
        choices=MODELS.keys(),
        default="haiku",
        help="The LLM model to use for the Email to Event Service",
    )
    argparser.add_argument(
        "--dry_run",
        action='store_true',
        help="If set, the service will not create actual calendar events, just print them.",
    )

    argparser.add_argument(
        "--hours-lookback",
        type=int,
        default=6,
        help="Number of hours to look back for emails to process.",
    )

    args = argparser.parse_args()
    model = MODELS[args.model]
    print("Using model:", args.model)
    email_to_event_service = init_email_to_event_service(model=model, with_critic=False, dry_run = args.dry_run)
    created_event_ids = asyncio.run(email_to_event_service.process_emails(lookback_hours=args.hours_lookback))
    print("Created event IDs:", created_event_ids)
