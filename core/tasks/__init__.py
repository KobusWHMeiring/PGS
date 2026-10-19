"""Celery tasks.

Every task declares `autoretry_for`, `max_retries` and `default_retry_delay`;
A6's meta-test asserts this for all of them rather than trusting review.
"""
