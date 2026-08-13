from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError, ApplicationErrorCategory


def error_type(err: BaseException | None) -> str | None:
    """
    The Temporal failure type of an error - the explicit ApplicationError
    type when set, the class name otherwise - mirroring how the server
    matches errors against RetryPolicy.non_retryable_error_types.
    """
    if err is None:
        return None

    return (
        err.type
        if isinstance(err, ApplicationError) and err.type
        else type(err).__name__
    )


def is_final_attempt(
    attempt: int,
    err: BaseException | None,
    retry_policy: RetryPolicy | None,
) -> bool:
    """
    Whether Temporal will not retry the failure: the retry policy's attempts
    are exhausted or the error is non-retryable. Retries cut off by
    schedule_to_close_timeout are not detectable worker-side and count as
    not final.
    """
    if isinstance(err, ApplicationError) and err.non_retryable:
        # the activity marked the error itself as non-retryable when raising
        return True

    if retry_policy is None:
        # unknown policy - Temporal defaults to endless retries
        return False

    if error_type(err) in (retry_policy.non_retryable_error_types or ()):
        # the workflow's retry policy declares the error type non-retryable
        return True

    # the policy's attempts are exhausted (0 means unlimited retries)
    return (
        bool(retry_policy.maximum_attempts) and attempt >= retry_policy.maximum_attempts
    )


def should_log_failure(
    attempt: int,
    err: BaseException | None,
    retry_policy: RetryPolicy | None,
    attempts: tuple[int, ...],
    every: int | None,
) -> bool:
    """
    The shared throttling decision of ActivityFailureLoggingInterceptor and
    ActivityFailureThrottleFilter.
    """
    if (
        isinstance(err, ApplicationError)
        and err.category == ApplicationErrorCategory.BENIGN
    ):
        # the raiser deliberately marked the failure as expected behavior,
        # the SDK itself downgrades its own log for these to DEBUG
        return False

    if is_final_attempt(attempt, err, retry_policy):
        return True

    if retry_policy and retry_policy.maximum_attempts:
        # limited retries - only the final failure (handled above) is worth
        # logging, earlier attempts may yet succeed
        return False

    if attempt in attempts:
        return True

    return attempt % every == 0 if every else False
