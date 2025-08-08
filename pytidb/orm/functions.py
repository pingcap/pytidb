from sqlalchemy.sql.functions import GenericFunction


class fts_match_word(GenericFunction):
    type = None
    name = "FTS_MATCH_WORD"
    inherit_cache = True


class vec_l1_distance(GenericFunction):
    type = None
    name = "VEC_L1_DISTANCE"
    inherit_cache = True


class vec_l2_distance(GenericFunction):
    type = None
    name = "VEC_L2_DISTANCE"
    inherit_cache = True


class vec_cosine_distance(GenericFunction):
    type = None
    name = "VEC_COSINE_DISTANCE"
    inherit_cache = True


class vec_negative_inner_product(GenericFunction):
    type = None
    name = "VEC_NEGATIVE_INNER_PRODUCT"
    inherit_cache = True


class vec_embed_l1_distance(GenericFunction):
    type = None
    name = "VEC_EMBED_L1_DISTANCE"
    inherit_cache = True


class vec_embed_l2_distance(GenericFunction):
    type = None
    name = "VEC_EMBED_L2_DISTANCE"
    inherit_cache = True


class vec_embed_cosine_distance(GenericFunction):
    type = None
    name = "VEC_EMBED_COSINE_DISTANCE"
    inherit_cache = True
