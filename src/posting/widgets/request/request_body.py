from typing import Iterable

from textual import on, events
from textual.widgets.text_area import Location
from textual.widgets import TextArea

from posting.text_area_theme import POSTLING_THEME


class RequestBodyTextArea(TextArea):
    """
    For editing request bodies.
    """

    DEFAULT_CSS = """\
    RequestBodyTextArea {
        border: none;

        &:focus {
            border: none;
        }

    }
    """

    OPENING_BRACKETS = {
        "(": ")",
        "[": "]",
        "{": "}",
    }

    CLOSING_BRACKETS = {v: k for k, v in OPENING_BRACKETS.items()}

    def on_mount(self):
        self.register_theme(POSTLING_THEME)
        self.theme = "posting"
        self.show_line_numbers = True
        self.tab_behavior = "indent"
        self.indent_width = 2
        self.set_class(len(self.text) == 0, "empty")

    @on(TextArea.Changed)
    def on_change(self, event: TextArea.Changed) -> None:
        self.set_class(len(self.text) == 0, "empty")

    def _on_key(self, event: events.Key) -> None:
        character = event.character

        if character in self.OPENING_BRACKETS:
            opener = character
            closer = self.OPENING_BRACKETS[opener]
            self.insert(f"{opener}{closer}")
            self.move_cursor_relative(columns=-1)
            event.prevent_default()
        elif character in self.CLOSING_BRACKETS:
            # If we're currently at a closing bracket and
            # we type the same closing bracket, move the cursor
            # instead of inserting a character.
            if self._matching_bracket_location:
                row, col = self.cursor_location
                line = self.document.get_line(row)
                if character == line[col]:
                    event.prevent_default()
                    self.move_cursor_relative(columns=1)
        elif event.key == "enter":
            row, column = self.cursor_location
            line = self.document.get_line(row)
            if not line:
                return

            column = min(column, len(line) - 1)
            character_locations = self._yield_character_locations_reverse(
                (row, max(0, column - 1))
            )
            rstrip_line = line[: column + 1].rstrip()
            anchor_char = rstrip_line[-1] if rstrip_line else None
            get_content_start_column = self.get_content_start_column
            get_column_width = self.get_column_width
            try:
                #
                for character, location in character_locations:
                    # Ignore whitespace
                    if character.isspace():
                        continue
                    elif character in self.OPENING_BRACKETS:
                        # We found an opening bracket on this line,
                        # so check the indentation of the line.
                        # The newly created line should have increased
                        # indentation.
                        content_start_col = get_content_start_column(line)
                        width = get_column_width(row, content_start_col)
                        width_to_indent = max(
                            width + self.indent_width, self.indent_width
                        )

                        target_location = row + 1, column + width_to_indent
                        insert_text = "\n" + " " * width_to_indent
                        print("Anchor char", anchor_char)
                        if anchor_char in self.CLOSING_BRACKETS:
                            # If there's a bracket under the cursor, we should
                            # ensure that gets indented too.
                            insert_text += "\n" + " " * content_start_col

                        self.insert(insert_text)
                        self.cursor_location = target_location
                        event.prevent_default()
                        break
                    else:
                        content_start_col = get_content_start_column(line)
                        width = get_column_width(row, content_start_col)
                        print("width", width)
                        self.insert("\n" + " " * width)
                        event.prevent_default()
                        break

                # If we make it to here, we didn't find an opening bracket
                # on the line, so just insert a newline and indent to the
                # same level as the previous line.

            except IndexError:
                return

        self._restart_blink()

    def get_content_start_column(self, line: str) -> int:
        content_start_col = 0
        for index, char in enumerate(line):
            if not char.isspace():
                content_start_col = index
                break
        return content_start_col

    def _yield_character_locations_reverse(
        self, start: Location
    ) -> Iterable[tuple[str, Location]]:
        row, column = start
        document = self.document
        line_count = document.line_count

        while line_count > row >= 0:
            line = document[row]
            if column == -1:
                column = len(line) - 1
            while column >= 0:
                yield line[column], (row, column)
                column -= 1
            row -= 1
