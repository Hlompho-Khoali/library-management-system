REJECTION_REASONS = {
    "unclear_image": "The ID photo was not clear enough to read.",
    "not_id_document": "The uploaded photo does not show a valid ID document.",
    "details_mismatch": "The details on the ID do not match the registration information.",
    "incomplete_photo": "The ID photo is cropped or missing information.",
    "other": "Other reason (see comment).",
}


def describe_rejection_reasons(codes):
    """Convert a comma-separated string of reason codes into readable labels."""

    if not codes:
        return []

    selected = [code.strip() for code in codes.split(",") if code.strip()]

    return [REJECTION_REASONS.get(code, code) for code in selected]
