from sqlalchemy.sql.functions import GenericFunction


class fts_match_word(GenericFunction):
    type = None
    name = "fts_match_word"
    inherit_cache = True
