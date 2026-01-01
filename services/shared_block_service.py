"""
Shared Calendar Block Service

Handles calculation and synchronization of shared calendar blocks.
Blocks are fused time ranges shown to family with simplified titles.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from logging import Logger

from extensions import db
from models import Todo
from services.calendar_service import CalendarService
from time_utils import get_local_tz, now_local

# Work hours constants (for block fusion)
WORK_START = time(7, 0)
WORK_END = time(17, 30)


@dataclass
class Block:
    """Represents a time block for the shared calendar."""

    start: time
    end: time
    date: date
    titles: set[str] = field(default_factory=set)
    todo_ids: list[int] = field(default_factory=list)

    @property
    def title(self) -> str:
        """Get formatted title from all unique titles."""
        # Filter out None values and sort for consistent ordering
        valid_titles = sorted(t for t in self.titles if t)
        return ", ".join(valid_titles) if valid_titles else "Busy"

    @property
    def start_datetime(self) -> datetime:
        """Get start as datetime."""
        tz = get_local_tz()
        return datetime.combine(self.date, self.start, tzinfo=tz)

    @property
    def end_datetime(self) -> datetime:
        """Get end as datetime."""
        tz = get_local_tz()
        return datetime.combine(self.date, self.end, tzinfo=tz)

    def has_started(self) -> bool:
        """Check if this block has already started."""
        now = now_local()
        return now >= self.start_datetime


def _is_within_work_hours(t: time) -> bool:
    """Check if a time is within work hours (7:00-17:30)."""
    return WORK_START <= t <= WORK_END


def _calculate_end_time(todo: Todo) -> time:
    """Calculate end time for a todo based on end_time or duration."""
    if todo.end_time:
        return todo.end_time
    if todo.duration_minutes and todo.due_time:
        start_dt = datetime.combine(date.today(), todo.due_time)
        end_dt = start_dt + timedelta(minutes=todo.duration_minutes)
        return end_dt.time()
    # Default: 1 hour duration
    if todo.due_time:
        start_dt = datetime.combine(date.today(), todo.due_time)
        end_dt = start_dt + timedelta(hours=1)
        return end_dt.time()
    return todo.due_time  # Fallback


def _minutes_between(end_time: time, start_time: time) -> int:
    """Calculate minutes between two times (assumes same day)."""
    end_dt = datetime.combine(date.today(), end_time)
    start_dt = datetime.combine(date.today(), start_time)
    delta = start_dt - end_dt
    return int(delta.total_seconds() / 60)


def _should_include_completed_todo(todo: Todo, block_date: date) -> bool:
    """
    Determine if a completed todo should be included in block calculation.

    Rules:
    - If block has started (current time >= block start): include completed todos
    - If block is in future: exclude completed todos
    """
    if todo.status != "completed":
        return True  # Not completed, always include

    if not todo.due_time:
        return True  # All-day event, include

    now = now_local()
    block_start_dt = datetime.combine(block_date, todo.due_time, tzinfo=get_local_tz())

    # If the block has started, keep completed todos
    return now >= block_start_dt


def calculate_blocks_for_day(
    todos: list[Todo],
    target_date: date,
    logger: Logger | None = None,
) -> list[Block]:
    """
    Calculate shared calendar blocks from todos for a specific day.

    Fusion rules:
    1. All todos between 7:00-17:30 fuse into ONE block (work hours)
    2. Outside work hours, todos with gap <= 1 hour fuse together
    3. Outside work hours, todos with gap > 1 hour become separate blocks

    Args:
        todos: List of todos for the day
        target_date: The date to calculate blocks for
        logger: Optional logger

    Returns:
        List of Block objects to sync to shared calendar
    """
    # Filter: only timed todos marked for shared calendar
    timed_todos = [
        t
        for t in todos
        if t.due_time and t.sync_to_shared and t.due_date == target_date
    ]

    # Filter based on completion rules
    timed_todos = [
        t for t in timed_todos if _should_include_completed_todo(t, target_date)
    ]

    if not timed_todos:
        return []

    # Sort by start time
    timed_todos.sort(key=lambda t: t.due_time)

    blocks: list[Block] = []
    current_block: Block | None = None

    for todo in timed_todos:
        start = todo.due_time
        end = _calculate_end_time(todo)
        shared_title = todo.shared_title or "Busy"

        if current_block is None:
            # First todo starts a new block
            current_block = Block(
                start=start,
                end=end,
                date=target_date,
                titles={shared_title},
                todo_ids=[todo.id],
            )
        else:
            gap_minutes = _minutes_between(current_block.end, start)

            # Check if both current block and this todo are in work hours
            both_in_work_hours = (
                _is_within_work_hours(current_block.start)
                and _is_within_work_hours(current_block.end)
                and _is_within_work_hours(start)
                and _is_within_work_hours(end)
            )

            # FUSION RULES
            if both_in_work_hours:
                # Priority 1: Always fuse within work hours
                current_block.end = max(current_block.end, end)
                current_block.titles.add(shared_title)
                current_block.todo_ids.append(todo.id)
                if logger:
                    logger.debug(
                        f"Fused (work hours): {todo.title} into block {current_block.start}-{current_block.end}"
                    )
            elif gap_minutes <= 60:
                # Priority 2: Fuse if gap <= 1 hour
                current_block.end = max(current_block.end, end)
                current_block.titles.add(shared_title)
                current_block.todo_ids.append(todo.id)
                if logger:
                    logger.debug(
                        f"Fused (gap={gap_minutes}min): {todo.title} into block"
                    )
            else:
                # Priority 3: Gap > 1 hour, start new block
                blocks.append(current_block)
                current_block = Block(
                    start=start,
                    end=end,
                    date=target_date,
                    titles={shared_title},
                    todo_ids=[todo.id],
                )
                if logger:
                    logger.debug(f"New block (gap={gap_minutes}min): {todo.title}")

    # Don't forget the last block
    if current_block:
        blocks.append(current_block)

    if logger:
        logger.info(
            f"Calculated {len(blocks)} blocks for {target_date} from {len(timed_todos)} todos"
        )

    return blocks


class SharedBlockService:
    """Service for managing shared calendar blocks."""

    def __init__(
        self,
        calendar_service: CalendarService,
        logger: Logger | None = None,
    ) -> None:
        """
        Initialize shared block service.

        Args:
            calendar_service: CalendarService instance for API calls
            logger: Optional logger
        """
        self.calendar_service = calendar_service
        self.logger = logger

    def sync_blocks_for_day(
        self,
        user: Any,
        target_date: date,
        oauth_client: Any,
        token: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Synchronize shared calendar blocks for a specific day.

        This:
        1. Calculates what blocks should exist based on todos
        2. Compares with existing shared_event_ids
        3. Creates, updates, or deletes blocks as needed

        Args:
            user: User object (must have shared_calendar_id)
            target_date: Date to sync blocks for
            oauth_client: OAuth client for API calls
            token: OAuth token dict

        Returns:
            Dict with sync results: {created: int, updated: int, deleted: int, errors: list}
        """
        results = {"created": 0, "updated": 0, "deleted": 0, "errors": []}

        if not user.shared_calendar_id:
            if self.logger:
                self.logger.warning(
                    f"User {user.id} has no shared_calendar_id configured"
                )
            return results

        # Get all todos for this user on this date that are marked for shared sync
        todos = Todo.query.filter(
            Todo.user_id == user.id,
            Todo.due_date == target_date,
            Todo.sync_to_shared == True,  # noqa: E712
        ).all()

        # Calculate what blocks should exist
        target_blocks = calculate_blocks_for_day(todos, target_date, self.logger)

        # Get todos that currently have shared_event_ids (existing blocks)
        todos_with_shared_events = [t for t in todos if t.shared_event_id]

        # Strategy: Delete all existing shared events, create new ones
        # This is simpler than trying to match/update blocks
        # (blocks can merge/split in complex ways)

        # Delete existing shared events
        deleted_event_ids = set()
        for todo in todos_with_shared_events:
            if todo.shared_event_id and todo.shared_event_id not in deleted_event_ids:
                success = self.calendar_service.delete_event(
                    oauth_client,
                    token,
                    todo.shared_event_id,
                    calendar_id=user.shared_calendar_id,
                )
                if success and success != "token_invalid":
                    deleted_event_ids.add(todo.shared_event_id)
                    results["deleted"] += 1
                elif success == "token_invalid":
                    results["errors"].append("Token invalid - re-authentication needed")
                    return results

        # Clear shared_event_ids from all todos
        for todo in todos:
            if todo.shared_event_id:
                todo.shared_event_id = None

        # Create new blocks
        for block in target_blocks:
            event_result = self.calendar_service.create_event(
                oauth_client,
                token,
                title=block.title,
                start_time=block.start_datetime,
                end_time=block.end_datetime,
                calendar_id=user.shared_calendar_id,
            )

            if event_result and "id" in event_result:
                results["created"] += 1
                # Associate this event ID with all todos in the block
                for todo_id in block.todo_ids:
                    todo = Todo.query.get(todo_id)
                    if todo:
                        todo.shared_event_id = event_result["id"]
            elif event_result and event_result.get("error") == "token_invalid":
                results["errors"].append("Token invalid - re-authentication needed")
                return results
            else:
                results["errors"].append(f"Failed to create block: {block.title}")

        db.session.commit()

        if self.logger:
            self.logger.info(
                f"Synced blocks for {target_date}: "
                f"created={results['created']}, deleted={results['deleted']}, "
                f"errors={len(results['errors'])}"
            )

        return results

    def sync_blocks_for_dates(
        self,
        user: Any,
        dates: list[date],
        oauth_client: Any,
        token: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Sync blocks for multiple dates.

        Args:
            user: User object
            dates: List of dates to sync
            oauth_client: OAuth client
            token: OAuth token

        Returns:
            Aggregated sync results
        """
        total_results = {"created": 0, "updated": 0, "deleted": 0, "errors": []}

        for d in dates:
            day_results = self.sync_blocks_for_day(user, d, oauth_client, token)
            total_results["created"] += day_results["created"]
            total_results["updated"] += day_results["updated"]
            total_results["deleted"] += day_results["deleted"]
            total_results["errors"].extend(day_results["errors"])

            # Stop if we hit a token error
            if any("token" in e.lower() for e in day_results["errors"]):
                break

        return total_results

    def remove_todo_from_shared(
        self,
        todo: Todo,
        user: Any,
        oauth_client: Any,
        token: dict[str, Any],
    ) -> bool:
        """
        Remove a todo's contribution from shared calendar and recalculate blocks.

        Args:
            todo: Todo being removed/unmarked
            user: User object
            oauth_client: OAuth client
            token: OAuth token

        Returns:
            True if successful
        """
        if not todo.due_date:
            return True

        # Resync the entire day to recalculate blocks
        results = self.sync_blocks_for_day(user, todo.due_date, oauth_client, token)

        return len(results["errors"]) == 0
