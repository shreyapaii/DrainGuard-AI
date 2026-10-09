from drainguard.ui import badge, esc, priority_badge


def test_user_text_is_escaped_to_prevent_markup_injection():
    assert esc("<script>x</script>") == "&lt;script&gt;x&lt;/script&gt;"


def test_badge_escapes_text():
    html_out = badge("<b>bad</b>", "critical")
    assert "<b>" not in html_out
    assert "dg-badge-critical" in html_out


def test_priority_badge_tones():
    assert "dg-badge-high" in priority_badge("High")
    assert "dg-badge-medium" in priority_badge("Medium")
    assert "dg-badge-low" in priority_badge("Low")
