from enum import Enum


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"


class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    PIX = "pix"
    BOLETO = "boleto"
