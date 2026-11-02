"""Gemeinsame Dokument-Bausteine für die Validator-Tests (vorher am Kopf von `test_blatt_validator.py`)."""

def build_document(answer_block):
    return (
        "---\n"
        "Titel: T\n"
        "Fach: M\n"
        "Thema: X\n"
        "---\n"
        f"{answer_block}\n"
    )


def build_document_with_mode(mode_value, block_content="Ein Block"):
    return (
        "---\n"
        "Titel: T\n"
        "Fach: M\n"
        "Thema: X\n"
        f"mode: {mode_value}\n"
        "---\n"
        f"{block_content}\n"
    )
