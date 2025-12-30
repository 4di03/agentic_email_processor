from email_summarizer import EmailSummarizer
from llm_service import LocalLlamaService
from email_service import EmailService, Email
import json
import random

EVAL_SET_SIZE = 10
EVAL_SET_PATH = "evaluation_dataset.json"


def from_json_list(json_file_path : str, n : int = 100) -> tuple[list['Email'], list[bool]]:
    with open(json_file_path, 'r') as f:
        email_list_json = json.load(f)
    
    email_list_json = random.sample(email_list_json, min(n, len(email_list_json)))

    return [Email(subject=email_json['subject'], body=email_json['body']) for email_json in email_list_json], [email_json['is_important'] for email_json in email_list_json]

if __name__ == "__main__":
    eval_emails, should_include = from_json_list(EVAL_SET_PATH,n = EVAL_SET_SIZE)
    
    emails_by_subject = {email.subject: email for email in eval_emails}


    llm_service = LocalLlamaService()
    email_service = EmailService.create_email_service()
    email_summarizer = EmailSummarizer(llm_service, email_service)
    summary = email_summarizer._summarize_emails(eval_emails)
    print("Email Summary:\n", summary)
    # parse json from summary
    summary_objs = json.loads(summary)


    tp = 0
    fp = 0
    tn = 0
    fn = 0

    subjects_in_summary = set()

    for summary_obj in  summary_objs:
        subject = summary_obj['subject']

        eval_email = emails_by_subject[subject]
        should_include = summary_obj['is_important']

        if should_include:
            tp += 1
        else:
            fp += 1
        subjects_in_summary.add(subject)


    for eval_email, should_include in zip(eval_emails, should_include):
        if eval_email.subject not in subjects_in_summary:
            if should_include:
                fn += 1
            else:
                tn += 1

    print(f"TP: {tp}, FP: {fp}, TN: {tn}, FN: {fn}")
    # precison = of all the emails labeled as important by our agent, how many were actually important
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    # recall = of all the actually important emails, how many did our agent label as important
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    print(f"Precision: {precision:.2f}, Recall: {recall:.2f}, F1 Score: {f1:.2f}")


