# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/coveragepy/django_coverage_plugin/blob/main/NOTICE.txt

"""The Django template coverage plugin."""

import os.path
import re

import coverage.plugin
import django
import django.template
from coverage.exceptions import NoSource
from django.template.base import Lexer, NodeList, Template, TextNode, TokenType
from django.template.defaulttags import VerbatimNode
from django.templatetags.i18n import BlockTranslateNode


class DjangoTemplatePluginException(Exception):
    """Used for any errors from the plugin itself."""

    pass


# For debugging the plugin itself.
SHOW_PARSING = False
SHOW_TRACING = False


def check_debug():
    """Check that Django's template debugging is enabled.

    Django's built-in "template debugging" records information the plugin needs
    to do its work.  Check that the setting is correct, and raise an exception
    if it is not.

    Returns True if the debug check was performed, False otherwise
    """
    from django.conf import settings

    if not settings.configured:
        return False

    # I _think_ this check is all that's needed and the 3 "hasattr" checks
    # below can be removed, but it's not clear how to verify that
    from django.apps import apps

    if not apps.ready:
        return False

    # django.template.backends.django gets loaded lazily, so return false
    # until they've been loaded
    if not hasattr(django.template, "backends"):
        return False
    if not hasattr(django.template.backends, "django"):
        return False
    if not hasattr(django.template.backends.django, "DjangoTemplates"):
        raise DjangoTemplatePluginException("Can't use non-Django templates.")
    if not django.template.engines._engines:
        return False

    for engine in django.template.engines.all():
        if not isinstance(engine, django.template.backends.django.DjangoTemplates):
            raise DjangoTemplatePluginException("Can't use non-Django templates.")
        if not engine.engine.debug:
            raise DjangoTemplatePluginException("Template debugging must be enabled in settings.")

    return True


if django.VERSION < (5, 0):
    raise RuntimeError("Django Coverage Plugin requires Django 5.x or higher")


# Since we are grabbing at internal details, we have to adapt as they
# change over versions.
def filename_for_frame(frame):
    try:
        return frame.f_locals["self"].origin.name
    except (KeyError, AttributeError):
        return None


def position_for_node(node):
    try:
        return node.token.position
    except AttributeError:
        return None


def position_for_token(token):
    return token.position


def read_template_source(filename):
    """Read the source of a Django template, returning the Unicode text."""
    # Import this late to be sure we don't trigger settings machinery too
    # early.
    from django.conf import settings

    if not settings.configured:
        settings.configure()

    with open(filename, encoding="utf-8") as f:
        text = f.read()

    return text


class DjangoTemplatePlugin(
    coverage.plugin.CoveragePlugin,
    coverage.plugin.FileTracer,
):
    def __init__(self, options):
        extensions = options.get("template_extensions", "html,htm,txt")
        self.extensions = [e.strip() for e in extensions.split(",")]

        self.debug_checked = False
        self.exclude_lines = []

        self.django_template_dir = os.path.normcase(
            os.path.realpath(os.path.dirname(django.template.__file__))
        )

        self.source_map = {}

    # --- CoveragePlugin methods

    def sys_info(self):
        return [
            ("django_template_dir", self.django_template_dir),
            (
                "environment",
                sorted((f"{k} = {v}") for k, v in os.environ.items() if "DJANGO" in k),
            ),
        ]

    def configure(self, config):
        self.html_report_dir = os.path.abspath(config.get_option("html:directory"))
        self.exclude_lines = config.get_option("report:exclude_lines")

    def file_tracer(self, filename):
        if os.path.normcase(filename).startswith(self.django_template_dir):
            if not self.debug_checked:
                # Keep calling check_debug until it returns True, which it
                # will only do after settings have been configured
                self.debug_checked = check_debug()

            return self
        return None

    def file_reporter(self, filename):
        return FileReporter(filename, self.exclude_lines)

    def find_executable_files(self, src_dir):
        # We're only interested in files that look like reasonable HTML
        # files: Must end with one of our extensions, and must not have
        # funny characters that probably mean they are editor junk.
        rx = r"^[^.#~!$@%^&*()+=,]+\.(" + "|".join(self.extensions) + r")$"

        for dirpath, dirnames, filenames in os.walk(src_dir):
            if dirpath == self.html_report_dir:
                # Don't confuse the HTML report with HTML templates.
                continue
            for filename in filenames:
                if re.search(rx, filename):
                    yield os.path.join(dirpath, filename)

    # --- FileTracer methods

    def has_dynamic_source_filename(self):
        return True

    # "render" is the public method, but "render_annotated" is an internal
    # method sometimes implemented directly on nodes.
    RENDER_METHODS = {"render", "render_annotated"}

    def dynamic_source_filename(self, filename, frame):
        if frame.f_code.co_name not in self.RENDER_METHODS:
            return None

        if 0:
            dump_frame(frame, label="dynamic_source_filename")
        filename = filename_for_frame(frame)
        if filename is not None:
            if filename.startswith("<"):
                # String templates have a filename of "<unknown source>", and
                # can't be reported on later, so ignore them.
                return None
            return filename
        return None

    def line_number_range(self, frame):
        assert frame.f_code.co_name in self.RENDER_METHODS
        if 0:
            dump_frame(frame, label="line_number_range")

        render_self = frame.f_locals["self"]
        if isinstance(render_self, (NodeList, Template)):
            return -1, -1

        position = position_for_node(render_self)
        if position is None:
            return -1, -1

        if SHOW_TRACING:
            print(f"{render_self!r}: {position}")
        s_start, s_end = position
        if isinstance(render_self, TextNode):
            first_line = render_self.s.splitlines(True)[0]
            if first_line.isspace():
                s_start += len(first_line)
        elif VerbatimNode and isinstance(render_self, VerbatimNode):
            # VerbatimNode doesn't track source the same way. s_end only points
            # to the end of the {% verbatim %} opening tag, not the entire
            # content. Adjust it to cover all of it.
            s_end += len(render_self.content)
        elif isinstance(render_self, BlockTranslateNode):
            # BlockTranslateNode has a list of text and variable tokens.
            # Get the end of the contents by looking at the last token,
            # and use its endpoint.
            last_tokens = render_self.plural or render_self.singular
            s_end = position_for_token(last_tokens[-1])[1]

        filename = filename_for_frame(frame)
        line_map = self.get_line_map(filename)
        start = get_line_number(line_map, s_start)
        end = get_line_number(line_map, s_end - 1)
        if start < 0 or end < 0:
            start, end = -1, -1
        if SHOW_TRACING:
            print(f"line_number_range({filename}) -> {(start, end)}")
        return start, end

    # --- FileTracer helpers

    def get_line_map(self, filename):
        """The line map for `filename`.

        A line map is a list of character offsets, indicating where each line
        in the text begins.  For example, a line map like this::

            [13, 19, 30]

        means that line 2 starts at character 13, line 3 starts at 19, etc.
        Line 1 always starts at character 0.

        """
        if filename not in self.source_map:
            template_source = read_template_source(filename)
            if 0:  # change to see the template text
                for i in range(0, len(template_source), 10):
                    print("%3d: %r" % (i, template_source[i : i + 10]))
            self.source_map[filename] = make_line_map(template_source)
        return self.source_map[filename]


class FileReporter(coverage.plugin.FileReporter):
    exclude_re = None

    def __init__(self, filename, exclude_patterns=None):
        super().__init__(filename)
        # TODO: html filenames are absolute.

        self._source = None
        self._excluded = None
        if exclude_patterns:
            self.exclude_re = re.compile("|".join(f"(?:{p})" for p in exclude_patterns))

    def source(self):
        if self._source is None:
            try:
                self._source = read_template_source(self.filename)
            except (OSError, UnicodeError) as exc:
                raise NoSource(f"Couldn't read {self.filename}: {exc}")
        return self._source

    def lines(self):
        source_lines = set()
        excluded = set()

        if SHOW_PARSING:
            print(f"-------------- {self.filename}")

        lexer = Lexer(self.source())
        tokens = list(lexer.tokenize())

        # Are we inside a comment?
        comment = False
        # Is this a template that extends another template?
        extends = False
        # Are we inside a block?
        inblock = False
        # Pragma exclusion state
        excluding = False
        exclude_depth = 0  # tracks nesting so we find the correct closing tag
        last_block_opener = None

        for token_idx, token in enumerate(tokens):
            if SHOW_PARSING:
                print(
                    "%10s %2d: %r"
                    % (
                        token.token_type.capitalize(),
                        token.lineno,
                        token.contents,
                    )
                )

            # While inside an excluded block, add all lines to the
            # excluded set and track nesting depth to find the matching
            # closing tag.
            if excluding:
                excluded.add(token.lineno)
                if token.token_type == TokenType.TEXT:
                    lineno = token.lineno
                    lines = token.contents.splitlines(True)
                    num_lines = len(lines)
                    if lines[0].isspace():
                        lineno += 1
                        num_lines -= 1
                    excluded.update(range(lineno, lineno + num_lines))
                elif token.token_type == TokenType.BLOCK:
                    tag = token.contents.split()[0]
                    if not tag.startswith("end"):
                        exclude_depth += 1
                    else:
                        exclude_depth -= 1
                        if exclude_depth == 0:
                            excluding = False
                continue

            if token.token_type == TokenType.BLOCK:
                if token.contents == "endcomment":
                    comment = False
                    continue

            if comment:
                continue

            if token.token_type == TokenType.BLOCK:
                if token.contents.startswith("endblock"):
                    inblock = False
                elif token.contents.startswith("block"):
                    inblock = True
                    if extends:
                        continue

                if extends and not inblock:
                    # In an inheriting template, ignore all tags outside of
                    # blocks.
                    continue

                if token.contents == "comment":
                    comment = True
                if token.contents.startswith("end"):
                    continue
                elif token.contents in ("else", "empty"):
                    continue
                elif token.contents.startswith("elif"):
                    # NOTE: I don't like this, I want to be able to trace elif
                    # nodes, but the Django template engine doesn't track them
                    # in a way that we can get useful information from them.
                    continue
                elif token.contents.startswith("extends"):
                    extends = True

                last_block_opener = token
                source_lines.add(token.lineno)

            elif token.token_type == TokenType.VAR:
                source_lines.add(token.lineno)

            elif token.token_type == TokenType.TEXT:
                if extends and not inblock:
                    continue
                # Text nodes often start with newlines, but we don't want to
                # consider that first line to be part of the text.
                lineno = token.lineno
                lines = token.contents.splitlines(True)
                num_lines = len(lines)
                if lines[0].isspace():
                    lineno += 1
                    num_lines -= 1
                # When a tag is not at the start of a line, the preceding
                # TEXT token ends with whitespace and no newline.
                # That partial line is not executable content.
                if num_lines > 0 and (lines[-1].isspace() and not lines[-1].endswith(("\n", "\r"))):
                    num_lines -= 1
                source_lines.update(range(lineno, lineno + num_lines))

            # {# pragma: no cover #} — exclude this line, and if the
            # comment sits on the same line as a block-opening tag,
            # exclude the entire block through its matching end tag.
            elif (
                self.exclude_re is not None
                and token.token_type == TokenType.COMMENT
                and self.exclude_re.search("{# " + token.contents + " #}")
            ):
                excluded.add(token.lineno)
                if last_block_opener is not None and last_block_opener.lineno == token.lineno:
                    # Look ahead for a matching end tag to confirm
                    # this is a block opener, not a self-closing tag.
                    end_tag = "end" + last_block_opener.contents.split()[0]
                    if any(
                        t.token_type == TokenType.BLOCK and t.contents.split()[0] == end_tag
                        for t in tokens[token_idx + 1 :]
                    ):
                        excluding = True
                        exclude_depth = 1

            if SHOW_PARSING:
                print(f"\t\t\tNow source_lines is: {source_lines!r}")

        self._excluded = excluded
        return source_lines - excluded

    def excluded_lines(self):
        """Return lines excluded via {# pragma: no cover #} comments."""
        if self._excluded is None:
            self.lines()
        return self._excluded


def running_sum(seq):
    total = 0
    for num in seq:
        total += num
        yield total


def make_line_map(text):
    line_lengths = [len(line) for line in text.splitlines(True)]
    line_map = list(running_sum(line_lengths))
    return line_map


def get_line_number(line_map, offset):
    """Find a line number, given a line map and a character offset."""
    for lineno, line_offset in enumerate(line_map, start=1):
        if line_offset > offset:
            return lineno
    return -1


def dump_frame(frame, label=""):
    """Dump interesting information about this frame."""
    locals = dict(frame.f_locals)
    self = locals.get("self", None)
    context = locals.get("context", None)
    if "__builtins__" in locals:
        del locals["__builtins__"]

    if label:
        label = " ( %s ) " % label
    print("-- frame --%s---------------------" % label)
    print(
        "{}:{}:{}".format(
            os.path.basename(frame.f_code.co_filename),
            frame.f_lineno,
            type(self),
        )
    )
    print(locals)
    if self:
        print("self:", self.__dict__)
    if context:
        print("context:", context.__dict__)
    print("\\--")
