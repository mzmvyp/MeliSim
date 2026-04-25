from enum import StrEnum


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"


class PaymentMethod(StrEnum):
    CREDIT_CARD = "credit_card"
    PIX = "pix"
    BOLETO = "boleto"
