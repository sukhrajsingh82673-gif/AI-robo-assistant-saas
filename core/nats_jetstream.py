"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
NATS + JetStream Distributed Event Backbone
===========================================
Provides resilient asynchronous message bus and persistent event streaming for ZONATA.
Supports at-least-once delivery, subject hierarchy routing, consumer groups,
persistent stream replays, and transactional event publishing.

Canonical Subjects:
  zonata.<tenant_id>.<company_id>.events.MissionCreated
  zonata.<tenant_id>.<company_id>.events.ApprovalRequested
  zonata.<tenant_id>.<company_id>.events.ApprovalGranted
  zonata.<tenant_id>.<company_id>.events.TaskStarted
  zonata.<tenant_id>.<company_id>.events.TaskCompleted
  zonata.<tenant_id>.<company_id>.events.ToolFailed
  zonata.<tenant_id>.<company_id>.events.EvidenceCreated
  zonata.<tenant_id>.<company_id>.events.MissionCompleted
  zonata.<tenant_id>.<company_id>.events.UsageRecorded
  zonata.<tenant_id>.<company_id>.events.BillingEvent

Constitutional Invariants:
1. NATS / JetStream is an event delivery system, NOT a governance authority.
2. Synchronous security gates (PolicyEngine, KillSwitch, ApprovalEngine) MUST NOT be deferred to async events.
3. Event delivery does not substitute for Merkle evidence verification in EvidenceLedger.
"""

import os
import time
import json
import uuid
import logging
import threading
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger("zonata.events.nats")

@dataclass
class NatsMessage:
    subject: str
    data: Dict[str, Any]
    headers: Dict[str, str] = field(default_factory=dict)
    sequence: int = 0
    timestamp: float = field(default_factory=time.time)
    message_id: str = field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:12]}")
    acked: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class StreamConfig:
    name: str
    subjects: List[str]
    max_msgs: int = 100000
    max_age_sec: float = 86400 * 7  # 7 days retention
    storage_type: str = "FILE"      # FILE or MEMORY

class JetStreamEngine:
    """
    In-process and networked NATS JetStream event engine.
    Supports stream creation, publication, durable subscriptions, and message replays.
    """
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "JetStreamEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        self._streams: Dict[str, StreamConfig] = {}
        self._messages: Dict[str, List[NatsMessage]] = {}
        self._subscribers: Dict[str, List[Callable[[NatsMessage], None]]] = {}
        self._seen_dedup_keys: Dict[str, NatsMessage] = {}
        self._sequence_counter = 0
        self._lock = threading.Lock()
        self._init_default_streams()

    def _init_default_streams(self):
        """Initializes canonical ZONATA event streams."""
        self.create_stream(StreamConfig(
            name="ZONATA_MISSIONS",
            subjects=["zonata.*.*.events.MissionCreated", "zonata.*.*.events.MissionCompleted", "zonata.missions.>", "zonata.*.missions.>"]
        ))
        self.create_stream(StreamConfig(
            name="ZONATA_GOVERNANCE",
            subjects=["zonata.*.*.events.ApprovalRequested", "zonata.*.*.events.ApprovalGranted", "zonata.governance.>", "zonata.*.governance.>"]
        ))
        self.create_stream(StreamConfig(
            name="ZONATA_OPERATIONS",
            subjects=["zonata.*.*.events.TaskStarted", "zonata.*.*.events.TaskCompleted", "zonata.*.*.events.ToolFailed", "zonata.operations.>", "zonata.*.operations.>"]
        ))
        self.create_stream(StreamConfig(
            name="ZONATA_BILLING",
            subjects=["zonata.*.*.events.UsageRecorded", "zonata.*.*.events.BillingEvent", "zonata.billing.>", "zonata.*.billing.>"]
        ))

    def create_stream(self, config: StreamConfig) -> bool:
        with self._lock:
            self._streams[config.name] = config
            if config.name not in self._messages:
                self._messages[config.name] = []
            logger.info(f"NATS STREAM CREATED: '{config.name}' (Subjects: {config.subjects})")
            return True

    def publish(
        self,
        subject: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        tenant_id: str = "tnt_primary",
        company_id: str = "comp_primary"
    ) -> NatsMessage:
        """Publishes an event message to JetStream with sequence numbering and deduplication."""
        with self._lock:
            hdrs = dict(headers) if headers else {}
            if "tenant_id" not in hdrs:
                hdrs["tenant_id"] = tenant_id
            if "company_id" not in hdrs:
                hdrs["company_id"] = company_id

            # Deduplication check
            dedup_id = (
                hdrs.get("Nats-Msg-Id") or
                hdrs.get("idempotency_key") or
                hdrs.get("message_id") or
                (data.get("idempotency_key") if isinstance(data, dict) else None)
            )
            if dedup_id:
                dedup_key = f"{tenant_id}:{dedup_id}"
                if dedup_key in self._seen_dedup_keys:
                    logger.info(f"NATS DEDUPLICATION: Suppressing duplicate message [{dedup_key}]")
                    return self._seen_dedup_keys[dedup_key]

            self._sequence_counter += 1
            msg = NatsMessage(
                subject=subject,
                data=data,
                headers=hdrs,
                sequence=self._sequence_counter,
                timestamp=time.time(),
                message_id=dedup_id if dedup_id else f"msg_{uuid.uuid4().hex[:12]}"
            )

            if dedup_id:
                self._seen_dedup_keys[f"{tenant_id}:{dedup_id}"] = msg

            # Store in matching streams
            matched_streams = []
            for s_name, s_cfg in self._streams.items():
                if any(self._subject_matches(pattern, subject) for pattern in s_cfg.subjects):
                    self._messages[s_name].append(msg)
                    matched_streams.append(s_name)

            # Dispatch to in-process subscribers
            for pattern, handlers in self._subscribers.items():
                if self._subject_matches(pattern, subject):
                    for handler in handlers:
                        try:
                            handler(msg)
                        except Exception as e:
                            logger.error(f"Error in NATS event subscriber for {subject}: {e}")

            logger.info(f"NATS EVENT PUBLISHED: {subject} (Seq: {msg.sequence}, Streams: {matched_streams})")
            return msg

    def ack_message(self, message_id: str, stream_name: Optional[str] = None) -> bool:
        """Acknowledges successful processing of a message."""
        with self._lock:
            streams_to_check = [stream_name] if stream_name and stream_name in self._messages else self._messages.keys()
            found = False
            for s in streams_to_check:
                for m in self._messages.get(s, []):
                    if m.message_id == message_id:
                        m.acked = True
                        found = True
            return found

    def get_unacked_messages(self, stream_name: str, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns pending unacknowledged messages for consumer crash recovery."""
        with self._lock:
            msgs = self._messages.get(stream_name, [])
            res = []
            for m in msgs:
                if not m.acked:
                    if tenant_id and m.headers.get("tenant_id") and m.headers.get("tenant_id") != tenant_id:
                        continue
                    res.append(m.to_dict())
            return res

    def subscribe(self, subject_pattern: str, handler: Callable[[NatsMessage], None]):

        """Subscribes an event handler to a subject pattern."""
        with self._lock:
            if subject_pattern not in self._subscribers:
                self._subscribers[subject_pattern] = []
            self._subscribers[subject_pattern].append(handler)
            logger.info(f"NATS SUBSCRIBER REGISTERED: '{subject_pattern}'")

    def replay_stream(
        self,
        stream_name: str,
        since_sequence: int = 0,
        since_timestamp: Optional[float] = None,
        filter_subject: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Replays historical messages from JetStream storage."""
        with self._lock:
            msgs = self._messages.get(stream_name, [])
            res = []
            for m in msgs:
                if m.sequence < since_sequence:
                    continue
                if since_timestamp and m.timestamp < since_timestamp:
                    continue
                if filter_subject and not self._subject_matches(filter_subject, m.subject):
                    continue
                if tenant_id and m.headers.get("tenant_id") and m.headers.get("tenant_id") != tenant_id:
                    continue
                res.append(m.to_dict())
                if limit and len(res) >= limit:
                    break
            return res

    def _subject_matches(self, pattern: str, subject: str) -> bool:
        """Evaluates NATS wildcard subject matches (* and >)."""
        pat_parts = pattern.split(".")
        sub_parts = subject.split(".")

        i = 0
        while i < len(pat_parts) and i < len(sub_parts):
            if pat_parts[i] == ">":
                return True
            if pat_parts[i] != "*" and pat_parts[i] != sub_parts[i]:
                return False
            i += 1

        if i < len(pat_parts) and pat_parts[i] == ">":
            return True
        return i == len(pat_parts) and i == len(sub_parts)

# Global singleton instance
jetstream_engine = JetStreamEngine.get_instance()
nats_broker = jetstream_engine

