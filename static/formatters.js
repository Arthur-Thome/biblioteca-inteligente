'use strict';

/** Funções reutilizáveis de apresentação de datas e rótulos bibliográficos. */
(function registrarFormatadores(root) {
  const LANGUAGE_LABELS = Object.freeze({
    spa: 'Espanhol', por: 'Português', eng: 'Inglês', fre: 'Francês', fra: 'Francês',
    cat: 'Catalão'
  });
  const SOURCE_LABELS = Object.freeze({
    openlibrary: 'Open Library', google_books: 'Google Books'
  });

  /** Formata um instante ISO no horário de São Paulo sem alterar o instante recebido.
   *
   * @param {string|null|undefined} value - Instante serializado em ISO 8601.
   * @returns {string} Data brasileira ou "Não informado" para valor ausente/inválido.
   * @throws {never} Datas malformadas são convertidas em texto controlado.
   */
  function formatDateTimeBR(value) {
    if (typeof value !== 'string' || !value.trim()) return 'Não informado';
    const instant = new Date(value);
    if (Number.isNaN(instant.getTime())) return 'Não informado';
    const parts = new Intl.DateTimeFormat('pt-BR', {
      timeZone: 'America/Sao_Paulo',
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hourCycle: 'h23'
    }).formatToParts(instant).reduce((result, part) => {
      if (part.type !== 'literal') result[part.type] = part.value;
      return result;
    }, {});
    return `${parts.day}/${parts.month}/${parts.year} às ${parts.hour}:${parts.minute}`;
  }

  /** Converte somente códigos de idioma previamente conhecidos para rótulos confiáveis.
   *
   * @param {unknown} value - Valor bibliográfico original, preservado sem alteração.
   * @returns {unknown} Rótulo traduzido ou valor original quando não há mapeamento.
   */
  function languageLabel(value) {
    if (typeof value !== 'string') return value;
    return LANGUAGE_LABELS[value.trim().toLowerCase()] || value;
  }

  /** Converte códigos conhecidos do catálogo para nomes de exibição.
   *
   * @param {unknown} value - Identificador técnico original da fonte bibliográfica.
   * @returns {unknown} Nome amigável ou valor original para códigos desconhecidos.
   */
  function sourceLabel(value) {
    if (typeof value !== 'string') return value;
    return SOURCE_LABELS[value.trim().toLowerCase()] || value;
  }

  root.BibliotecaFormatters = Object.freeze({formatDateTimeBR, languageLabel, sourceLabel});
})(typeof window === 'undefined' ? globalThis : window);
