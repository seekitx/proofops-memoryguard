from proofops_memoryguard.rate_limit import FixedWindowRateLimiter


def test_rate_limiter_blocks_then_recovers_after_window() -> None:
    now = [100.0]
    limiter = FixedWindowRateLimiter(limit=2, window_seconds=10, clock=lambda: now[0])

    assert limiter.allow("client-a") == (True, 0)
    assert limiter.allow("client-a") == (True, 0)
    allowed, retry_after = limiter.allow("client-a")
    assert allowed is False
    assert retry_after >= 1

    now[0] = 111.0
    assert limiter.allow("client-a") == (True, 0)


def test_rate_limiter_keeps_clients_separate() -> None:
    limiter = FixedWindowRateLimiter(limit=1, window_seconds=60, clock=lambda: 1.0)

    assert limiter.allow("client-a") == (True, 0)
    assert limiter.allow("client-b") == (True, 0)


def test_rate_limiter_caps_cold_client_buckets() -> None:
    now = [1.0]
    limiter = FixedWindowRateLimiter(
        limit=1,
        window_seconds=60,
        max_keys=2,
        clock=lambda: now[0],
    )
    assert limiter.allow("client-a") == (True, 0)
    now[0] = 2.0
    assert limiter.allow("client-b") == (True, 0)
    now[0] = 3.0
    assert limiter.allow("client-c") == (True, 0)
    assert len(limiter._buckets) == 2
