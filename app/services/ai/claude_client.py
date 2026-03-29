import anthropic
from flask import current_app


def get_client():
    return anthropic.Anthropic(api_key=current_app.config['ANTHROPIC_API_KEY'])


def generate(system_prompt, user_prompt, model='claude-sonnet-4-20250514', max_tokens=4096):
    """Call Claude API with system + user prompt pair.

    Returns the text content of the response.
    """
    client = get_client()
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[
            {'role': 'user', 'content': user_prompt}
        ],
    )
    return message.content[0].text
