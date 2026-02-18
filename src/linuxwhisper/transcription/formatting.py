"""Sentence formatting post-processor for transcription output."""


def format_sentence(text: str) -> str:
    """Capitalize first character and ensure trailing punctuation.

    Whisper handles internal sentence punctuation well. This function
    only fixes the boundaries: uppercase first char, add period at end
    if no terminal punctuation exists.

    Args:
        text: Raw transcription text (already stripped by engine).

    Returns:
        Formatted text with capitalized first char and trailing punctuation.
    """
    if not text:
        return text

    # Capitalize first character
    text = text[0].upper() + text[1:]

    # Add period if no terminal punctuation
    if text[-1] not in ".!?":
        text += "."

    return text
