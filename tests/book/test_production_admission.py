from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import yaml

from living_narrative.book.production_admission import (
    ProductionAdmissionController,
    ProductionAdmissionPolicy,
    ProductionAdmissionRequest,
)


def test_admission_limits_parallel_delivery_across_distinct_books(tmp_path: Path) -> None:
    controller = ProductionAdmissionController(
        tmp_path / "scheduler",
        policy=ProductionAdmissionPolicy(max_active_deliveries=1),
        clock=lambda: datetime(2026, 8, 21, 12, 0, tzinfo=UTC),
    )

    first = controller.try_admit(
        ProductionAdmissionRequest(
            book_id="book-alpha",
            provider_profile_id="provider-a/fiction",
        )
    )
    second = controller.try_admit(
        ProductionAdmissionRequest(
            book_id="book-beta",
            provider_profile_id="provider-a/fiction",
        )
    )

    assert first.allowed is True
    assert first.lease is not None
    assert second.allowed is False
    assert second.reason == "parallel delivery limit reached"

    controller.release(first.lease)

    admitted_after_release = controller.try_admit(
        ProductionAdmissionRequest(
            book_id="book-beta",
            provider_profile_id="provider-a/fiction",
        )
    )
    assert admitted_after_release.allowed is True


def test_admission_defers_provider_until_the_configured_rate_window_expires(
    tmp_path: Path,
) -> None:
    current = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
    controller = ProductionAdmissionController(
        tmp_path / "scheduler",
        policy=ProductionAdmissionPolicy(
            provider_window_seconds=60,
            max_deliveries_per_provider_window=1,
        ),
        clock=lambda: current,
    )
    request = ProductionAdmissionRequest(
        book_id="book-alpha",
        provider_profile_id="provider-a/fiction",
    )

    first = controller.try_admit(request)
    assert first.allowed is True
    assert first.lease is not None
    controller.release(first.lease)

    deferred = controller.try_admit(
        ProductionAdmissionRequest(
            book_id="book-beta",
            provider_profile_id="provider-a/fiction",
        )
    )
    assert deferred.allowed is False
    assert deferred.reason == "provider rate limit reached"

    current = current.replace(minute=1)
    admitted_after_window = controller.try_admit(request)
    assert admitted_after_window.allowed is True


def test_admission_reserves_usd_against_the_book_hard_cap(tmp_path: Path) -> None:
    controller = ProductionAdmissionController(
        tmp_path / "scheduler",
        policy=ProductionAdmissionPolicy(),
        clock=lambda: datetime(2026, 8, 21, 12, 0, tzinfo=UTC),
    )
    request = ProductionAdmissionRequest(
        book_id="book-alpha",
        provider_profile_id="provider-a/fiction",
        actual_usd=Decimal("1.00"),
        forecast_usd=Decimal("0.75"),
        hard_usd=Decimal("2.00"),
    )

    first = controller.try_admit(request)
    assert first.allowed is True
    assert first.lease is not None

    deferred = controller.try_admit(request)
    assert deferred.allowed is False
    assert deferred.reason == "book hard USD budget exceeded"

    controller.release(first.lease)
    admitted_after_release = controller.try_admit(request)
    assert admitted_after_release.allowed is True


def test_admission_persists_reader_safe_active_leases_across_controller_restart(
    tmp_path: Path,
) -> None:
    scheduler_root = tmp_path / "scheduler"
    policy = ProductionAdmissionPolicy(max_active_deliveries=1)
    request = ProductionAdmissionRequest(
        book_id="book-alpha",
        provider_profile_id="provider-a/fiction",
    )

    first = ProductionAdmissionController(scheduler_root, policy=policy).try_admit(request)
    assert first.allowed is True

    restarted = ProductionAdmissionController(scheduler_root, policy=policy)
    deferred = restarted.try_admit(
        ProductionAdmissionRequest(
            book_id="book-beta",
            provider_profile_id="provider-a/fiction",
        )
    )

    assert deferred.allowed is False
    snapshot = (scheduler_root / "admission.yaml").read_text(encoding="utf-8")
    assert "book-alpha" in snapshot
    assert "provider-a/fiction" in snapshot
    for forbidden in ("prompt", "credential", "worker", "workspace", "traceback"):
        assert forbidden not in snapshot


def test_expired_admission_no_longer_blocks_new_delivery_or_release(tmp_path: Path) -> None:
    current = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
    controller = ProductionAdmissionController(
        tmp_path / "scheduler",
        policy=ProductionAdmissionPolicy(
            max_active_deliveries=1,
            admission_lease_seconds=60,
        ),
        clock=lambda: current,
    )

    first = controller.try_admit(
        ProductionAdmissionRequest(
            book_id="book-alpha",
            provider_profile_id="provider-a/fiction",
        )
    )
    assert first.lease is not None

    current = current.replace(minute=1, second=1)
    second = controller.try_admit(
        ProductionAdmissionRequest(
            book_id="book-beta",
            provider_profile_id="provider-a/fiction",
        )
    )
    assert second.allowed is True
    assert second.lease is not None

    controller.release(first.lease)
    deferred = controller.try_admit(
        ProductionAdmissionRequest(
            book_id="book-gamma",
            provider_profile_id="provider-a/fiction",
        )
    )
    assert deferred.allowed is False
    assert deferred.reason == "parallel delivery limit reached"


def test_admission_reloads_shared_snapshot_before_each_cross_book_decision(
    tmp_path: Path,
) -> None:
    scheduler_root = tmp_path / "scheduler"
    policy = ProductionAdmissionPolicy(max_active_deliveries=1)
    first_controller = ProductionAdmissionController(scheduler_root, policy=policy)
    second_controller = ProductionAdmissionController(scheduler_root, policy=policy)

    first = first_controller.try_admit(
        ProductionAdmissionRequest(
            book_id="book-alpha",
            provider_profile_id="provider-a/fiction",
        )
    )
    second = second_controller.try_admit(
        ProductionAdmissionRequest(
            book_id="book-beta",
            provider_profile_id="provider-a/fiction",
        )
    )

    assert first.allowed is True
    assert second.allowed is False
    assert second.reason == "parallel delivery limit reached"


def test_admission_records_reader_safe_admit_and_release_events(tmp_path: Path) -> None:
    scheduler_root = tmp_path / "scheduler"
    controller = ProductionAdmissionController(
        scheduler_root,
        policy=ProductionAdmissionPolicy(),
        clock=lambda: datetime(2026, 8, 21, 12, 0, tzinfo=UTC),
    )

    admitted = controller.try_admit(
        ProductionAdmissionRequest(
            book_id="book-alpha",
            provider_profile_id="provider-a/fiction",
            forecast_usd=Decimal("0.75"),
        )
    )
    assert admitted.lease is not None
    controller.release(admitted.lease)

    events = [
        yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in sorted((scheduler_root / "events").glob("*.yaml"))
    ]

    assert [event["event"] for event in events] == ["admitted", "released"]
    assert events[0]["book_id"] == "book-alpha"
    assert events[0]["provider_profile_id"] == "provider-a/fiction"
    assert events[0]["forecast_usd"] == "0.75"
    for event in events:
        serialized = yaml.safe_dump(event, allow_unicode=True)
        for forbidden in ("prompt", "credential", "worker", "workspace", "traceback"):
            assert forbidden not in serialized
