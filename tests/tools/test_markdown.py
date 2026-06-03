"""Tests for rikugan.ui.markdown — Markdown-to-HTML converter."""

from __future__ import annotations

import unittest

from rikugan.ui.markdown import md_to_html


class TestMdToHtmlEmptyAndPlain(unittest.TestCase):
    def test_empty_string_returns_empty(self):
        self.assertEqual(md_to_html(""), "")

    def test_plain_text_passthrough(self):
        result = md_to_html("hello world")
        self.assertIn("hello world", result)

    def test_plain_text_with_newlines(self):
        result = md_to_html("hello\nworld")
        self.assertIn("hello", result)
        self.assertIn("world", result)


class TestMdToHtmlHeaders(unittest.TestCase):
    def test_h1(self):
        result = md_to_html("# Title")
        self.assertIn("Title", result)
        self.assertIn("20px", result)

    def test_h2(self):
        result = md_to_html("## Heading")
        self.assertIn("17px", result)

    def test_h3(self):
        result = md_to_html("### Sub")
        self.assertIn("15px", result)

    def test_h4(self):
        result = md_to_html("#### Small")
        self.assertIn("13px", result)

    def test_heading_with_bold(self):
        result = md_to_html("# **Bold Title**")
        self.assertIn("<b>Bold Title</b>", result)


class TestMdToHtmlHorizontalRule(unittest.TestCase):
    def test_triple_dash(self):
        result = md_to_html("---")
        self.assertIn("<hr", result)

    def test_triple_star(self):
        result = md_to_html("***")
        self.assertIn("<hr", result)


class TestMdToHtmlBulletList(unittest.TestCase):
    def test_dash_list(self):
        result = md_to_html("- item one\n- item two")
        self.assertIn("<ul", result)
        self.assertIn("<li>", result)
        self.assertIn("item one", result)
        self.assertIn("item two", result)

    def test_star_list(self):
        result = md_to_html("* alpha\n* beta")
        self.assertIn("<ul", result)
        self.assertIn("alpha", result)


class TestMdToHtmlNumberedList(unittest.TestCase):
    def test_numbered_list(self):
        result = md_to_html("1. first\n2. second")
        self.assertIn("<ol", result)
        self.assertIn("first", result)
        self.assertIn("second", result)


class TestMdToHtmlFencedCodeBlock(unittest.TestCase):
    def test_code_block_rendered(self):
        result = md_to_html("```python\nx = 1\n```")
        # Pygments wraps tokens in styled spans, so check for fragments
        self.assertIn("x", result)
        self.assertIn("1", result)
        self.assertIn("white-space", result)

    def test_code_block_with_lang_tag(self):
        result = md_to_html("```python\ncode\n```")
        # Language tag is no longer rendered as visible text.
        # Verify the block still renders with syntax highlighting.
        self.assertIn("<table", result)
        self.assertIn("code", result)

    def test_code_block_without_lang(self):
        result = md_to_html("```\nraw code\n```")
        self.assertIn("raw code", result)

    def test_code_block_escapes_html(self):
        result = md_to_html("```\n<script>alert(1)</script>\n```")
        self.assertNotIn("<script>", result)
        self.assertIn("&lt;script&gt;", result)

    def test_code_block_not_processed_for_inline(self):
        result = md_to_html("```\n**not bold**\n```")
        self.assertNotIn("<b>not bold</b>", result)


class TestMdToHtmlParagraph(unittest.TestCase):
    def test_paragraph_break(self):
        result = md_to_html("para one\n\npara two")
        self.assertIn("para one", result)
        self.assertIn("para two", result)


class TestInlineFormatting(unittest.TestCase):
    def test_bold(self):
        result = md_to_html("**bold**")
        self.assertIn("<b>bold</b>", result)

    def test_italic(self):
        result = md_to_html("*italic*")
        self.assertIn("<i>italic</i>", result)

    def test_link(self):
        result = md_to_html("[text](http://example.com)")
        self.assertIn("href", result)
        self.assertIn("text", result)
        self.assertIn("http://example.com", result)

    def test_inline_code(self):
        result = md_to_html("use `foo()` here")
        self.assertIn("foo()", result)

    def test_bold_inside_code_not_applied(self):
        result = md_to_html("`**not bold**`")
        self.assertNotIn("<b>not bold</b>", result)

    def test_html_escaped_in_code_block(self):
        result = md_to_html("```\n<b>not bold</b>\n```")
        self.assertNotIn("<b>not bold</b>", result)
        self.assertIn("&lt;b&gt;", result)


class TestMdToHtmlIntegration(unittest.TestCase):
    def test_mixed_content(self):
        md = "# Title\n\nSome **bold** and `code`.\n\n- item\n- item2"
        result = md_to_html(md)
        self.assertIn("<b>bold</b>", result)
        self.assertIn("<ul", result)
        self.assertIn("Title", result)

    def test_link_in_list(self):
        result = md_to_html("- [link](http://x.com)")
        self.assertIn("href", result)
        self.assertIn("<li>", result)


class TestMdToHtmlTables(unittest.TestCase):
    def test_basic_table(self):
        result = md_to_html("| Name | Type |\n|------|------|\n| foo  | int  |")
        self.assertIn("<table", result)
        self.assertIn("<th", result)
        self.assertIn("<td", result)
        self.assertIn("Name", result)
        self.assertIn("foo", result)

    def test_table_with_many_rows(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |"
        result = md_to_html(md)
        self.assertIn("<table", result)
        self.assertIn("1", result)
        self.assertIn("3", result)


class TestMdToHtmlBlockquotes(unittest.TestCase):
    def test_single_blockquote(self):
        result = md_to_html("> quoted text")
        self.assertIn("quoted text", result)

    def test_blockquote_has_border_style(self):
        result = md_to_html("> quoted text")
        self.assertIn("border-left", result)


class TestMdToHtmlStrikethrough(unittest.TestCase):
    def test_strikethrough(self):
        result = md_to_html("~~deleted~~")
        self.assertIn("<s>deleted</s>", result)


class TestMdToHtmlTaskLists(unittest.TestCase):
    def test_unchecked_task(self):
        result = md_to_html("- [ ] todo item")
        self.assertIn("☐", result)

    def test_checked_task(self):
        result = md_to_html("- [x] done item")
        self.assertIn("☑", result)


class TestMdToHtmlNestedLists(unittest.TestCase):
    def test_nested_bullet_list(self):
        md = "- item one\n  - nested item\n- item two"
        result = md_to_html(md)
        self.assertIn("item one", result)
        self.assertIn("nested item", result)
        # Should have nested <ul> inside <li>
        self.assertEqual(result.count("<ul"), 2)

    def test_mixed_nested_list(self):
        md = "1. first\n   - nested bullet\n2. second"
        result = md_to_html(md)
        self.assertIn("first", result)
        self.assertIn("nested bullet", result)
        self.assertIn("<ul", result)
        self.assertIn("<ol", result)


class TestMdToHtmlStreaming(unittest.TestCase):
    def test_incomplete_code_block(self):
        """Streaming often delivers unclosed code blocks."""
        result = md_to_html("```python\ndef foo(")
        # Pygments splits tokens, so check fragments are present
        self.assertIn("foo", result)
        self.assertIn("white-space", result)

    def test_incomplete_bold(self):
        result = md_to_html("Some **bold te")
        self.assertIn("**bold te", result)

    def test_incomplete_table(self):
        result = md_to_html("| Name | Type |\n|---")
        self.assertIn("Name", result)


if __name__ == "__main__":
    unittest.main()
