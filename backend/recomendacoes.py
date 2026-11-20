"""Seleção de assuntos e classificação de recomendações bibliográficas."""

from typing import Any

from backend.catalogo import normalize_text, search_books

GENERIC_SUBJECTS = {
    "fiction", "ficcao", "general", "literature", "literatura", "novels", "novel",
    "accessible book", "protected daisy", "in library", "bibliography",
    "open library staff picks", "reading level", "books", "livros",
    "english literature", "american literature", "translations", "accessible books",
}


def useful_subjects(books: list[dict[str, Any]]) -> list[str]:
    """Seleciona até dois assuntos específicos recorrentes na biblioteca.

    Parâmetros:
        books: livros previamente normalizados por ``valid_books``.

    Retorno:
        Lista de assuntos representativos para pesquisa no catálogo.

    Integração:
        ``recommend_books`` usa os assuntos para consultar Open Library.

    Tratamento de erros:
        Lista sem assuntos utilizáveis resulta em lista vazia.
    """
    counter: dict[str, int] = {}
    original: dict[str, str] = {}
    for book in books:
        for subject in book["subjects"]:
            short = subject.split(" -- ")[0].strip()
            key = normalize_text(short)
            if key in GENERIC_SUBJECTS or not (4 <= len(key) <= 50) or key.isdigit():
                continue
            counter[key] = counter.get(key, 0) + 1
            original[key] = short
    return [original[key] for key, _ in sorted(counter.items(), key=lambda item: -item[1])[:2]]


def recommend_books(
    books: list[dict[str, Any]], *, preferences: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Busca e classifica obras relacionadas aos assuntos da biblioteca.

    Parâmetros:
        books: livros da biblioteca da conta autenticada, validados pela rota.
        preferences: interesses pessoais opcionais com categoria, valor e nível.

    Retorno:
        Dicionário JSON serializável com livros, assuntos e mensagem opcional.

    Integração:
        Consulta ``search_books`` para cada assunto; a rota Flask obtém os
        registros pessoais pelos repositórios PostgreSQL antes desta chamada.

    Tratamento de erros:
        ``CatalogError`` é tratado pela rota para manter resposta HTTP 503.
    """
    if not books:
        return {"books": [], "message": "Adicione um livro à biblioteca para gerar recomendações."}
    safe_preferences = [
        item for item in (preferences or [])
        if isinstance(item, dict)
        and item.get("category") in {"genero", "assunto"}
        and isinstance(item.get("value"), str)
        and item["value"].strip()
        and isinstance(item.get("level", 3), int)
        and not isinstance(item.get("level", 3), bool)
    ]
    subjects = useful_subjects(books)
    ordered_queries: list[str] = []
    # Favoritos e interesses explicitamente salvos aumentam prioridade sem virar
    # previsão de preferência nem excluir os assuntos observados no catálogo.
    favorite_subjects = useful_subjects([book for book in books if book.get("favorite")])
    for value in [item["value"] for item in sorted(
        safe_preferences, key=lambda preference: -preference.get("level", 3)
    )] + favorite_subjects + subjects:
        if normalize_text(value) not in {normalize_text(query) for query in ordered_queries}:
            ordered_queries.append(value)
    subjects = ordered_queries[:4]
    if not subjects:
        return {"books": [], "message": "Os livros salvos ainda não têm assuntos específicos no catálogo. Tente outro livro."}
    owned = {book["id"] for book in books}
    owned_titles = {normalize_text(book["title"]) for book in books if book.get("title")}
    collection: dict[str, dict[str, Any]] = {}
    for subject in subjects:
        for candidate in search_books(subject, 24, subject=True):
            candidate_title = normalize_text(candidate.get("title", ""))
            if candidate["id"] in owned or candidate_title in owned_titles:
                continue
            candidate_subjects = {normalize_text(value) for value in candidate.get("subjects", [])}
            score = sum(3 for value in subjects if normalize_text(value) in candidate_subjects)
            score += len(candidate_subjects & {
                normalize_text(value) for book in books for value in book["subjects"]
            })
            matched_preference = next((item for item in safe_preferences
                                       if normalize_text(item["value"]) in candidate_subjects), None)
            if matched_preference:
                score += matched_preference.get("level", 3)
            reason = (f"Obra relacionada ao interesse em {matched_preference['value']}"
                      if matched_preference else f"Obra sugerida por compartilhar assuntos: {subject}")
            recommendation = {**candidate, "score": score, "reason": reason}
            recommendation_key = candidate_title or candidate["id"]
            previous = collection.get(recommendation_key)
            if previous is None or recommendation["score"] > previous["score"]:
                collection[recommendation_key] = recommendation
    suggestions = sorted(collection.values(), key=lambda book: (-book["score"], book["title"]))[:9]
    return {
        "books": suggestions,
        "subjects": subjects,
        "message": None if suggestions else "Não encontrei sugestões neste momento.",
    }
