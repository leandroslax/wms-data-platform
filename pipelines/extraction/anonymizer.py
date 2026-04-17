SENSITIVE_FIELDS = {"cpf", "email", "phone", "document_number"}


def mask_record(record: dict) -> dict:
    return {
        key: "***" if key.lower() in SENSITIVE_FIELDS and value is not None else value
        for key, value in record.items()
    }
