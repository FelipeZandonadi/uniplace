from rest_framework.pagination import LimitOffsetPagination


class Paginacao(LimitOffsetPagination):
    """`?offset=` = quantos itens o front já tem: excluir um item não faz o próximo lote pular outro.
    `max_limit` impede que `?limit=` vire um "me dá tudo"."""

    default_limit = 20
    max_limit = 50
