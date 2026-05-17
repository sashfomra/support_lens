"""Stripe-specific synthetic support tickets and KB articles for demo."""
from datetime import datetime, timezone, timedelta
import random

AGENTS = [
    {"id": "agent-1", "name": "Sarah Chen"},
    {"id": "agent-2", "name": "Marcus Williams"},
    {"id": "agent-3", "name": "Priya Patel"},
    {"id": "agent-4", "name": "James O'Brien"},
]

KB_ARTICLES = []

TICKETS = [
    {
        "subject": "Need to issue a partial refund",
        "description": "A customer returned one item from their order (ch_3L9xYZ). How do I issue a partial refund instead of refunding the whole amount?",
        "customer_name": "Alex Mercer",
        "customer_email": "alex.m@example.com",
        "customer_tier": "premium",
        "source": "ticket",
    },
    {
        "subject": "Customer filed a dispute",
        "description": "I just received an email that a customer filed a dispute for charge ch_1GqIC8. They claim they never received the product. How do I submit evidence to win this dispute?",
        "customer_name": "Linda Wu",
        "customer_email": "linda.wu@techco.io",
        "customer_tier": "enterprise",
        "source": "ticket",
    },
    {
        "subject": "Canceling a subscription at period end",
        "description": "One of my users wants to cancel their subscription, but they want it to remain active until the end of the current billing cycle. How do I configure that in the dashboard?",
        "customer_name": "Kevin Smith",
        "customer_email": "ksmith@mac.com",
        "customer_tier": "standard",
        "source": "ticket",
    },
    {
        "subject": "Refund taking too long",
        "description": "I refunded a customer 10 days ago (re_3M2xyz) and they are complaining that the money still isn't in their bank account. What's the timeline and what should I tell them?",
        "customer_name": "Dan Rogers",
        "customer_email": "dan@notion-user.com",
        "customer_tier": "standard",
        "source": "email",
    },
    {
        "subject": "Lost a dispute due to lack of evidence",
        "description": "We just lost a $500 dispute because we didn't submit evidence in time. Is there any way to appeal this decision now that the dispute is closed?",
        "customer_name": "Sarah Jenkins",
        "customer_email": "sarah.j@company.net",
        "customer_tier": "premium",
        "source": "ticket",
    },
    {
        "subject": "Cancel subscription immediately",
        "description": "A user violated our terms of service. I need to cancel their subscription immediately and not wait until the end of the month. Does this automatically refund them or do I need to do that separately?",
        "customer_name": "Chloe Adams",
        "customer_email": "chloe@startup.io",
        "customer_tier": "standard",
        "source": "ticket",
    },
    {
        "subject": "How to prevent fraud disputes?",
        "description": "We've been getting a lot of fraudulent disputes lately. What tools or settings does Stripe provide to help us prevent these fraudulent charges before they happen?",
        "customer_name": "Marcus Reid",
        "customer_email": "mreid@agency.com",
        "customer_tier": "standard",
        "source": "email",
    },
    {
        "subject": "Can I cancel a refund?",
        "description": "I accidentally clicked refund on the wrong charge (ch_999xyz). It just happened 2 minutes ago. Can I cancel the refund before it reaches the customer's bank?",
        "customer_name": "Elena Rodriguez",
        "customer_email": "elena.r@enterprise.org",
        "customer_tier": "enterprise",
        "source": "ticket",
    },
    {
        "subject": "Proration when canceling",
        "description": "If a customer cancels their subscription in the middle of the month, does Stripe automatically calculate the prorated amount to refund them, or do I have to calculate it manually?",
        "customer_name": "Tyler Durden",
        "customer_email": "tyler@paper.com",
        "customer_tier": "premium",
        "source": "ticket",
    },
    {
        "subject": "Dispute fee refund",
        "description": "If we submit evidence and win a dispute in our favor, do we get the $15 dispute fee refunded back to our account?",
        "customer_name": "Fiona Gallagher",
        "customer_email": "fiona.g@southside.com",
        "customer_tier": "standard",
        "source": "email",
    }
]
