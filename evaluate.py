import asyncio
from email_summarizer import EmailSummarizer, EmailSummaryResponseFormat, _init_email_summarizer_agent, _init_critic_agent
from llm_service import LocalLlamaService
from email_service import EmailService, Email
import json
import random
from test_email_summarizer import claude_sonnet, haiku, llama
import argparse
EVAL_SET_SIZE = 100
EVAL_SET_PATH = "evaluation_dataset.json"

MODELS = {
    "claude": claude_sonnet,
    "llama": llama,
    "haiku": haiku # cheap but reliable
}


def from_json_list(json_file_path : str, n : int = 100) -> dict[str, tuple[Email, bool]]:
    with open(json_file_path, 'r') as f:
        email_list_json = json.load(f)
    
    email_list_json = random.sample(email_list_json, min(n, len(email_list_json)))


    email_by_subject = {}
    for email_json in email_list_json:
        subject = email_json['subject']
        email_by_subject[subject] = (Email(subject=email_json['subject'], body=email_json['body']), email_json['is_important'])
    
    return email_by_subject
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Evaluate Email Summarizer")
    parser.add_argument(
        "--model",
        type=str,
        choices=MODELS.keys(),
        default="haiku",
        help="The LLM model to use for evaluation",
    )
    args = parser.parse_args()

    model = MODELS[args.model]
    print("Using model:", args.model)


    emails_by_subject= from_json_list(EVAL_SET_PATH,n = EVAL_SET_SIZE)
    eval_emails = [eval_email for eval_email, _ in emails_by_subject.values()]

    agent = _init_email_summarizer_agent(model)
    critic_agent = _init_critic_agent(model)
    llm_service = LocalLlamaService()
    email_service = EmailService.create_email_service()
    email_summarizer = EmailSummarizer(agent, email_service, critic_agent= critic_agent)


    summaries = asyncio.run(email_summarizer._summarize_emails_async(eval_emails, concurrency=10))
    



    tp = 0
    fp = 0
    tn = 0
    fn = 0

    subjects_in_summary = set()

    for summary_obj in  summaries:
        subject = summary_obj.email.subject

        eval_email, eval_is_important = emails_by_subject[subject]
        llm_is_important = summary_obj.is_important

        if eval_is_important and llm_is_important:
            tp += 1
        
        if eval_is_important and not llm_is_important:
            fn += 1
            print("Missed Important Email:\n", str(eval_email), "\nJustification:", summary_obj.justification)
        
        if not eval_is_important and llm_is_important:
            fp += 1
            print("Wrongly Labeled Email as Important:\n", str(eval_email), "\nJustification:", summary_obj.justification)
        
        if not eval_is_important and not llm_is_important:
            tn += 1
    


    print(f"TP: {tp}, FP: {fp}, TN: {tn}, FN: {fn}")
    # precison = of all the emails labeled as important by our agent, how many were actually important
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    # recall = of all the actually important emails, how many did our agent label as important
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    print(f"Precision: {precision:.2f}, Recall: {recall:.2f}, F1 Score: {f1:.2f}")


