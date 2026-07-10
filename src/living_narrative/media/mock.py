"""外部通信を行わない決定論的画像provider。"""

import hashlib
import html


class MockImageProvider:
    """Prompt hashを表示する安定したSVG placeholderを返す。"""

    def generate(self, prompt: str, profile: str) -> bytes:
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        # profileはcredentialを誤って渡される可能性があるためasset本文へ埋め込まない。
        label = html.escape(f"mock image {digest[:16]}", quote=True)
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" '
            'viewBox="0 0 640 360">'
            '<rect width="640" height="360" fill="#20242b"/>'
            f'<text x="32" y="184" fill="#f1f3f5" font-family="monospace" '
            f'font-size="22">{label}</text></svg>\n'
        ).encode()
