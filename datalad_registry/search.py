from functools import partial
from lark import Lark, Token, Transformer, v_args
from sqlalchemy import Text, or_, and_, not_

from .models import RepoUrl, URLMetadata

escape = "\\"
def _escape_for_ilike(value):
    escaped_value = (
        value.replace(escape, escape + escape)
        .replace("%", escape + "%")
        .replace("_", escape + "_")
    )
    return f"%{escaped_value}%"

# ATM most are  1:1 mapping to DB schema.
# List explicitly so we could reuse in grammar and error messages etc
# without duplication
known_fields_RepoUrl_1to1 = ["url", "ds_id", "head", "head_describe", "branches", "tags"]
def get_ilike_search(model, field, value):
    return getattr(model, field).ilike(_escape_for_ilike(value), escape=escape)

def get_metadata_ilike_search(value):
    escaped_value = _escape_for_ilike(value)
    return RepoUrl.metadata_.any(
        or_(
            URLMetadata.extractor_name.ilike(escaped_value, escape=escape),
            URLMetadata.extracted_metadata.cast(Text).ilike(escaped_value, escape=escape),
        )
    )

# mapping to schema of fields
known_fields = {
    _: partial(get_ilike_search, RepoUrl, _)
    for _ in known_fields_RepoUrl_1to1
}
known_fields["metadata"] = get_metadata_ilike_search
# TODO: add "metadata_extractor"?
known_fields_str = "|".join(f'"{_}"' for _ in known_fields)

# This is a grammar for the search query language.
# For interactive testing, you can use the Lark parser at https://www.lark-parser.org/ide/
grammar = fr"""
?start: search
?search: orand_exp
?orand_exp: not_exp
        | orand_exp ("OR" not_exp)+ -> or_search
        | orand_exp ("AND" not_exp)+ -> and_search
?not_exp: primary
        | "NOT" primary -> not_expr

?primary: "(" search ")" // -> group
        | secondary

// if no op, so just `:` it would be identical to `:?` (present within)
?secondary: (field_select | unknown_field_error) ":" op? (quoted_string | WORD) -> field_matched
        | WORD  -> search_word
        | quoted_string  -> search_string

// later to subselect metadata
// ?field_select: (field | metadata_field "[" metadata_extractors "]") value_path?
// ?value_path: ("[" (WORD|quoted_string) "]")+
?field_select: field
    | metadata_field "[" metadata_extractors "]" -> field_select
?metadata_extractors: WORD (","WORD)*
!field: {known_fields_str}
!metadata_field: "metadata"
// To make it easier for user to be informed about an unknown field being specified in the field_matching
!unknown_field_error: WORD

// Let's make it into a rule so we could have transformer for it
// and unescape escaped \s
?quoted_string: ESCAPED_STRING // /"((?:\.|[^\"])*)"/
WORD: /[-_.*?+\w]+/

// :operations to aim for
!op: "?"   // string present somewhere within
    |"="   // equal to the value as a string
    |">"   // greater to the value as a string
    |"~"   // regex search, should be able to use ^ and $ to anchor if desired 
// TODO:
//  - come up with transformers, e.g. (int) or `!int` to precede :? etc which should change how operations like =, >
//  - operator "in" might come handy
//  - also to make it case-sensitive since to make most useful - by default are case insensitive!

%import common.ESCAPED_STRING
%import common.WS
%ignore WS
"""
with open("/tmp/grammar.lark", "w") as f:
    f.write(grammar)

@v_args(inline=True)    # Affects the signatures of the methods
class SearchQueryTransformer(Transformer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Additional initialization here if needed

    def or_search(self, *args):
        # args will be a list of the arguments to the OR operation
        return or_(*args)

    def and_search(self, *args):
        # args will be a list of the arguments to the AND operation
        return and_(*args)

    def not_expr(self, arg):
        # args will be a single-element list containing the NOT argument
        return not_(arg)

    ## ?secondary: (field_select | unknown_field_error) ":" op? (quoted_string | WORD) -> field_matched
    def __field_select(self, metadata_field_l, metadata_extractors_l):
        assert metadata_field_l.data.value == 'metadata_field'
        assert metadata_extractors_l.data.value == 'metadata_extractors'

        extractors = list(map(self._get_str_value,
                              metadata_extractors_l.children))
        if not extractors:
            raise ValueError(f"No extractors were specified in {metadata_extractors_l}")
        elif len(extractors) == 1:
            raise NotImplementedError(f"Single extractor {extractors} is not implemented")
        else:
            # ??? it seems we do not have search target value here, so we are to
            # return the function to search with but we can't since here we already
            # need to know ilike vs exact match
            return RepoUrl.metadata_.any(
                or_(
                    URLMetadata.extractor_name == extractor,
                    # search the entire JSON column as text
                    URLMetadata.extracted_metadata.cast(Text).icontains(
                        value, autoescape=True
                    ),
                )
            )

    def field_matched(self, *args):
        # Example for handling field-specific matches. You'll need to expand this
        # logic based on your specific fields and operations.
        if len(args) == 3:
            field_l, op_l, value_l = args
            assert op_l.data.value == 'op'
            op = op_l.children[0].value
        elif len(args) == 2:
            # ":" is identical to ":?
            field_l, value_l = args
            op = '?'
        else:
            raise ValueError(f"Unexpected number of args: {len(args)} in {args}")

        assert field_l.data.value == 'field'
        assert len(field_l.children) == 1  # TODO: handle multiple??
        field = field_l.children[0].value

        if op == "?":
            return known_fields[field](self._get_str_value(value_l))
        else:
            raise NotImplementedError(f"Operation {op} is not implemented")

    def _get_str_value(self, arg: Token):
        assert isinstance(arg, Token)
        value = arg.value
        if arg.type == 'WORD':
            return value
        elif arg.type == 'ESCAPED_STRING':
            return value[1:-1].replace(r'\"', '"')
        else:
            raise TypeError(arg.type)

    def _get_str_search(self, arg: Token):
        value = self._get_str_value(arg)
        return or_(*[f(value) for f in known_fields.values()])

    search_word = _get_str_search
    search_string = _get_str_search

    def unknown_field_error(self, arg):
        # Handle unknown fields
        raise ValueError(f"Unknown field: '{arg}'. Known are: {', '.join(known_fields)}")


# Assuming `grammar` is your grammar definition string
parser = Lark(grammar, parser='lalr', transformer=SearchQueryTransformer())

# `query_struct` now is an SQLAlchemy expression ready to be applied to a query
## r = session.query(RepoUrl).filter(query_struct)