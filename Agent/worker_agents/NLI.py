#Natural Language Intent to determine the intent of the query
from transformers import pipeline
import torch
NLI_MODEL = "facebook/bart-large-mnli"


INTENTS = [
    "Delivery / Shipping Issue",
    "Customer Service Complaint / Escalation",
    "Device & App Technical Support",
    "Damaged / Wrong / Defective Item",
    "Order Cancellation / Refund",
    "Payment, Billing & Gift Card Issues",
    "Account Access & Security",
    "Pre-order Issues",
    "Prime Membership & Billing",
    "Resolved / Successful Query",   # thanks, confirmation, issue resolved
]

device = 0 if torch.cuda.is_available() else -1
print(f"Using {'GPU' if device == 0 else 'CPU'} for NLI inference")

classifier = pipeline(
    "zero-shot-classification",
    model=NLI_MODEL,
    device=device,
)

def classify_content(text):
    results = classifier(
        [text],
        candidate_intents = INTENTS,
        multi_label = True,
        confidence_threshold = 0.3,
    )
    return results





    