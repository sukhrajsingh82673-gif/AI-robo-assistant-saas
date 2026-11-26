"""
Logistics Port & Carrier Tracking State Machine
================================================
State machine: label_created -> in_transit -> out_for_delivery -> delivered / exception.
LogisticsPort implementations for DHL, FedEx, and Freight.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ShipmentTrackingEvent(BaseModel):
    status: str  # 'label_created', 'in_transit', 'out_for_delivery', 'delivered', 'exception'
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    location: str
    details: str


class Shipment(BaseModel):
    tracking_number: str
    carrier: str  # 'DHL', 'FEDEX', 'FREIGHT'
    origin: str
    destination: str
    current_status: str = "label_created"
    events: List[ShipmentTrackingEvent] = Field(default_factory=list)


class LogisticsPort(ABC):
    """Abstract Port for Shipping Carriers."""

    @abstractmethod
    def create_shipment(self, carrier: str, origin: str, destination: str) -> Shipment:
        pass

    @abstractmethod
    def track_shipment(self, tracking_number: str) -> Shipment:
        pass

    @abstractmethod
    def advance_status(self, tracking_number: str, next_status: str, location: str, details: str) -> Shipment:
        pass


class SovereignLogisticsAdapter(LogisticsPort):
    """In-memory sovereign logistics tracker supporting DHL, FedEx, and Freight."""

    VALID_TRANSITIONS = {
        "label_created": ["in_transit", "exception"],
        "in_transit": ["out_for_delivery", "exception"],
        "out_for_delivery": ["delivered", "exception"],
        "delivered": [],
        "exception": ["in_transit", "delivered"]
    }

    def __init__(self):
        self.shipments: Dict[str, Shipment] = {}

    def create_shipment(self, carrier: str, origin: str, destination: str) -> Shipment:
        import uuid
        tracking_num = f"{carrier[:3].upper()}-{uuid.uuid4().hex[:10].upper()}"
        initial_event = ShipmentTrackingEvent(
            status="label_created",
            location=origin,
            details="Shipping label created"
        )
        shipment = Shipment(
            tracking_number=tracking_num,
            carrier=carrier.upper(),
            origin=origin,
            destination=destination,
            current_status="label_created",
            events=[initial_event]
        )
        self.shipments[tracking_num] = shipment
        return shipment

    def track_shipment(self, tracking_number: str) -> Shipment:
        if tracking_number not in self.shipments:
            raise KeyError(f"Tracking number {tracking_number} not found")
        return self.shipments[tracking_number]

    def advance_status(self, tracking_number: str, next_status: str, location: str, details: str) -> Shipment:
        shipment = self.track_shipment(tracking_number)
        current = shipment.current_status

        allowed = self.VALID_TRANSITIONS.get(current, [])
        if next_status not in allowed:
            raise ValueError(f"Invalid tracking state transition: {current} -> {next_status}")

        event = ShipmentTrackingEvent(
            status=next_status,
            location=location,
            details=details
        )
        shipment.current_status = next_status
        shipment.events.append(event)
        return shipment
